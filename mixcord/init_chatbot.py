import json, time, utils
from mixer import MixerAPI
from __main__ import settings

mixer = MixerAPI(settings["mixer"]["client-id"], settings["mixer"]["client-secret"])

scope = [
"chat:bypass_catbot", "chat:bypass_filter", "chat:bypass_links",
"chat:bypass_slowchat", "chat:cancel_skill", "chat:change_ban",
"chat:change_role", "chat:chat", "chat:clear_messages",
"chat:connect", "chat:edit_options", "chat:giveaway_start",
"chat:poll_start", "chat:poll_vote", "chat:purge",
"chat:remove_message", "chat:timeout", "chat:view_deleted",
"chat:whisper"]

shortcode = mixer.get_shortcode(scope)

url = "https://mixer.com/go?code=" + shortcode["code"]
print("Please visit the following URL:", url)

while True:
    time.sleep(10)
    response = mixer.check_shortcode(shortcode["handle"])
    status_code = response.status_code
    if response.status_code == 200:
        authorization_code = response.json()["code"]
        print("Authorization Code:", authorization_code)
        break

tokens = mixer.get_token(authorization_code)
print("Access Token:", tokens["access_token"])
print("Refresh Token:", tokens["refresh_token"])

settings["mixer"]["access_token"] = tokens["access_token"]
settings["mixer"]["refresh_token"] = tokens["refresh_token"]

data_raw = json.dumps(settings, indent = 4)
utils.write_all_text("settings.cfg", data_raw)
