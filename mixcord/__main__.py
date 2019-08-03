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

    # TODO: make sure we private message the link to the user, if its in a guild

    # make sure discord id isn't already in database
    discord_id = ctx.author.id
    if database.mixer_from_discord(discord_id) is not None:
        await ctx.send("You've already linked your Mixer account via mixcord.")
        return

    # get shortcode stuff from mixer
    shortcode = mixer.get_shortcode()
    code = shortcode["code"]
    handle = shortcode["handle"]

    # tell the user what to do to link their mixer account
    await ctx.send("Visit the following page to link your Mixer: <https://mixer.com/go?code={}>".format(code))

    # poll shortcode checking endpoint with handle until we can move on with authorization_code
    while True:
        await asyncio.sleep(10)
        response = mixer.check_shortcode(handle)
        status_code = response.status_code
        if status_code == 200:
            authorization_code = response.json()["code"]
            break
        elif status_code == 403:
            await ctx.send("Failed: user denied permissions.")
            return
        elif status_code == 404:
            await ctx.send("Failed: verification timed out.")
            return

    tokens = mixer.get_token(authorization_code)
    token_data = mixer.check_token(tokens["access_token"])
    user_data = mixer.get_user(token_data["sub"])

    user_id = user_data["id"]
    channel_id = user_data["channel"]["id"]
    database.insert_user(user_id, channel_id, discord_id)
    await ctx.send("Your Mixer account has been linked: " + user_data["username"])


bot.run(settings["discord"]["token"])
