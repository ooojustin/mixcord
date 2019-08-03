import json
from mixer import MixerAPI

# determine settings
settings_raw = open("settings.cfg").read()
settings = json.loads(settings_raw)

# database initialization
import database
database.init()

# discord bot initialization
import discord, logging
from discord.ext import commands
logging.basicConfig(level = logging.ERROR)
bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
    print('discord logged in:', bot.user)

@bot.command()
async def mixcord(ctx):
    await ctx.send("got it")

bot.run(settings["discord"]["token"])
