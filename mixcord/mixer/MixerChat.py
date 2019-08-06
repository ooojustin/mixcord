import inspect
import requests
import shlex

from .MixerWS import MixerWS

class MixerChat:

    class ChatCommands:

        commands = dict()

        def __init__(self, chat, prefix):
            self.chat = chat
            self.prefix = prefix

        def __call__(self, method):
            if inspect.iscoroutinefunction(method):
                sig = inspect.signature(method)
                self.commands[method.__name__] = {
                    "method": method,
                    "signature": sig,
                    "param_count": len(sig.parameters) - 1 # ignore data parameter (required)
                }

        async def handle(self, data):

            # determine the raw message as text
            message = ""
            pieces = data["message"]["message"]
            for piece in pieces: message += piece["text"]

            # verify that prefix is 1 character
            if len(self.prefix) != 1:
                raise ValueError("Prefix must be a single character.")

            # command prefix check
            if message[:1] != self.prefix:
                return False

            # handle it as a command
            try:
                parsed = shlex.split(message) # split string by whitespace and account for quotes
                name = parsed[0][1:] # the name of the command -> 0th item with command prefix removed
                arguments = parsed[1:] # remove first parsed item, because its the command name
            except:
                await self.chat.send_message("an error occurred while parsing that command.")
                return False

            # make sure the command exists
            command = self.commands.get(name, None)
            if command is None:
                await self.chat.send_message("unrecognized command '{}'.".format(name))
                return False

            # make sure we've been supplied the correct number of arguments
            if len(arguments) != command["param_count"]:
                await self.chat.send_message("invalid parameter count for command '{}'.".format(name))
                return False

            # try to execute the command!
            message = await command["method"](data, *arguments)
            if message is not None:
                message = "@{} {}".format(data["user_name"], message)
                await self.chat.send_message(message)

            return True

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

    async def send_message(self, message, user = None):
        if user is None:
            await self.send_method_packet("msg", message)
        else:
            await self.send_method_packet("whisper", user, message)
        await self.websocket.receive_packet()

    def register_method_callback(self, id, callback):
        if inspect.iscoroutinefunction(callback):
            if not id in self.callbacks:
                self.callbacks[id] = callback

    async def start(self, access_token):

        # get the bots username and user id
        token_data = self.api.check_token(access_token)
        self.user_id = token_data["sub"]
        self.username = token_data["username"]

        url = "{}/chats/{}".format(self.api.API_URL, self.channel_id)
        headers = { "Authorization": "Bearer " + access_token }
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
                        await self.commands.handle(packet["data"])

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