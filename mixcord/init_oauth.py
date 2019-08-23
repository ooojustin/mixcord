# TODO: the mixer module will *eventually* be installed via pypi
# i am temporarily spcifying the path during development of the wrapper
import sys
sys.path.append(R"C:\Users\justi\Documents\Programming\mixer.py")

import json, time, utils, asyncio
import mixer.exceptions as MixerExceptions
from mixer.api import MixerAPI
from __main__ import settings

async def run():

    api = MixerAPI(settings["mixer"]["client-id"], settings["mixer"]["client-secret"])

    scope = [
    "chat:bypass_catbot", "chat:bypass_filter", "chat:bypass_links",
    "chat:bypass_slowchat", "chat:cancel_skill", "chat:change_ban",
    "chat:change_role", "chat:chat", "chat:clear_messages",
    "chat:connect", "chat:edit_options", "chat:giveaway_start",
    "chat:poll_start", "chat:poll_vote", "chat:purge",
    "chat:remove_message", "chat:timeout", "chat:view_deleted",
    "chat:whisper"]

    shortcode = await api.get_shortcode(scope)
    authorization_code = None

    url = "https://mixer.com/go?code=" + shortcode["code"]
    print("Please visit the following URL:", url)

    while not authorization_code:
        await asyncio.sleep(10)
        try:
            response = await api.check_shortcode(shortcode["handle"])
            authorization_code = response["code"]
            print("Authorization Code:", authorization_code)
        except MixerExceptions.WebException as ex:
            # NOTE: status 204 -> still waiting...
            if ex.status == 403:
                print("Permission denied.")
                return False
            elif ex.status == 404:
                print("Timed out.")
                return False

    tokens = await api.get_token(authorization_code)
    print("Access Token:", tokens["access_token"])
    print("Refresh Token:", tokens["refresh_token"])

    settings["mixer"]["access_token"] = tokens["access_token"]
    settings["mixer"]["refresh_token"] = tokens["refresh_token"]

    data_raw = json.dumps(settings, indent = 4)
    utils.write_all_text("settings.cfg", data_raw)

    await api.close()
