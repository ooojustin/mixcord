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

# establish coroutines
discord = bots.discord.bot.start(settings["discord"]["token"])
chat = bots.mixer.chat.start(bots.mixer.auth)
constellation = bots.mixer.constellation.start()

# run coroutines using mixer.py utility func
import mixer, mixer.utils
mixer.utils.run(discord, chat, constellation)
