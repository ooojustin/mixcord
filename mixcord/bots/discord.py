import sys
sys.path.append("..")

# logging initialization
import logging
log = logging.getLogger("discord")

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
