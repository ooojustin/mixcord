import json, asyncio, utils

# determine settings
settings_raw = utils.read_all_text("settings.cfg")
settings = json.loads(settings_raw)

# database initialization
import database
database.init()

import bots.mixer
import bots.discord

# logging initialization
import logging
bots.mixer.log.setLevel(logging.ERROR)
bots.discord.log.setLevel(logging.ERROR)

loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.gather(
    bots.discord.bot.start(settings["discord"]["token"]),
    bots.mixer.chat.start(bots.mixer.auth),
    bots.mixer.constellation.start())
)
