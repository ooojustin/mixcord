import json
from mixer import MixerAPI

# determine settings
settings_raw = open("settings.cfg").read()
settings = json.loads(settings_raw)

# database initialization
import database
database.init()

# mixer initialization
mixer = MixerAPI(settings["mixer"]["client-id"], settings["mixer"]["client-secret"])

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

    # TODO: make sure discord id isn't already in database

    # get shortcode stuff from mixer
    shortcode = mixer.get_shortcode()
    code = shortcode["code"]
    handle = shortcode["handle"]

    # tell the user what to do to link their mixer account
    await ctx.send("Visit the following page to link your Mixer: https://mixer.com/go?code=" + code)

    # TODO: poll url w/ handle

bot.run(settings["discord"]["token"])
