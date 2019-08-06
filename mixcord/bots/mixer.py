import sys
sys.path.append("..")

from __main__ import settings
from mixer import MixerAPI, MixerChat, MixerConstellation
import random, utils, json, asyncio, os

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
    print("access_token and refresh_token have been updated automatically.")

# initialize chatbot
channel = mixer.get_channel(settings["mixer"]["username"])
bot = MixerChat(mixer, channel["id"])

# import discord bot from bots.discord module
from bots.discord import send_announcement
from bots.discord import bot as discord

@bot.commands
async def help(data):
    """Displays a list of commands that can be used in the chat."""

    command_count = 0
    command_names = list()

    # build a list of command names/descriptions with params
    for name, commands in bot.commands.commands.items():

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
    await bot.delete_message(data["id"])

    # formate response messages
    message1 = "There are a total of {} commands: {}."
    message2 = "To see information about a specific command, use '{}help command_name'."
    message1 = message1.format(command_count, ", ".join(command_names))
    message2 = message2.format(bot.commands.prefix)

    # whisper formatted response messages to used
    await bot.send_message(message1, data["user_name"])
    await asyncio.sleep(.5) # wait before sending second message :p
    await bot.send_message(message2, data["user_name"])

@bot.commands
async def help(data, name):
    """Provides a description of a specific command."""
    return bot.commands.get_help(name)

@bot.commands
async def help(data, name, parameter_count_or_name):
    """Provides a description of a command given a parameter count or parameter name."""

    # if the second parameter is numeric, assume they're specifying parameter count
    if utils.is_number(parameter_count_or_name):
        return bot.commands.get_help(name, int(parameter_count_or_name))

    # fallback to get_help command if it doesnt exist
    if not name in bot.commands.commands:
        return bot.commands.get_help(name)

    # try to find a definition of the specified command with the given parameter name
    for command in bot.commands.commands[name]:
        if parameter_count_or_name in command["params"]:
            return bot.commands.get_help(name, command["param_count"])
    return "no variation of command '{}' has parameter named '{}'.".format(name, parameter_count_or_name)

@bot.commands
async def restart(data):

    # make sure the person triggering the command is stream owner
    if not "Owner" in data["user_roles"]:
        return "permission denied. only owner can use 'announce' command."

    # restart the bot
    await bot.send_message("bot restarting... wait a few seconds")
    sys.argv.insert(0, '"{}"'.format(sys.executable))
    os.execl(sys.executable, *sys.argv)

@bot.commands
async def announce(data, message):

    # make sure the person triggering the command is stream owner
    if not "Owner" in data["user_roles"]:
        return "permission denied. only owner can use 'announce' command."

    await send_announcement(message)
    return "announcement has been sent."

@bot.commands
async def uptime(data):
    """Displays how long the streamer has been live for."""

    # get uptime and check if online
    uptime = mixer.get_uptime(channel["id"])
    if uptime is None:
        return channel["token"] + " is not currently online."

    # return formatted uptime
    return channel["token"] + " has been live for: " + str(uptime)

@bot.commands
async def ping(data):
    """Returns 'pong!'"""
    return "pong!"

@bot.commands
async def uid(data):
    """Tells a user their unique user id on Mixer."""
    return "your user id is: {}".format(data["user_id"])

@bot.commands
async def uid(data, username):
    """Tells a user the unique user id of a tagged user on Mixer."""

    if len(username) < 2 or username[:1] != "@":
        return "please @ the user you'd like to find the uid of."

    username = username[1:]
    channel = mixer.get_channel(username)
    if not "user" in channel:
        return "failed to detect user information."

    return "@{} user id is: {}".format(username, channel["user"]["id"])

@bot.commands
async def avatar(data):
    """Provides a user with a link to their Mixer avatar."""
    return "link to your avatar: {}".format(data["user_avatar"])

@bot.commands
async def flip(data):
    """Flips a coin to determine if it'll land on heads or tails."""
    choice = random.randint(0, 1)
    desc = "heads" if choice else "tails"
    return "flipped a coin and picked: " + desc

@bot.commands
async def add(data, n1, n2):
    """Adds 2 numbers together and outputs the sum."""

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
        await send_announcement("{} is now online: https://mixer.com/{}".format(channel["token"], channel["token"]))
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
