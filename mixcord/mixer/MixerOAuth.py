import json, asyncio
from time import time

class MixerOAuth:

    # array of methods to invoke once access_token is refreshed
    # methods are invoked with 2 params (new access_token/refresh_token)
    refreshed_events = list()

    def __init__(self, access_token, refresh_token):
        self.access_token = access_token
        self.refresh_token = refresh_token

    def refresh(self):
        tokens = self.mixer.get_token(self.refresh_token, refresh = True)
        self.access_token = tokens["access_token"]
        self.refresh_token = tokens["refresh_token"]
        for event in refreshed_events:
            event(self.access_token, self.refresh_token)

    async def start(self, mixer):

        self.mixer = mixer

        while True:

            token_data = mixer.check_token(self.access_token) # https://pastebin.com/diWKPbqg

            if not token_data["active"]:
                self.refresh()
                continue

            expires_in = int(token_data["exp"] - time() - 10)
            print("waiting {} seconds before refreshing access_token".format(expires_in))
            await asyncio.sleep(expires_in)
            self.refresh()
