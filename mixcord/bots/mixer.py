import sys
sys.path.append("..")

from __main__ import settings
from mixer import MixerAPI, MixerChat, MixerConstellation
import random, utils, json

from mixer.MixerAPI import MixerAPI
from mixer.MixerChat import MixerChat
from mixer.MixerConstellation import MixerConstellation

# initialize general mixer api wrapper
mixer = MixerAPI(settings["mixer"]["client-id"], settings["mixer"]["client-secret"])

# initialize chatbot with oauth tokens if needed
if not "access_token" in settings["mixer"]:
    import init_oauth

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
from discord.utils import get as discord_get
from bots.discord import bot as discord

@bot.commands
async def announce(data, message):

    # make sure the person triggering the command is stream owner
    if not "Owner" in data["user_roles"]:
        return "permission denied. only owner can use 'announce' command."

    # get discord guild from config + announcements channel
    guild = discord.get_guild(settings["discord"]["guild"])
    channel = discord_get(guild.text_channels, name = "announcements")

    # send the announcement and return chat message
    await channel.send("@everyone " + message)
    return "announcement has been sent."

@bot.commands
async def uptime(data):

    # get uptime and check if online
    uptime = mixer.get_uptime(channel["id"])
    if uptime is None:
        return channel["token"] + " is not currently online."

    # return formatted uptime
    return channel["token"] + " has been live for: " + str(uptime)

@bot.commands
async def ping(data):
    return "pong!"

@bot.commands
async def uid(data):
    return "your user id is: {}".format(data["user_id"])

@bot.commands
async def avatar(data):
    return "link to your avatar: {}".format(data["user_avatar"])

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

async def follow_triggered(packet, payload):
    message = "@{} ".format(payload["user"]["username"])
    message += "thanks for following!" if payload["following"] else "why'd you unfollow :("
    await bot.send_message(message)

async def skill_triggered(packet, payload):
    user = mixer.get_user(payload["triggeringUserId"])
    username = user["username"]
    await bot.send_message("@{} just used a whopping {} {}".format(username, payload["price"], payload["currencyType"].lower()))

async def broadcast_triggered(packet, payload):

    if not "online" in payload: return

    if payload["online"]:
        await bot.send_message("@{} has gone online!".format(channel["token"]))
    else:
        await bot.send_message("@{} has gone offline :(".format(channel["token"]))

# triggered when constellation websocket connection is established
# this function should be used to subscribe to events
async def constellation_connected(constellation):

    # subscribe to follow/unfollow event
    event_name = "channel:{}:followed".format(channel["id"])
    await constellation.subscribe(event_name, follow_triggered)

    # subscribe to skill event
    event_name = "channel:{}:skill".format(channel["id"])
    await constellation.subscribe(event_name, skill_triggered)

    # subscribe to chanenl update event
    event_name = "channel:{}:broadcast".format(channel["id"])
    await constellation.subscribe(event_name, broadcast_triggered)

# initialize constellation manager w/ connected callback
constellation = MixerConstellation(constellation_connected)
