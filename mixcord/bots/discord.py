import sys
sys.path.append("..")

from __main__ import settings, database
from database import cursor as db_cursor
import discord, asyncio, json, utils
from discord.ext import commands

# import mixer api and mixer chatbot from bots.mixer module
from bots.mixer import api as api
from bots.mixer import chat as mixer_chat
from bots.mixer import channel as channel

# initialize discord bot
bot = commands.Bot(command_prefix = '>')

@bot.command()
async def leaderboard_jarks(ctx):
    db_cursor.execute("SELECT * FROM mixcord ORDER BY balance DESC LIMIT 10")
    data = db_cursor.fetchall()
    message = ""
    for i in range(len(data)):
        row = data[i]
        place = i + 1
        member = bot.get_user(row["discord_id"])
        if not member is None:
            username = member.mention
        else:
            username = "**{}**".format(api.get_user(row["user_id"]).username)
        message += "{} is in {}{} place w/ {} jarks\n".format(username, place, utils.num_suffix(place), row["balance"])
    await ctx.send(message)

@bot.command()
async def link(ctx):
    await ctx.send("https://mixer.com/" + channel.username)

@bot.command()
async def leaderboard(ctx):
    leaderboard = channel.get_leaderboard('sparks-weekly')
    message = ""
    for i in range(len(leaderboard)):
        leader = leaderboard[i]
        user_id = leader["userId"]
        username = leader["username"]
        sparks = leader["statValue"]
        place = i + 1
        mixcord_user = database.get_user(user_id)
        if mixcord_user is not None:
            member = bot.get_user(mixcord_user["discord_id"])
            username = "**{}**".format(username) if member is None else member.mention
        else:
            username = "**{}**".format(username)
        message += "{} is in {}{} place w/ {} sparks\n".format(username, place, utils.num_suffix(place), sparks)
    await ctx.send(message)

@bot.command()
async def uptime(ctx):

    # get uptime and check if online
    uptime = channel.get_uptime()
    if uptime is None:
        await ctx.send(channel.username + " is not currently online.")
        return

    # return formatted uptime
    await ctx.send(channel.username + " has been live for: " + str(uptime))

# triggered when the discord bot is connected + authenticated
@bot.event
async def on_ready():
    print('discord logged in:', bot.user)

# triggered when !mixcord command is executed in discord
@bot.command()
async def mixcord(ctx):

    # make sure discord id isn't already in database
    discord_id = ctx.author.id
    if database.get_user(discord_id, database.IDType.DISCORD) is not None:
        await ctx.author.send("You've already linked your Mixer account via mixcord.")
        return

    # get shortcode stuff from mixer
    shortcode = await api.get_shortcode()
    code = shortcode["code"]
    handle = shortcode["handle"]

    # tell the user what to do to link their mixer account
    await ctx.author.send("Visit the following page to link your Mixer: <https://mixer.com/go?code={}>".format(code))

    # poll shortcode checking endpoint with handle until we can move on with authorization_code
    while True:
        await asyncio.sleep(10)
        response = await api.check_shortcode(handle)
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

    tokens = await api.get_token(authorization_code)
    token_data = await api.check_token(tokens["access_token"])
    user = await api.get_user(token_data["sub"])

    database.insert_user(user.id, user.channel.id, discord_id)
    database.update_tokens(discord_id, tokens["access_token"], tokens["refresh_token"], token_data["exp"], database.IDType.DISCORD)

    await ctx.author.send("Your Mixer account has been linked: " + user.username)
    await mixer_chat.send_message("@{} has linked their discord account: {}".format(user.username, ctx.author))

async def send_announcement(message):
    guild = bot.get_guild(settings["discord"]["guild"])
    channel = discord.utils.get(guild.text_channels, name = "announcements")
    await channel.send("@everyone " + message)
