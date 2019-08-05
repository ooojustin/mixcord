import requests, json, inspect
import asyncio, websockets, shlex, dateutil.parser
from datetime import datetime, timezone, timedelta

class MixerAPI:

    API_URL = "https://mixer.com/api/v1"

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.session = requests.Session()
        self.session.headers.update({ "Client-ID": self.client_id })

    def get_channel(self, id_or_token):
        url = "{}/channels/{}".format(self.API_URL, id_or_token)
        response = self.session.get(url)
        return response.json()

    def get_user(self, user_id):
        url = "{}/users/{}".format(self.API_URL, user_id)
        response = self.session.get(url)
        return response.json() # https://pastebin.com/paR8PfSn

    def get_shortcode(self, scope = None):
        url = "{}/oauth/shortcode".format(self.API_URL)
        if scope is None: scope = list()
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": " ".join(scope)
        }
        response = self.session.post(url, data)
        return response.json()

    def check_shortcode(self, handle):
        url = "{}/oauth/shortcode/check/{}".format(self.API_URL, handle)
        response = self.session.get(url)
        return response

    def get_token(self, code_or_token, refresh = False):
        url = "{}/oauth/token".format(self.API_URL)
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        if refresh:
            data["grant_type"] = "refresh_token"
            data["refresh_token"] = code_or_token
        else:
            data["grant_type"] = "authorization_code"
            data["code"] = code_or_token

        response = self.session.post(url, data)
        return response.json() # https://pastebin.com/n1Kjjphq

    def check_token(self, token):
        url = "{}/oauth/token/introspect".format(self.API_URL)
        data = { "token": token }
        response = self.session.post(url, data)
        return response.json() # https://pastebin.com/SEd6Y2Jz

    def get_broadcast(self, channel_id):
        url = "{}/channels/{}/broadcast".format(self.API_URL, channel_id)
        response = self.session.get(url)
        return response.json()

    def get_uptime(self, channel_id):

        # get broadcast and make sure it's online
        broadcast = self.get_broadcast(channel_id)
        if "error" in broadcast or not broadcast["online"]:
            return None

        # determine the streams start time and current time
        started = dateutil.parser.parse(broadcast["startedAt"])
        now = datetime.now(timezone.utc)

        # calculate delta and remove microseconds because they're insignificant
        delta = now - started
        delta = delta - timedelta(microseconds = delta.microseconds)
        return delta

class MixerWS:

    def __init__(self, url, opts = None):
        self.url = url
        self.opts = opts if opts is not None else dict()
        
    async def connect(self):
        self.websocket = await websockets.connect(self.url, **self.opts)

    async def send_packet(self, packet):
        packet_raw = json.dumps(packet)
        await self.websocket.send(packet_raw)

    async def receive_packet(self):
        packet_raw = await self.websocket.recv()
        return json.loads(packet_raw)

class MixerChat:

    class ChatCommands:

        commands = dict()

        def __init__(self, chat):
            self.chat = chat

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

            # command prefix check
            if message[:1] != ">":
                return False

            # handle it as a command
            parsed = shlex.split(message) # split string by whitespace and account for quotes
            name = parsed[0][1:] # the name of the command -> 0th item with command prefix removed
            arguments = parsed[1:] # remove first parsed item, because its the command name

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
            if len(message) > 0:
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

    def __init__(self, api, channel_id):
        self.api = api
        self.channel_id = channel_id
        self.commands = self.ChatCommands(self)

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

    async def send_message(self, message):
        await self.send_method_packet("msg", message)
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

        # establish websocket connection and receive welcome packet
        self.websocket = MixerWS(chat_info["endpoints"][0])
        await self.websocket.connect()

        # authentication callback (executed when w received reply for 'auth' method)
        async def auth_callback(data):
            if data["authenticated"]:
                await self.call_func("on_ready", self.username, self.user_id)

        # send auth packet and register callback
        auth_packet_id = await self.send_method_packet("auth", self.channel_id, self.user_id, chat_info["authkey"])
        self.register_method_callback(auth_packet_id, auth_callback)

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

class MixerConstellation:

    CONSTELLATION_URL = "wss://constellation.mixer.com"

    def __init__(self, on_connected):
        self.on_connected = on_connected
        self.callbacks = dict()
        self.packet_id = 0

    async def start(self, access_token):

        # connect to websocket with oauth access token
        opts = { 'extra_headers': { "Authorization": "Bearer " + access_token } }
        self.websocket = MixerWS(self.CONSTELLATION_URL, opts)
        await self.websocket.connect()

        await self.websocket.receive_packet() # receive welcome packet
        await self.on_connected(self) # call on_connected func (we should probably subscribe to events)

        while True:

            # receive packets from server
            packet = await self.websocket.receive_packet()
            print(json.dumps(packet, indent = 4))

            # make sure it's an event we're subscribed to
            if packet["type"] != "event": continue
            if packet["event"] != "live": continue

            # find and invoke the callback function with the packet & payload
            event_name = packet["data"]["channel"]
            payload = packet["data"]["payload"]
            callback = self.callbacks.get(event_name, None)
            if callback is not None:
                await callback(packet, payload)

    async def subscribe(self, event_name, callback):

        # build livesubscribe packet
        packet = {
            "type": "method",
            "method": "livesubscribe",
            "params": {
                "events": [event_name]
            },
            "id": self.packet_id
        }

        # send packet to server and determine callback
        await self.websocket.send_packet(packet)
        self.callbacks[event_name] = callback

        # increment packet id and return unique packet id
        self.packet_id += 1
        return self.packet_id
