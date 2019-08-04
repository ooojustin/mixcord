import sys
sys.path.append("..")

from __main__ import settings
from mixer import MixerAPI, MixerChat
import random

# initialize general mixer api wrapper
mixer = MixerAPI(settings["mixer"]["client-id"], settings["mixer"]["client-secret"])

# update chatbot tokens if needed
if not "access_token" in settings["mixer"]:
    print("Required variable 'access_token' missing from settings...\nDid you forget to run init_chatbot.py?")
    sys.exit()

# refresh the chatbot access token if needed
token_data = mixer.check_token(settings["mixer"]["access_token"])
if not token_data["active"]:
    tokens = mixer.get_token(settings["mixer"]["refresh_token"], refresh = True)
    settings["mixer"]["access_token"] = tokens["access_token"]
    settings["mixer"]["refresh_token"] = tokens["refresh_token"]
    file = open("settings.cfg", "w")
    file.write(json.dumps(settings, indent = 4))
    file.close()

# initialize chatbot
channel = mixer.get_channel(settings["mixer"]["username"])
bot = MixerChat(mixer, channel["id"])

# import discord bot from bots.discord module
from bots.discord import bot as discord

@bot.commands
async def flip(data):
    choice = random.randint(0, 1)
    desc = "heads" if choice else "tails"
    return "@{} flipped a coin and picked: {}".format(data["user_name"], desc)

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
    await bot.send_message("welcome to the stream, " + data["username"])
