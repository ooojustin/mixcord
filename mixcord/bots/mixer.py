import sys
sys.path.append("..")

import random, utils, json, asyncio, os, requests
from __main__ import settings as settings_all
settings = settings_all["mixer"]

from mixer.MixerAPI import MixerAPI
from mixer.MixerChat import MixerChat
from mixer.MixerConstellation import MixerConstellation
from mixer.MixerOAuth import MixerOAuth
import mixer.MixerExceptions as MixerExceptions

# initialize chatbot with oauth tokens if needed
if not "access_token" in settings:
    import init_oauth

# initialize general mixer api wrapper and oauth manager
api = MixerAPI(settings["client-id"], settings["client-secret"])
auth = MixerOAuth(settings["access_token"], settings["refresh_token"])

# initialize chatbot
try:
    channel = api.get_channel(settings["username"])
    chat = MixerChat(api, channel.id)
except MixerExceptions.NotFound:
    print("invalid account username specified in settings file.")
    sys.exit(1)

# import discord bot from bots.discord module
from bots.discord import send_announcement
from bots.discord import bot as discord

@chat.commands
async def shutdown(message):

    # make sure the person triggering the command is stream owner
    if not message.has_role("Owner"):
        return "permission denied. only owner can use 'shutdown' command."

    # shutdown the bot
    await chat.send_message("bot shutting down...")
    await asyncio.sleep(.5) # wait before exiting
    sys.exit(0)

@chat.commands
async def restart(message):

    # make sure the person triggering the command is stream owner
    if not message.has_role("Owner"):
        return "permission denied. only owner can use 'restart' command."

    # restart the bot
    await chat.send_message("bot restarting... wait a few seconds")
    await asyncio.sleep(.5) # wait before restarting

    # modify arguments and use execl to execute python module
    sys.argv.insert(0, '"{}"'.format(sys.executable))
    os.execl(sys.executable, *sys.argv)

@chat.commands
async def announce(message, announcement):

    # make sure the person triggering the command is stream owner
    if not message.has_role("Owner"):
        return "permission denied. only owner can use 'announce' command."

    await send_announcement(announcement)
    return "announcement has been sent."

@chat.commands
async def uptime(message):
    """Displays how long the streamer has been live for."""

    # get uptime and check if online
    uptime = channel.get_uptime()
    if uptime is None:
        return channel.token + " is not currently online."

    # return formatted uptime
    return channel.token + " has been live for: " + str(uptime)

@chat.commands
async def ping(message):
    """Returns 'pong!'"""
    return "pong!"

@chat.commands
async def uid(message):
    """Tells a user their unique user id on Mixer."""
    return "your user id is: {}".format(message.user_id)

@chat.commands
async def uid(message, username):
    """Tells a user the unique user id of a tagged user on Mixer."""

    if len(username) < 2 or username[:1] != "@":
        return "please @ the user you'd like to find the uid of."

    username = username[1:]
    try:
        channel = api.get_channel(username)
    except MixerExceptions.NotFound:
        return "failed to detect user information."

    return "@{} user id is: {}".format(username, channel.user.id)

@chat.commands
async def avatar(message):
    """Provides a user with a link to their Mixer avatar."""
    return "link to your avatar: {}".format(message.user_avatar)

@chat.commands
async def avatar(message, username):
    """Provides a link to the avatar of another Mixcord user."""

    if len(username) < 2 or username[:1] != "@":
        return "please @ the user you'd like to find the uid of."

    username = username[1:]
    try:
        channel = api.get_channel(username)
    except MixerExceptions.NotFound:
        return "failed to detect user information."

    return "link to @{} avatar: {}".format(username, channel.user.avatarUrl)

@chat.commands
async def flip(message):
    """Flips a coin to determine if it'll land on heads or tails."""
    choice = random.randint(0, 1)
    desc = "heads" if choice else "tails"
    return "flipped a coin and picked: " + desc

@chat.commands
async def add(message, number1, number2):
    """Adds number1 and number2 together and outputs the sum."""
    try:
        sum = float(number1) + float(number2)
        return "sum = " + str(sum)
    except:
        return "failed to add provided values."

