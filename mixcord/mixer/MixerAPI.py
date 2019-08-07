import requests
import dateutil.parser
from datetime import datetime, timezone, timedelta

from . import MixerExceptions
from .MixerObjects import MixerUser, MixerChannel

class MixerAPI:

    API_URL = "https://mixer.com/api/v1"
    API_URL_V2 = "https://mixer.com/api/v2"

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.session = requests.Session()
        self.session.headers.update({ "Client-ID": self.client_id })

    def get_channel(self, id_or_token):
        url = "{}/channels/{}".format(self.API_URL, id_or_token)
        response = self.session.get(url)
        if response.status_code == 200:
            return MixerChannel(response.json())
        elif response.status_code == 404:
            raise MixerExceptions.NotFound("Channel not found: API returned 404.")
        else:
            info = "{} -> {}".format(response.status_code, response.text)
            raise RuntimeError("API returned unhandled status code: " + info)

    def get_user(self, user_id):
        url = "{}/users/{}".format(self.API_URL, user_id)
        response = self.session.get(url)
        if response.status_code == 200:
            return MixerUser(response.json())
        elif response.status_code == 404:
            raise MixerExceptions.NotFound("User not found: API returned 404.")
        else:
            info = "{} -> {}".format(response.status_code, response.text)
            raise RuntimeError("API returned unhandled status code: " + info)

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

    # type format: [sparks, embers]-[weekly, monthly, yearly, alltime]
    def get_leaderboard(self, type, channel_id, limit = 10):
        url = "{}/leaderboards/{}/channels/{}?limit={}".format(self.API_URL_V2, type, channel_id, limit)
        response = self.session.get(url)
        return response.json()
