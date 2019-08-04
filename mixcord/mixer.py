import requests, json, inspect
import asyncio, websockets

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

    def get_discord(self, channel_id):
        url = "{}/channels/{}/discord".format(self.API_URL, channel_id)
        response = self.session.get(url)
        return response.json()

    def get_chats(self, channel_id):
        url = "{}/chats/{}".format(self.API_URL, channel_id)
        response = self.session.get(url)
        return response.json()

    def get_shortcode(self, scope = ""):
        url = "{}/oauth/shortcode".format(self.API_URL)
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": scope
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

class MixerChat:

    # used to uniquely identify 'method' packets
    packet_id = 0

    # used to store references to event functions (see __call__ and call_func)
    funcs = dict()

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

    def __call__(self, method):
        if callable(method):
            self.funcs[method.__name__] = method

    async def call_func(self, name, *args):

        # make sure the function exists
        # these are added via __call__ (@instance_name decorator)
        if not name in self.funcs:
            return

        # get a reference to the function
        func = self.funcs[name]

        # call the function (await if async)
        if inspect.iscoroutinefunction(func):
            await func(*args)
        else:
            func(*args)

    async def send_packet(self, packet):
        packet_raw = json.dumps(packet)
        await self.websocket.send(packet_raw)

    async def receive_packet(self):
        packet_raw = await self.websocket.recv()
        return json.loads(packet_raw)

    async def send_method_packet(self, method, *args):
        packet = {
            "type": "method",
            "method": method,
            "arguments": list(args),
            "id": self.packet_id
        }
        await self.send_packet(packet)
        self.packet_id += 1
        return packet["id"]

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
        self.websocket = await websockets.connect(chat_info["endpoints"][0])
        welcome_packet = await self.receive_packet()
        print(json.dumps(welcome_packet, indent = 4))

        # authenticate connection so we can send messages and stuff
        auth_packet_id = await self.send_method_packet("auth", self.channel_id, self.user_id, chat_info["authkey"])
        await self.websocket.recv()

        # try to trigger on_ready func, because we're authenticated
        await self.call_func("on_ready", self.username, self.user_id)

        # infinite loop to handle future packets from server
        while True:

            # receive a packet from the server
            packet = await self.receive_packet()

            if packet["type"] == "event":
                print(packet["event"])
                if packet["event"] in self.event_map:
                    func_name = self.event_map[packet["event"]]
                    await self.call_func(func_name, packet["data"])

    async def send_message(self, message):
        await self.send_method_packet("msg", message)
        await self.websocket.recv()
