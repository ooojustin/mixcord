import requests, json, sys
from mixer import MixerAPI

settings_raw = open("settings.cfg").read()
settings = json.loads(settings_raw)

# https://mixer.com/oauth/authorize?client_id=7472a113de477580849d668215f8aaaf37e0ecdea991be7f&response_type=code&redirect_uri=https:%2F%2Fjustin.ooo&scope=...

# m = MixerAPI(settings["mixer-client-id"], settings["mixer-client-secret"])
m = MixerAPI("", "")
channel = m.get_channel("ooojustin")
chats = m.get_chats(id)
print(json.dumps(chats))
