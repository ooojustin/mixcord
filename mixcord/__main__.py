import json, asyncio, sys
from mixer import MixerAPI, MixerChat

# determine settings
settings_raw = open("settings.cfg").read()
settings = json.loads(settings_raw)

# database initialization
import database
database.init()

# mixer initialization
mixer = MixerAPI(settings["mixer"]["client-id"], settings["mixer"]["client-secret"])

# update chatbot tokens if needed
if not "access_token" in settings["mixer"]:
    print("Required variable 'access_token' missing from settings...\nDid you forget to run init_chatbot.py?")
    sys.exit()

token_data = mixer.check_token(settings["mixer"]["access_token"])
if not token_data["active"]:
    tokens = mixer.get_token(settings["mixer"]["refresh_token"], refresh = True)
    settings["mixer"]["access_token"] = tokens["access_token"]
    settings["mixer"]["refresh_token"] = tokens["refresh_token"]
    file = open("settings.cfg", "w")
    file.write(json.dumps(settings, indent = 4))
    file.close()

# chatbot initiailization ?
channel = mixer.get_channel(settings["mixer"]["username"])
mixer_chat = MixerChat(mixer, channel["id"], settings["mixer"]["access_token"], settings["mixer"]["refresh_token"])
asyncio.get_event_loop().run_until_complete(mixer_chat.init())

# discord bot initialization
import discord, logging
from discord.ext import commands
logging.basicConfig(level = logging.ERROR)
bot = commands.Bot(command_prefix = '!')

@bot.event
async def on_ready():
    print('discord logged in:', bot.user)

@bot.command()
async def mixcord(ctx):

    # make sure discord id isn't already in database
    discord_id = ctx.author.id
    if database.user_from_discord(discord_id) is not None:
        await ctx.author.send("You've already linked your Mixer account via mixcord.")
        return

    # get shortcode stuff from mixer
    shortcode = mixer.get_shortcode()
    code = shortcode["code"]
    handle = shortcode["handle"]

    # tell the user what to do to link their mixer account
    await ctx.author.send("Visit the following page to link your Mixer: <https://mixer.com/go?code={}>".format(code))

    # poll shortcode checking endpoint with handle until we can move on with authorization_code
    while True:
        await asyncio.sleep(10)
        response = mixer.check_shortcode(handle)
        status_code = response.status_code
        if status_code == 200:
            authorization_code = response.json()["code"]
            break
        elif status_code == 403:
            await ctx.author.send("Failed: user denied permissions.")
            return
        elif status_code == 404:
            await ctx.author.send("Failed: verification timed out.")
            return

    tokens = mixer.get_token(authorization_code)
    token_data = mixer.check_token(tokens["access_token"])
    user_data = mixer.get_user(token_data["sub"])

    user_id = user_data["id"]
    channel_id = user_data["channel"]["id"]

    database.insert_user(user_id, channel_id, discord_id)
    database.update_tokens(discord_id, tokens["access_token"], tokens["refresh_token"], token_data["exp"])

    await ctx.author.send("Your Mixer account has been linked: " + user_data["username"])

bot.run(settings["discord"]["token"])