@chat.commands
async def subtract(message, number1, number2):
    """Subtracts number2 from number1 and outputs the difference."""
    try:
        diff = float(number1) - float(number2)
        return "difference = " + str(diff)
    except:
        return "failed to subtract provided values."

@chat.commands
async def multiply(message, number1, number2):
    """Multiplies number1 and number2 and outputs the product."""
    try:
        prod = float(number1) * float(number2)
        return "product = " + str(prod)
    except:
        return "failed to multiply provided values."

@chat.commands
async def divide(message, number1, number2):
    """Divides number1 by number2 and outputs the quotient."""
    try:
        quot = float(number1) / float(number2)
        return "quotient = " + str(quot)
    except:
        return "failed to divide provided values."

@chat.commands
async def modulus(message, number1, number2):
    """Products the remainder of the result of number1 divided by number2."""
    try:
        rem = float(number1) % float(number2)
        return "remainder = " + str(rem)
    except:
        return "failed to perform modulo operation on provided values."

@chat.commands
async def btc(message, currency):
    """Gets the price of BTC given a currency code. (supported: usd, gbp, eur)"""

    try:
        response = requests.get("https://api.coindesk.com/v1/bpi/currentprice.json")
        all_prices = response.json()["bpi"]
    except:
        return "failed to parse data from coindesk api."

    price = all_prices.get(currency.upper())
    if price is None:
        return "unrecognized currency code."

    return "The price of BTC in {} is {}".format(currency.upper(), price["rate"])

@chat.commands
async def lunch(message):

    if not message.has_role("Owner"):
        return "permission denied. only owner can use 'lunch' command."

    await chat.send_method_packet(
        "vote:start",
        "What should I get for lunch?",
        ["Chinese Food", "Mexican Food", "Pizza"], 30)

    return "starting poll for lunch... cast your vote!"

# trigerred when the mixer bot is connected + authenticated
@chat
async def on_ready(username, user_id): #
    print("mixer logged in: {} (uid = {})".format(username, user_id))
    await chat.send_message("mixcord logged in successfully!")

# trigerred when a user joins the stream
@chat
async def user_joined(data):
    await chat.send_message("welcome to the stream, @" + data["username"], data["username"])

async def follow_triggered(packet, payload):
    message = "@{} ".format(payload["user"]["username"])
    message += "thanks for following!" if payload["following"] else "why'd you unfollow :("
    await chat.send_message(message)

async def skill_triggered(packet, payload):
    user = api.get_user(payload["triggeringUserId"])
    await chat.send_message("@{} just used a whopping {} {}".format(user.username, payload["price"], payload["currencyType"].lower()))

async def broadcast_triggered(packet, payload):

    if not "online" in payload: return

    if payload["online"]:
        await send_announcement("{} is now online: https://mixer.com/{}".format(channel.token, channel.token))
        await chat.send_message("@{} has gone online!".format(channel.token))
    else:
        await chat.send_message("@{} has gone offline :(".format(channel.token))

# triggered when constellation websocket connection is established
# this function should be used to subscribe to events
async def constellation_connected(constellation):

    # subscribe to follow/unfollow event
    event_name = "channel:{}:followed".format(channel.id)
    await constellation.subscribe(event_name, follow_triggered)

    # subscribe to skill event
    event_name = "channel:{}:skill".format(channel.id)
    await constellation.subscribe(event_name, skill_triggered)

    # subscribe to chanenl update event
    event_name = "channel:{}:broadcast".format(channel.id)
    await constellation.subscribe(event_name, broadcast_triggered)

# initialize constellation manager w/ connected callback
constellation = MixerConstellation(constellation_connected)

# add event to update settings file when tokens are refreshed
def update_tokens(access_token, refresh_token):
    settings_all["mixer"]["access_token"] = access_token
    settings_all["mixer"]["refresh_token"] = refresh_token
    settings_cfg = json.dumps(settings_all, indent = 4)
    utils.write_all_text("settings.cfg", settings_cfg)
    print("access_token and refresh_token have been updated automatically.")
auth.refreshed_events.append(update_tokens)
