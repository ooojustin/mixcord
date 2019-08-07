import inspect
import requests
import shlex
import asyncio
import json

from .MixerWS import MixerWS
from .MixerObjects import MixerChatMessage

class MixerChat:

    class ChatCommands:

        commands = dict()

        def get_command(self, name, param_count = None):

            # make sure the command actually exists
            if not name in self.commands:
                return None

            # get a list of overloaded commands
            command_list = self.commands[name]

            # if parma_count isnt specified, return the first defined func
            if param_count is None:
                return command_list[0]

            # look for a definition with a matching parameter count
            for command in command_list:
                if command["param_count"] == param_count:
                    return command

            # return false because the command is defined but no matching parameter count
            return False

        def get_help(self, name, param_count = None):

            command = self.get_command(name, param_count)

            if command is False:
                return "failed to find '{}' command with {} parameters.".format(name, param_count)
            elif command is None:
                return "failed to find '{}' command.".format(name)
            elif command["description"] is None:
                return "command '{}' with {} parameters is undocumented.".format(name, param_count)

            if command["param_count"] > 0:
                params = ", ".join(command["params"])
                return "{} ({}) -> {}".format(name, params, command["description"])
            else:
                return "{} -> {}".format(name, command["description"])

        def add_command(self, name, method):

            if not inspect.iscoroutinefunction(method):
                return

            name = name.lower()
            sig = inspect.signature(method)
            params = sig.parameters
            command = {
                "method": method,
                "signature": sig,
                "description": method.__doc__, # command docstring (should be a brief description)
                "params": list(params.keys())[1:], # list of parameter names
                "param_count": len(params) - 1 # ignore data parameter (required)
            }

            existing = self.get_command(name, command["param_count"])
            if isinstance(existing, dict):
                # this command name already exists with this parameter count
                # it cant be overloaded unless we override the old one
                return

            if name in self.commands:
                self.commands[name].append(command)
            else:
                self.commands[name] = [command]

        async def handle(self, message):

            # determine the raw message as text
            text = message.get_text()

            # command prefix check
            if text[:1] != self.prefix:
                return False

            # handle it as a command
            try:
                parsed = shlex.split(text) # split string by whitespace and account for quotes
                name = parsed[0][1:].lower() # the name of the command -> 0th item with command prefix removed
                arguments = parsed[1:] # remove first parsed item, because its the command name
            except:
                await self.chat.send_message("an error occurred while parsing that command.")
                return False

            # make sure the command exists
            command = self.get_command(name, len(arguments))
            if command is None:
                await self.chat.send_message("unrecognized command '{}'.".format(name))
                return False
            elif command is False:
                await self.chat.send_message("invalid parameter count for command '{}'.".format(name))
                return False

            # try to execute the command!
            message.chat = self.chat
            response = await command["method"](message, *arguments)
            if response is not None:
                response = "@{} {}".format(message.user_name, response)
                await self.chat.send_message(response)

            return True

        def __init__(self, chat, prefix):

            self.chat = chat
            self.prefix = prefix

            # initialize default commands
            for name, methods in DEFAULT_COMMANDS.items():
                for method in methods:
                    self.add_command(name, method)

        def __call__(self, method):
            self.add_command(method.__name__, method)

    # used to uniquely identify 'method' packets
    packet_id = 0

    # used to store references to functions (see __call__ and call_func)
    funcs = dict()
    callbacks = dict()

    # map events to functions
    event_map = {
        "WelcomeEvent": "welcomed",
        "ChatMessage": "handle_message",
        "UserJoin": "user_joined",
        "UserLeave": "user_left",
        "PollStart": "poll_started",
        "PollEnd": "poll_end",
        "DeleteMessage": "message_deleted",
        "PurgeMessage": "messages_purged",
        "ClearMessages": "messages_cleared",
        "UserUpdate": "user_updated",
        "UserTimeout": "user_timed_out",
        "SkillAttribution": "handle_skill",
        "DeleteSkillAttribution": "skill_cancelled"
    }

    def __init__(self, api, channel_id, command_prefix = ">"):

        self.api = api
        self.channel_id = channel_id

        # verify that prefix is 1 character
        if len(command_prefix) != 1:
            raise ValueError("Prefix must be a single character.")
        else:
            self.commands = self.ChatCommands(self, command_prefix)

    def __call__(self, method):
        if inspect.iscoroutinefunction(method):
            self.funcs[method.__name__] = method

    async def call_func(self, name, *args):

        # make sure the function exists
        # these are added via __call__ (@instance_name decorator)
        if not name in self.funcs: return

        # get a reference to the function
        func = self.funcs[name]

        # call the function
        await func(*args)

    async def send_method_packet(self, method, *args):
        packet = {
            "type": "method",
            "method": method,
            "arguments": list(args),
            "id": self.packet_id
        }
        await self.websocket.send_packet(packet)
        self.packet_id += 1
        return packet["id"]

    def register_method_callback(self, id, callback):
        if inspect.iscoroutinefunction(callback):
            if not id in self.callbacks:
                self.callbacks[id] = callback

    async def start(self, oauth):

        # get the bots username and user id
        token_data = self.api.check_token(oauth.access_token)
        self.user_id = token_data["sub"]
        self.username = token_data["username"]

        url = "{}/chats/{}".format(self.api.API_URL, self.channel_id)
        headers = { "Authorization": "Bearer " + oauth.access_token }
        response = requests.get(url, headers = headers)
        chat_info = response.json() # https://pastebin.com/Z3RyUgBh

        # authentication callback (executed when w received reply for 'auth' method)
        async def auth_callback(data):
            if data["authenticated"]:
                await self.call_func("on_ready", self.username, self.user_id)

        # send auth packet upon connection and register auth_callback
        async def connected_callback():
            auth_packet_id = await self.send_method_packet("auth", self.channel_id, self.user_id, chat_info["authkey"])
            self.register_method_callback(auth_packet_id, auth_callback)

        # establish websocket connection and receive welcome packet
        self.websocket = MixerWS(chat_info["endpoints"][0])
        self.websocket.on_connected = connected_callback
        await self.websocket.connect()

        # infinite loop to handle future packets from server
        while True:

            # receive a packet from the server
            packet = await self.websocket.receive_packet()

            # handle 'event' packets from server
            if packet["type"] == "event":
                if packet["event"] in self.event_map:

                    # custom handling for chat messages (commands?)
                    if packet["event"] == "ChatMessage":
                        message = MixerChatMessage(packet["data"])
                        await self.commands.handle(message)

                    # call corresponding event handler
                    func_name = self.event_map[packet["event"]]
                    await self.call_func(func_name, packet["data"])

                continue

            # handle 'reply' packets from server
            if packet["type"] == "reply":

                # see if there's a reply callback for this packet
                callback = self.callbacks.pop(packet["id"], None)
                if callback is not None:

                    # invoke callback with data from reply packet
                    response = packet.get("data", packet)
                    await callback(response)

                continue

    async def send_message(self, message, user = None):
        if user is None:
            await self.send_method_packet("msg", message)
        else:
            await self.send_method_packet("whisper", user, message)

    async def delete_message(self, id):
        await self.send_method_packet("deleteMessage", id)

