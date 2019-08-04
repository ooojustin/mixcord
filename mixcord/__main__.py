import json, asyncio

# determine settings
settings_raw = open("settings.cfg").read()
settings = json.loads(settings_raw)

# database initialization
import database
database.init()

import bots.mixer
import bots.discord

loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.gather(
    bots.discord.bot.start(settings["discord"]["token"]),
    bots.mixer.bot.start(settings["mixer"]["access_token"]))
)
