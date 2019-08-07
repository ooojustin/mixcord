import json, asyncio, utils

# determine settings
settings_raw = utils.read_all_text("settings.cfg")
settings = json.loads(settings_raw)

# database initialization
import database
database.init()

import bots.mixer
import bots.discord

loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.gather(
    bots.discord.bot.start(settings["discord"]["token"]),
    bots.mixer.auth.start(bots.mixer.mixer),
    bots.mixer.bot.start(bots.mixer.auth),
    bots.mixer.constellation.start(bots.mixer.auth))
)
