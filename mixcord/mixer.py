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
