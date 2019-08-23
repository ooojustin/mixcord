import sys
sys.path.append("..")

# logging initialization
import logging
log = logging.getLogger("discord")

from __main__ import settings, database
import discord, asyncio, json, utils
from discord.ext import commands

# import mixer api and mixer chatbot from bots.mixer module
from bots.mixer import api as api
from bots.mixer import chat as mixer_chat
from bots.mixer import channel as channel

# initialize discord bot
bot = commands.Bot(command_prefix = '>')

async def send_announcement(message):
    guild = bot.get_guild(settings["discord"]["guild"])
    channel = discord.utils.get(guild.text_channels, name = "announcements")
    await channel.send("@everyone " + message)

@bot.event
async def on_ready():
    print('discord logged in:', bot.user)

@bot.command()
async def link(ctx):
    await ctx.send("https://mixer.com/" + channel.username)

@bot.command()
async def leaderboard_jarks(ctx):
    data = await database._fetchall("SELECT * FROM users ORDER BY balance DESC LIMIT 10")
    message = ""
    for i in range(len(data)):
        row = data[i]
        place = i + 1
        member = await bot.fetch_user(row["discord"])
        if member is not None:
            username = member.mention
        else:
            user = await api.get_user(row["id"])
            username = "**{}**".format(user.username)
        message += "{} is in {}{} place w/ {} jarks\n".format(username, place, utils.num_suffix(place), row["balance"])
    await ctx.send(message)

@bot.command()
async def leaderboard(ctx):
    leaderboard = await channel.get_leaderboard('sparks-weekly')
    message = ""
    for i in range(len(leaderboard)):
        leader = leaderboard[i]
        user_id = leader["userId"]
        username = leader["username"]
        sparks = leader["statValue"]
        place = i + 1
        mixcord_user = await database.get_user(user_id)
        if mixcord_user is not None:
            member = bot.get_user(mixcord_user["discord"])
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
