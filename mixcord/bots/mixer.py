import sys
sys.path.append("..")

from __main__ import settings
from mixer import MixerAPI, MixerChat
import random, utils

# initialize general mixer api wrapper
mixer = MixerAPI(settings["mixer"]["client-id"], settings["mixer"]["client-secret"])

# initialize chatbot with oauth tokens if needed
if not "access_token" in settings["mixer"]:
    import init_chatbot

# refresh the chatbot access token if needed
token_data = mixer.check_token(settings["mixer"]["access_token"])
if not token_data["active"]:

    # update access_token and refresh_token from server
    tokens = mixer.get_token(settings["mixer"]["refresh_token"], refresh = True)
    settings["mixer"]["access_token"] = tokens["access_token"]
    settings["mixer"]["refresh_token"] = tokens["refresh_token"]

    # store updated tokens in settings file
    settings_cfg = json.dumps(settings, indent = 4)
    utils.write_all_text("settings.cfg", settings_cfg)

# initialize chatbot
channel = mixer.get_channel(settings["mixer"]["username"])
bot = MixerChat(mixer, channel["id"])

# import discord bot from bots.discord module
from bots.discord import bot as discord

@bot
async def handle_message(data):
    pass

@bot.commands
async def flip(data):
    choice = random.randint(0, 1)
    desc = "heads" if choice else "tails"
    return "flipped a coin and picked: " + desc

@bot.commands
async def add(data, n1, n2):

    # make sure both inputs are numeric before trying to use them as floats
    if not utils.is_number(n1) or not utils.is_number(n2):
        return "please ensure both parameters are numeric."

    # return the sum of the numbers
    sum = float(n1) + float(n2)
    return "sum = " + str(sum)

@bot.commands
async def lunch(data):

    if not "Owner" in data["user_roles"]:
        return "permission denied. only owner can use 'lunch' command."

    await bot.send_method_packet(
        "vote:start",
        "What should I get for lunch?",
        ["Chinese Food", "Mexican Food", "Pizza"], 30)

    return "starting poll for lunch... cast your vote!"

# trigerred when the mixer bot is connected + authenticated
@bot
async def on_ready(username, user_id): #
    print("mixer logged in: {} (uid = {})".format(username, user_id))
    await bot.send_message("mixcord logged in successfully!")

# trigerred when a user joins the stream
@bot
async def user_joined(data):
    await bot.send_message("welcome to the stream, @" + data["username"])
