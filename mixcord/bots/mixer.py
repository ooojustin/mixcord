import sys
sys.path.append("..")

import random, utils, json, asyncio, os, requests
from threading import Timer
from time import time

from __main__ import database
from __main__ import settings as settings_all

settings = settings_all["mixer"]
currency_name = settings_all["mixcord"]["currency_name"]

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

    tags = message.get_tags()
    if len(tags) == 0:
        return "please @ a user."
    else: username = tags[0]

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

    tags = message.get_tags()
    if len(tags) == 0:
        return "please @ a user."
    else: username = tags[0]

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
async def bet(message, amount):
    """You have a 50% chance of doubling your bet, and a 50% chance of losing it."""

    try: amount = int(amount)
    except: return "invalid 'amount' provided."
    if amount <= 0: return "please enter a positive 'amount' to bet."

    # make sure their discord account is linked
    mixcord_user = database.get_user(message.user_id)
    if mixcord_user is None:
        return "your mixer account must be linked to your discord via mixcord to use this command."

    # make sure they have sufficient balance
    if mixcord_user["balance"] < amount:
        return "you have insufficient balance. ({}/{} {})".format(mixcord_user["balance"], amount, currency_name)

    won = random.randint(0, 1) == 1
    if won:
        database.add_balance(message.user_id, amount)
        return "you won :D you now have {} {}.".format((mixcord_user["balance"] + amount), currency_name)
    else:
        database.add_balance(message.user_id, -amount)
        return "you lost :( you now have {} {}.".format((mixcord_user["balance"] - amount), currency_name)

@chat.commands
async def bet(message, username, amount):
    """Challenge another member to a 50/50 coin flip! Winner takes the losers bet."""

    # make sure we have a tagged user
    tags = message.get_tags()
    if len(tags) == 0:
        return "please @ the user you're challenging/responding to."
    else:
        username = tags[0].lower()
        message.user_name = message.user_name.lower()

    mixcord_user = database.get_user(message.user_id)

    # handle if somebody is trying to accept or deny
    if amount == "accept" or amount == "deny":

        # get the pending bet
        bet = pending_bets.get(username)
        if bet is None or bet["username"] != message.user_name:
            return "failed to find the bet you're responding to."

        # delete the pending bet, because we're handling it
        del pending_bets[username]

        # if the user wants to deny the bet, don't do anything
        if amount == "deny":
            return "you have denied the pending bet from @{}.".format(username)

        # if the user wants to accept the bet, continue
        if amount == "accept":

            # make sure they have enough money to accept
            if bet["amount"] > mixcord_user["balance"]:
                return "you have insufficient funds to accept this bet."

            # make sure the issuer of the challenge still has enough money
            competitor = api.get_channel(username).user
            challenger_mixcord_user = database.get_user(competitor.id)
            if bet["amount"] > challenger_mixcord_user["balance"]:
                return "@{} no longer has sufficient funding to run this bet.".format(username)

            # determine winner/loser
            pick = random.randint(0, 1) == 1
            winner_id = competitor.id if pick else message.user_id
            loser_id = message.user_id if pick else  competitor.id
            winner_username = username if pick else message.user_name
            loser_username = message.user_name if pick else username

            # affect balances accordingly
            database.add_balance(winner_id, bet["amount"])
            database.add_balance(loser_id, -bet["amount"])

            # end the bet!
            await chat.send_message("@{} has won {} {}! better luck next time, @{}.".format(winner_username, bet["amount"], currency_name, loser_username))
            return None

    # if the amount isnt being written as "accept" or "deny", we're trying to start a new bet
    # make sure the amount is numeric by converting it to an int
    try: amount = int(amount)
    except: return "invalid 'amount' provided."
    if amount <= 0: return "please enter a positive 'amount' to bet."

    # make sure they're not trying to start a bet against themself :/
    if message.user_name == username:
        return "you're not able to start a bet against yourself."

    # make sure we don't already have a pending bet
    if pending_bets.get(message.user_name) is not None:
        return "you already have a pending bet."

    # make sure the challenger has enough money to start the bet
    if amount > mixcord_user["balance"]:
        return "you have insufficient funds to request this bet."

    # store challenge information
    pending_bets[message.user_name] = {
        "username": username,
        "amount": amount
    }

    # send messages indicating the challenge has been issued
    await chat.send_message("@{} has challenged @{} to a bet of {} {}!".format(message.user_name, username, amount, currency_name))
    await asyncio.sleep(0.5)
    await chat.send_message("use {}bet @{} [accept/deny] to respond to your pending bet!".format(chat.commands.prefix, message.user_name), username)

    # automatically timeout the bet in 30 seconds
    async def bet_timeout(username):
        await asyncio.sleep(30)
        bet = pending_bets.get(username)
        if bet is not None:
            del pending_bets[username]
            await chat.send_message("@{} your pending bet has timed out.".format(username))
    asyncio.ensure_future(bet_timeout(message.user_name))
pending_bets = dict()

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
    """Gets the price of BTC given a currency code. Run the 'btc_list' command to see all supported currencies."""

    try:
        response = requests.get("https://blockchain.info/ticker")
        prices = response.json()
    except:
        return "failed to parse data from coindesk api."

    price = prices.get(currency.upper())
    if price is None:
        return "unrecognized currency code."

    return "The price of BTC in {} is {}{}".format(currency.upper(), price["symbol"], price["15m"])

