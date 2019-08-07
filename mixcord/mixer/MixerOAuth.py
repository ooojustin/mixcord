import json, asyncio, inspect, logging
from time import time

class MixerOAuth:

    # array of methods to invoke once access_token is refreshed
    # methods are invoked with 2 params (new access_token/refresh_token)
    refreshed_events = list()

    def __init__(self, access_token, refresh_token):
        self.access_token = access_token
        self.refresh_token = refresh_token

    async def refresh(self):
        tokens = self.api.get_token(self.refresh_token, refresh = True)
        self.access_token = tokens["access_token"]
        self.refresh_token = tokens["refresh_token"]
        for event in self.refreshed_events:
            if inspect.iscoroutinefunction(event):
                await event(self.access_token, self.refresh_token)
            elif inspect.isfunction(event):
                event(self.access_token, self.refresh_token)

    async def start(self, api):

        self.api = api

        while True:

            token_data = api.check_token(self.access_token) # https://pastebin.com/diWKPbqg

            if not token_data["active"]:
                await self.refresh()
                continue

            expires_in = int(token_data["exp"] - time() - 10)
            logging.info("waiting ~{} seconds before refreshing access_token".format(expires_in))
            await asyncio.sleep(expires_in)
            await self.refresh()
