import json, asyncio
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

    # shortcode auth method: https://dev.mixer.com/reference/oauth/shortcodeauth
    # TODO: make sure discord id isn't already in database

    # get shortcode stuff from mixer
    shortcode = mixer.get_shortcode()
    code = shortcode["code"]
    handle = shortcode["handle"]

    # tell the user what to do to link their mixer account
    await ctx.send("Visit the following page to link your Mixer: https://mixer.com/go?code=" + code)

    # poll shortcode checking endpoint with handle until we can move on with authorization_code
    while True:
        await asyncio.sleep(10)
        response = mixer.check_shortcode(handle)
        status_code = response.status_code
        if status_code == 200:
            authorization_code = response.json()["code"]
            await ctx.send("Confirmed: " + authorization_code)
            break
        elif status_code == 403:
            await ctx.send("Failed: user denied permissions.")
            return
        elif status_code == 404:
            await ctx.send("Failed: verification timed out.")
            return

    # TODO: use authorization_code variable to generate tokens...

bot.run(settings["discord"]["token"])
