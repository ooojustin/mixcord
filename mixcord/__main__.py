import requests, json, sys
from mixer import MixerAPI

import database
database.init()

settings_raw = open("settings.cfg").read()
settings = json.loads(settings_raw)

mixer = MixerAPI(settings["mixer"]["client-id"], settings["mixer"]["client-secret"])
id = mixer.get_channel_id("ooojustin")
chats = mixer.get_chats(id)
print(json.dumps(chats))
