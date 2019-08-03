import requests

class MixerAPI:

    API_URL = "https://mixer.com/api/v1"

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.session = requests.Session()
        self.session.headers.update({ "Client-ID": self.client_id })

    def get_channel(self, username):
        url = "{}/channels/{}".format(self.API_URL, username)
        response = self.session.get(url)
        return response.json()

    def get_channel_id(self, username):
        return self.get_channel(username)["id"]

    def get_discord(self, channel_id):
        url = "{}/channels/{}/discord".format(self.API_URL, channel_id)
        response = self.session.get(url)
        return response.json()

    def get_chats(self, channel_id):
        url = "{}/chats/{}".format(self.API_URL, channel_id)
        response = self.session.get(url)
        return response.json()

    def get_shortcode(self):
        url = "{}/oauth/shortcode".format(self.API_URL)
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": ""
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