async def help_0(message):
    """Displays a list of commands that can be used in the chat."""

    chat = message.chat
    command_count = 0
    command_names = list()

    # build a list of command names/descriptions with params
    for name, commands in chat.commands.commands.items():

        variants = list()

        for command in commands:

            if command["description"] is None:
                continue

            command_count += 1
            variants.append(str(command["param_count"]))

        if len(variants) == 0:
            continue
        elif len(variants) == 1:
            command_names.append(name)
        else:
            param_counts = ", ".join(variants)
            command_names.append("{} ({})".format(name, param_counts))

    # delete original >help message
    await chat.delete_message(message.id)

    # formate response messages
    message1 = "There are a total of {} commands: {}."
    message2 = "To see information about a specific command, use '{}help command_name'."
    message1 = message1.format(command_count, ", ".join(command_names))
    message2 = message2.format(chat.commands.prefix)

    # whisper formatted response messages to used
    await chat.send_message(message1, message.user_name)
    await asyncio.sleep(.5) # wait before sending second message :p
    await chat.send_message(message2, message.user_name)

async def help_1(message, name):
    """Provides a description of a specific command."""
    name = name.lower()
    return message.chat.commands.get_help(name)

async def help_2(message, name, parameter_count_or_name):
    """Provides a description of a command given a parameter count or parameter name."""
    chat = message.chat

    # if the second parameter is an int, assume they're specifying parameter count
    name = name.lower()
    try:
        return chat.commands.get_help(name, int(parameter_count_or_name))
    except ValueError: pass

    # fallback to get_help command if it doesnt exist
    if not name in chat.commands.commands:
        return chat.commands.get_help(name)

    # try to find a definition of the specified command with the given parameter name
    for command in chat.commands.commands[name]:
        if parameter_count_or_name in command["params"]:
            return chat.commands.get_help(name, command["param_count"])
    return "no variation of command '{}' has parameter named '{}'.".format(name, parameter_count_or_name)

DEFAULT_COMMANDS = {
    "help": [help_0, help_1, help_2]
}
