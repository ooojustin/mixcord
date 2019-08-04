import requests, json
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

    packet_id = 0

    def __init__(self, api, channel_id, access_token, refresh_token):
        self.api = api
        self.channel_id = channel_id
        self.access_token = access_token
        self.refresh_token = refresh_token

        # get the bots user id
        self.token_data = self.api.check_token(access_token)
        self.user_id = self.token_data["sub"]

    async def send_method_packet(self, method, *args):
        packet = {
            "type": "method",
            "method": method,
            "arguments": list(args),
            "id": self.packet_id
        }
        packet_raw = json.dumps(packet)
        await self.websocket.send(packet_raw)
        self.packet_id += 1
        return packet["id"]

    async def receive_reply_packet(self, id):

        while True:

            packet = await self.websocket.recv()
            packet = json.loads(packet)

            if packet["type"] != "reply":
                continue

            if packet["id"] != id:
                continue

            return packet

    async def start(self):

        url = "{}/chats/{}".format(self.api.API_URL, self.channel_id)
        headers = { "Authorization": "Bearer " + self.access_token }
        response = requests.get(url, headers = headers)
        chat_info = response.json() # https://pastebin.com/Z3RyUgBh

        # establish websocket connection and receive welcome packet
        self.websocket = await websockets.connect(chat_info["endpoints"][0])
        await self.websocket.recv()

        # authenticate connection so we can send messages and stuff
        auth_packet_id = await self.send_method_packet("auth", self.channel_id, self.user_id, chat_info["authkey"])
        auth_packet = await self.receive_reply_packet(auth_packet_id)
        print(json.dumps(auth_packet, indent = 4))

        # handle future messages
        while True:
            packet = json.loads(await self.websocket.recv())
            print(json.dumps(packet, indent = 4))

    def send_message(self, message):
        async def send_message_async():
            msg_packet_id = await self.send_method_packet("msg", message)
            msg_packet = await self.receive_reply_packet(msg_packet_id)
        asyncio.ensure_future(send_message_async())
