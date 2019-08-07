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
channel = api.get_channel(settings["username"])
chat = MixerChat(api, channel.id)

# import discord bot from bots.discord module
from bots.discord import send_announcement
from bots.discord import bot as discord

@chat.commands
async def help(data):
    """Displays a list of commands that can be used in the chat."""

    command_count = 0
    command_names = list()

    # build a list of command names/descriptions with params
    for name, commands in chat.commands.commands.items():

        variants = list()

        for command in commands:

            if command["description"] is None:
                continue

            command_count += 1
            variants.append(str(command["param_count"]))

        if len(variants) == 0:
            continue
        elif len(variants) == 1:
            command_names.append(name)
        else:
            param_counts = ", ".join(variants)
            command_names.append("{} ({})".format(name, param_counts))

    # delete original >help message
    await chat.delete_message(data["id"])

    # formate response messages
    message1 = "There are a total of {} commands: {}."
    message2 = "To see information about a specific command, use '{}help command_name'."
    message1 = message1.format(command_count, ", ".join(command_names))
    message2 = message2.format(chat.commands.prefix)

    # whisper formatted response messages to used
    await chat.send_message(message1, data["user_name"])
    await asyncio.sleep(.5) # wait before sending second message :p
    await chat.send_message(message2, data["user_name"])

@chat.commands
async def help(data, name):
    """Provides a description of a specific command."""
    name = name.lower()
    return chat.commands.get_help(name)

@chat.commands
async def help(data, name, parameter_count_or_name):
    """Provides a description of a command given a parameter count or parameter name."""

    # if the second parameter is numeric, assume they're specifying parameter count
    name = name.lower()
    if utils.is_number(parameter_count_or_name):
        return chat.commands.get_help(name, int(parameter_count_or_name))

    # fallback to get_help command if it doesnt exist
    if not name in chat.commands.commands:
        return chat.commands.get_help(name)

    # try to find a definition of the specified command with the given parameter name
    for command in chat.commands.commands[name]:
        if parameter_count_or_name in command["params"]:
            return chat.commands.get_help(name, command["param_count"])
    return "no variation of command '{}' has parameter named '{}'.".format(name, parameter_count_or_name)

@chat.commands
async def shutdown(data):

    # make sure the person triggering the command is stream owner
    if not "Owner" in data["user_roles"]:
        return "permission denied. only owner can use 'shutdown' command."

    # shutdown the bot
    await chat.send_message("bot shutting down...")
    await asyncio.sleep(.5) # wait before exiting
    sys.exit(0)

@chat.commands
async def restart(data):

    # make sure the person triggering the command is stream owner
    if not "Owner" in data["user_roles"]:
        return "permission denied. only owner can use 'restart' command."

    # restart the bot
    await chat.send_message("bot restarting... wait a few seconds")
    await asyncio.sleep(.5) # wait before restarting

    # modify arguments and use execl to execute python module
    sys.argv.insert(0, '"{}"'.format(sys.executable))
    os.execl(sys.executable, *sys.argv)

@chat.commands
async def announce(data, message):

    # make sure the person triggering the command is stream owner
    if not "Owner" in data["user_roles"]:
        return "permission denied. only owner can use 'announce' command."

    await send_announcement(message)
    return "announcement has been sent."

@chat.commands
async def uptime(data):
    """Displays how long the streamer has been live for."""

    # get uptime and check if online
    uptime = api.get_uptime(channel.id)
    if uptime is None:
        return channel.token + " is not currently online."

    # return formatted uptime
    return channel.token + " has been live for: " + str(uptime)

@chat.commands
async def ping(data):
    """Returns 'pong!'"""
    return "pong!"

@chat.commands
async def uid(data):
    """Tells a user their unique user id on Mixer."""
    return "your user id is: {}".format(data["user_id"])

@chat.commands
async def uid(data, username):
    """Tells a user the unique user id of a tagged user on Mixer."""

    if len(username) < 2 or username[:1] != "@":
        return "please @ the user you'd like to find the uid of."

    username = username[1:]
    try:
        channel = api.get_channel(username)
    except MixerExceptions.NotFoundException:
        return "failed to detect user information."

    return "@{} user id is: {}".format(username, channel.user.id)

@chat.commands
async def avatar(data):
    """Provides a user with a link to their Mixer avatar."""
    return "link to your avatar: {}".format(data["user_avatar"])

@chat.commands
async def flip(data):
    """Flips a coin to determine if it'll land on heads or tails."""
    choice = random.randint(0, 1)
    desc = "heads" if choice else "tails"
    return "flipped a coin and picked: " + desc

@chat.commands
async def add(data, n1, n2):
    """Adds 2 numbers together and outputs the sum."""

    # make sure both inputs are numeric before trying to use them as floats
    if not utils.is_number(n1) or not utils.is_number(n2):
        return "please ensure both parameters are numeric."

    # return the sum of the numbers
    sum = float(n1) + float(n2)
    return "sum = " + str(sum)

@chat.commands
async def btc(data, currency):
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
async def lunch(data):

    if not "Owner" in data["user_roles"]:
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
    username = user["username"]
    await chat.send_message("@{} just used a whopping {} {}".format(username, payload["price"], payload["currencyType"].lower()))

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
    settings["mixer"]["access_token"] = access_token
    settings["mixer"]["refresh_token"] = refresh_token
    settings_cfg = json.dumps(settings, indent = 4)
    utils.write_all_text("settings.cfg", settings_cfg)
    print("access_token and refresh_token have been updated automatically.")
auth.refreshed_events.append(update_tokens)