@chat.commands
async def btc_list(message):
    """Lists all currency codes supported by the 'btc' command."""

    try:
        response = requests.get("https://blockchain.info/ticker")
        prices = response.json()
    except:
        return "failed to parse data from coindesk api."

    currency_list = list(prices.keys())
    currencies = ", ".join(currency_list).lower()
    return "supported currencies: " + currencies

@chat.commands
async def balance(message):
    """Outputs a users balance."""
    mixcord_user = database.get_user(message.user_id)
    if mixcord_user is None:
        return "your mixer account must be linked to your discord via mixcord before tracking balance."
    return "you have {} {}".format(mixcord_user["balance"], currency_name)

@chat.commands
async def balance(message, username):
    """Outputs the balance of a tagged user."""

    tags = message.get_tags()
    if len(tags) == 0:
        return "please @ a user."
    else: username = tags[0]

    user = api.get_channel(username).user
    mixcord_user = database.get_user(user.id)
    balance = 0 if mixcord_user is None else mixcord_user["balance"]

    return "@{} has {} {}".format(username, balance, currency_name)

@chat.commands
async def lunch(message):

    if not message.has_role("Owner"):
        return "permission denied. only owner can use 'lunch' command."

    await chat.send_method_packet(
        "vote:start",
        "What should I get for lunch?",
        ["Chinese Food", "Mexican Food", "Pizza"], 30)

    return "starting poll for lunch... cast your vote!"

@chat.commands
async def jackpot(message):
    """Outputs information about the current jackpot, if there's one running."""

    if current_jackpot is None:
        return "a jackpot is not currently running."

    response = "a jackpot is active with {} competitors and a total of {} {}!".format(len(current_jackpot["users"]), current_jackpot["total"], currency_name)

    user = current_jackpot["users"].get(message.user_name)
    if user is not None:
        response += " you have a {}% chance of winning.".format(utils.get_percentage_str(user["amount"], current_jackpot["total"]))

    return response
current_jackpot = None

@chat.commands
async def jackpot_start(message, duration):

    if not message.has_role("Owner"):
        return "only the stream owner can start a jackpot."

    try: duration = int(duration)
    except:
        return "please enter a valid jackput duration in seconds."

    # start a jackpot
    global current_jackpot
    current_jackpot = {
        "started": time(),
        "ends": time() + duration,
        "total": 0,
        "users": dict()
    }

    # set a timeout for ending the jackpot
    async def jackpot_end():
        await asyncio.sleep(duration - 3)
        for i in range(3, 0, -1):
            await chat.send_message("jackpot ends in {} seconds...".format(i))
            await asyncio.sleep(1)
        global current_jackpot
        running_total = 0
        choice = random.randint(0, current_jackpot["total"])
        for username, user in current_jackpot["users"].items():
            running_total += user["amount"]
            if choice <= running_total:
                winner = user
                winner["username"] = username
                break
        chance = utils.get_percentage_str(winner["amount"], current_jackpot["total"])
        await chat.send_message("@{} won the jackpot with a {}% chance! total: {} {}".format(winner["username"], chance, current_jackpot["total"], currency_name))
        database.add_balance(winner["id"], current_jackpot["total"])
        current_jackpot = None
    asyncio.ensure_future(jackpot_end())

    return "jackpot has been started! it will end in {} seconds...".format(duration)

@chat.commands
async def deposit(message, amount):
    """Deposits specified amount of balance into the current jackpot."""

    try: amount = int(amount)
    except: return "invalid 'amount' provided."
    if amount <= 0: return "please enter a positive amount to bet."

    mixcord_user = database.get_user(message.user_id)
    if mixcord_user is None:
        return "your discord must be linked to your mixer via mixcord to participate in jackpots."

    if mixcord_user["balance"] < amount:
        return "you do not have sufficient funds to deposit that many {}.".format(currency_name)

    if current_jackpot is None:
        return "no jackpot is currently running."

    current_jackpot["total"] += amount
    database.add_balance(message.user_id, -amount)
    if message.user_name in current_jackpot["users"]:
        current_jackpot["users"][message.user_name]["amount"] += amount
        return "you have deposited an additional {} {} to total {} this pot.".format(amount, currency_name, current_jackpot["users"][message.user_name]["amount"])
    else:
        current_jackpot["users"][message.user_name] = {
            "id": message.user_id,
            "amount": amount
        }
        return "you have entered the pot with {} {}.".format(amount, currency_name)

# triggered when the mixer bot is connected + authenticated
@chat
async def on_ready(username, user_id): #
    print("mixer logged in: {} (uid = {})".format(username, user_id))
    await chat.send_message("mixcord logged in successfully!")

# triggered when a user joins the stream
@chat
async def user_joined(data):
    await chat.send_message("welcome to the stream, @" + data["username"])

# triggered when we receive any message (MixerChatMessage object)
@chat
async def handle_message(message):
    current_time = time()
    last_reward = last_rewards.get(message.user_name, 0)
    if current_time - last_reward >= 5 and not message.handled:
        database.add_balance(message.user_id, 5)
        last_rewards[message.user_name] = current_time
last_rewards = dict()

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
