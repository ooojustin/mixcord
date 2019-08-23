import sys
sys.path.append("..")

# logging initialization
import logging
log = logging.getLogger("mixer")

import random, json, asyncio, os, requests, utils
from threading import Timer
from time import time
import dateutil.parser

from __main__ import database
from __main__ import settings as settings_all

settings = settings_all["mixer"]
currency_name = settings_all["mixcord"]["currency_name"]

# TODO: the mixer module will *eventually* be installed via pypi
# i am temporarily spcifying the path during development of the wrapper
sys.path.append(R"C:\Users\justi\Documents\Programming\mixer.py")

# mixer imports
import mixer.exceptions as MixerExceptions
from mixer.api import MixerAPI
from mixer.constellation import MixerConstellation
from mixer.oauth import MixerOAuth
from mixer.chat import MixerChat
ParamType = MixerChat.ParamType

async def init():

    # variables we're setting in the mixer module
    global api, auth, channel, chat

    # initialize chatbot with oauth tokens if needed
    if not "access_token" in settings:
        import init_oauth
        await init_oauth.run()

    # function to update tokens saved in settings file
    def update_tokens(access_token, refresh_token):
        settings_all["mixer"]["access_token"] = access_token
        settings_all["mixer"]["refresh_token"] = refresh_token
        settings_cfg = json.dumps(settings_all, indent = 4)
        utils.write_all_text("settings.cfg", settings_cfg)
        print("access_token and refresh_token have been updated automatically.")

    # initialize general mixer api wrapper and oauth manager
    api = MixerAPI(settings["client-id"], settings["client-secret"])
    auth = await MixerOAuth.create(api, settings["access_token"], settings["refresh_token"])
    auth.on_refresh(update_tokens)
    await auth.ensure_active()
    auth.register_auto_refresh()

    # initialize chatbot
    try:
        channel = await api.get_channel(settings["username"])
        chat = await MixerChat.create(api, channel.id, command_prefix = ">")
    except MixerExceptions.NotFound:
        print("invalid account username specified in settings file.")
        sys.exit(1)

# run initialization code
# NOTE: this must be done before importing discord
loop = asyncio.get_event_loop()
loop.run_until_complete(init())

# discord imports (note: should be imported after init)
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
    uptime = await channel.get_uptime()
    if uptime is None:
        return channel.username + " is not currently online."

    # return formatted uptime
    return channel.username + " has been live for: " + str(uptime)

@chat.commands
async def ping(message):
    """Returns 'pong!'"""
    return "pong!"

@chat.commands
async def uid(message):
    """Tells a user their unique user id on Mixer."""
    return "your user id is: {}".format(message.user_id)

@chat.commands
async def uid(message, user: ParamType.MIXER_USER):
    """Tells a user the unique user id of a tagged user on Mixer."""
    return "@{} user id is: {}".format(user.username, user.id)

@chat.commands
async def avatar(message):
    """Provides a user with a link to their Mixer avatar."""
    return "link to your avatar: {}".format(message.user_avatar)

@chat.commands
async def avatar(message, user: ParamType.MIXER_USER):
    """Provides a link to the avatar of another Mixcord user."""
    return "link to @{} avatar: {}".format(user.username, user.avatarUrl)

@chat.commands
async def flip(message):
    """Flips a coin to determine if it'll land on heads or tails."""
    choice = random.randint(0, 1)
    desc = "heads" if choice else "tails"
    return "flipped a coin and picked: " + desc

@chat.commands
async def bet(message, amount):
    """You have a 50% chance of doubling your bet, and a 50% chance of losing it."""

    # make sure their discord account is linked
    mixcord_user = database.get_user(message.user_id)
    if mixcord_user is None:
        return "your mixer account must be linked to your discord via mixcord to use this command."

    # make sure they have sufficient balance
    if amount == "all":
        amount = mixcord_user["balance"]
        if amount == 0:
            return "amount must be a positive integer."
    else:
        amount = utils.get_positive_int(amount)
        if amount is None:
            return "amount must be a positive integer."
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
async def bet(message, user: ParamType.MIXER_USER, amount):
    """Challenge another member to a 50/50 coin flip! Winner takes the losers bet."""

    username = user.username.lower()
    username_sender = message.username.lower()

    mixcord_user = database.get_user(message.user_id)

    # handle if somebody is trying to accept or deny
    if amount == "accept" or amount == "deny":

        # get the pending bet
        bet = pending_bets.get(username)
        if bet is None or bet["username"] != username_sender:
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
            competitor_mixcord_user = database.get_user(user.id)
            if bet["amount"] > competitor_mixcord_user["balance"]:
                return "@{} no longer has sufficient funding to run this bet.".format(username)

            # determine winner/loser
            pick = random.randint(0, 1) == 1
            winner_id = user.id if pick else message.user_id
            loser_id = message.user_id if pick else  user.id
            winner_username = username if pick else username_sender
            loser_username = message.username if pick else username

            # affect balances accordingly
            database.add_balance(winner_id, bet["amount"])
            database.add_balance(loser_id, -bet["amount"])

            # end the bet!
            await chat.send_message("@{} has won {} {}! better luck next time, @{}.".format(winner_username, bet["amount"], currency_name, loser_username))
            return None

    # make sure the amount is numeric by converting it to an int
    amount = utils.get_positive_int(amount)
    if amount is None: return "amount must be a positive integer."

    # make sure they're not trying to start a bet against themself :/
    if message.username == username:
        return "you're not able to start a bet against yourself."

    # make sure we don't already have a pending bet
    if pending_bets.get(message.username) is not None:
        return "you already have a pending bet."

    # make sure the challenger has enough money to start the bet
    if amount > mixcord_user["balance"]:
        return "you have insufficient funds to request this bet."

    # store challenge information
    pending_bets[message.username] = {
        "username": username,
        "amount": amount
    }

    # send messages indicating the challenge has been issued
    await chat.send_message("@{} has challenged @{} to a bet of {} {}!".format(message.username, username, amount, currency_name))
    await asyncio.sleep(0.5)
    await chat.send_message("use {}bet @{} [accept/deny] to respond to your pending bet!".format(chat.commands.prefix, message.username), username)

    # automatically timeout the bet in 30 seconds
    async def bet_timeout(username):
        await asyncio.sleep(30)
        bet = pending_bets.get(username)
        if bet is not None:
            del pending_bets[username]
            await chat.send_message("@{} your pending bet has timed out.".format(username))
    asyncio.ensure_future(bet_timeout(message.username))
pending_bets = dict()

@chat.commands
async def add(message, number1: ParamType.NUMBER, number2: ParamType.NUMBER):
    """Adds number1 and number2 together and outputs the sum."""
    sum = number1 + number2
    return "sum = " + str(sum)

@chat.commands
async def subtract(message, number1: ParamType.NUMBER, number2: ParamType.NUMBER):
    """Subtracts number2 from number1 and outputs the difference."""
    diff = number1 - number2
    return "difference = " + str(diff)

@chat.commands
async def multiply(message, number1: ParamType.NUMBER, number2: ParamType.NUMBER):
    """Multiplies number1 and number2 and outputs the product."""
    prod = number1 * number2
    return "product = " + str(prod)

@chat.commands
async def divide(message, number1: ParamType.NUMBER, number2: ParamType.NUMBER):
    """Divides number1 by number2 and outputs the quotient."""
    try:
        quot = number1 / number2
        return "quotient = " + str(quot)
    except:
        return "failed to divide provided values."

@chat.commands
async def modulus(message, number1: ParamType.NUMBER, number2: ParamType.NUMBER):
    """Products the remainder of the result of number1 divided by number2."""
    try:
        rem = number1 % number2
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
async def balance(message, user: ParamType.MIXER_USER):
    """Outputs the balance of a tagged user."""
    mixcord_user = database.get_user(user.id)
    if mixcord_user is not None:
        return "@{} has {} {}".format(user.username, mixcord_user["balance"], currency_name)
    else:
        return "their mixer account must be linked to their discord before tracking balance."

@chat.commands
async def pay(message, user: ParamType.MIXER_USER, amount: ParamType.POSITIVE_NUMBER):
    """Send some of your balance to a tagged user."""

    receiver_mixcord = database.get_user(user.id)
    sender_mixcord = database.get_user(message.user_id)

    if sender_mixcord is None:
        return "your mixer account must be linked to your discord via mixcord before sending balance."
    elif receiver_mixcord is None:
        return "you can't send {} to @{} until they link their discord to their mixer via mixcord.".format(currency_name, user.username)

    amount = int(amount)
    if sender_mixcord["balance"] < amount:
        return "you have insufficient balance."

    database.add_balance(sender_mixcord["user_id"], -amount)
    database.add_balance(receiver_mixcord["user_id"], amount)
    return "you have successfully sent {} {} to @{}!".format(amount, currency_name, user.username)


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

    user = current_jackpot["users"].get(message.username) # users entry in jackpot
    response = "a jackpot is active with {} competitors and a total of {} {}!".format(len(current_jackpot["users"]), current_jackpot["total"], currency_name)

    if user is not None:
        response += " you have a {}% chance of winning.".format(utils.get_percentage_str(user["amount"], current_jackpot["total"]))

    time_left = int(current_jackpot["ends"] - time())
    response += " it ends in {} seconds...".format(time_left)

    return response
current_jackpot = None

@chat.commands
async def link(message):

    # make sure they're not already linked
    if await database.get_user(message.user_id):
        return "your mixer account is already linked to mixcord."

    # begin shortcode oauth process
    shortcode = await api.get_shortcode(["user:details:self"])
    code = shortcode["code"]
    handle = shortcode["handle"]
    authorization_code = None

    # tell the user what to do to link their mixer account
    link = "https://mixer.com/go?code=" + code
    await chat.send_message("Visit the following link: " + link, message.username)
    await asyncio.sleep(0.5)
    await chat.send_message("@{} i've whispered a super secret link to you.".format(message.username))

    # poll shortcode checking endpoint with handle until we can move on with authorization_code
    while not authorization_code:
        await asyncio.sleep(10)
        try:
            response = await api.check_shortcode(handle)
            authorization_code = response.get("code")
        except MixerExceptions.WebException as ex:
            if ex.status == 403:
                await chat.send_message("Auth failed: permission denied.", message.username)
                return
            elif ex.status == 404:
                await chat.send_message("Auth failed: verification timed out.", message.username)
                return

    auth = await MixerOAuth.create_from_authorization_code(api, authorization_code)
    user = await api.get_user(auth.user_id)
    discord = await api.get_user_service("discord", auth)

    await database.insert_user(user.id, user.channel.id, discord)
    await database.update_tokens(user.id, auth.access_token, auth.refresh_token)
    await chat.send_message("your mixer account has been linked!")


async def jackpot_end(duration):

    # countdown
    countdown = 3
    await asyncio.sleep(duration - countdown)
    for i in range(countdown, 0, -1):
        await chat.send_message("jackpot ends in {} seconds...".format(i))
        await asyncio.sleep(1)

    # make sure ppl are in the pot
    global current_jackpot
    if len(current_jackpot["users"]) == 0:
        await chat.send_message("nobody entered the jackpot so no winner was chosen :(")
        return

    # determine a winner
    running_total = 0
    choice = random.randint(1, current_jackpot["total"])
    for username, user in current_jackpot["users"].items():
        running_total += user["amount"]
        if choice <= running_total:
            winner = user
            winner["username"] = username
            break

    # notify the chat
    chance = utils.get_percentage_str(winner["amount"], current_jackpot["total"])
    await chat.send_message("@{} won the jackpot with a {}% chance! total: {} {}".format(winner["username"], chance, current_jackpot["total"], currency_name))

    # add balance to user and end current jackpot
    database.add_balance(winner["id"], current_jackpot["total"])
    current_jackpot = None

@chat.commands
async def jackpot_start(message, duration):

    if not message.has_role("Owner"):
        return "only the stream owner can start a jackpot."

    duration = utils.get_positive_int(duration)
    if duration is None: return "please enter a valid jackput duration in seconds."

    # start a jackpot
    global current_jackpot
    current_jackpot = {
        "started": time(),
        "ends": time() + duration,
        "total": 0,
        "users": dict()
    }

    # create a task to automatically end the jackpot and return
    coro = jackpot_end(duration)
    asyncio.create_task(coro)
    return "jackpot has been started! it will end in {} seconds...".format(duration)

@chat.commands
async def deposit(message, amount: ParamType.POSITIVE_NUMBER):
    """Deposits specified amount of balance into the current jackpot."""

    amount = int(amount)
    mixcord_user = database.get_user(message.user_id)
    if mixcord_user is None:
        return "your discord must be linked to your mixer via mixcord to participate in jackpots."

    if mixcord_user["balance"] < amount:
        return "you do not have sufficient funds to deposit that many {}.".format(currency_name)

    if current_jackpot is None:
        return "no jackpot is currently running."

    current_jackpot["total"] += amount
    database.add_balance(message.user_id, -amount)
    if message.username in current_jackpot["users"]:
        current_jackpot["users"][message.username]["amount"] += amount
        return "you have deposited an additional {} {} to total {} this pot.".format(amount, currency_name, current_jackpot["users"][message.username]["amount"])
    else:
        current_jackpot["users"][message.username] = {
            "id": message.user_id,
            "amount": amount
        }
        return "you have entered the pot with {} {}.".format(amount, currency_name)

@chat.commands
async def discord(message):
    return "here is a link to my discord server: https://justin.ooo/discord - use the '{}mixcord' command when you join!".format(chat.commands.prefix)

@chat.commands
async def registered(message):
    """Tells a used when they registered on Mixer."""
    user = api.get_user(message.user_id)
    registered = dateutil.parser.parse(user.createdAt)
    registered_str = registered.strftime("%B %Y day @ %I:%M %p (%Z)").lower()
    registered_str = registered_str.replace("day", str(registered.day) + utils.num_suffix(registered.day))
    return registered_str

@chat.commands
async def hotpotato_start(message, reward: ParamType.POSITIVE_NUMBER):
    chatters = api.get_chatters(channel.id)
    chatters = random.shuffle(chatters)
    hotpotato = {
        "reward": reward,
        "started": time(),
        "players": chatters
    }

    # TODO: make this work?
    async def hotpotato_next():
        pass
        # await asyncio.sleep(random.randint(1, 1))

    asyncio.ensure_future(hotpotato_next())
hotpotato = None

# triggered when the mixer bot is connected + authenticated
@chat
async def on_ready(username, user_id): #
    print("mixer logged in: {} (uid = {})".format(username, user_id))
    await chat.send_message("mixcord logged in successfully!")

# TODO: force user to leave game of hotpotato
@chat
async def user_left(data):
    pass

# triggered when a user joins the stream
@chat
async def user_joined(data):
    await chat.send_message("welcome to the stream, @" + data["username"])

# triggered when we receive any message (MixerChatMessage object)
@chat
async def handle_message(message):

    skill = message.skill
    if await database.get_user(message.user_id) is not None and skill is not None:
        if skill["currency"] == "Sparks":
            reward = int(skill["cost"] / 10)
            await database.add_balance(message.user_id, reward)
            await chat.send_message("thanks for using sparks! you've received {} {} as a reward.".format(reward, currency_name), message.username)

    current_time = time()
    last_reward = last_rewards.get(message.username, 0)
    if current_time - last_reward >= 5 and not message.handled:
        await database.add_balance(message.user_id, 5)
        last_rewards[message.username] = current_time
last_rewards = dict()

async def follow_triggered(packet, payload):
    message = "@{} ".format(payload["user"]["username"])
    message += "thanks for following!" if payload["following"] else "why'd you unfollow :("
    await chat.send_message(message)

async def skill_triggered(packet, payload):
    # payload: https://pastebin.com/R2rZzsja

    # announce skill in chat
    user_id = payload["triggeringUserId"]
    user = await api.get_user(user_id)
    await chat.send_message("@{} just used a whopping {} {}".format(user.username, payload["price"], payload["currencyType"].lower()))

    # reward them with balance (sparks / 10)
    if await database.get_user(user_id) is not None and payload["currencyType"] == "Sparks":
        reward = int(payload["price"] / 10)
        database.add_balance(user_id, reward)
        await chat.send_message("thanks for using sparks! you've received {} {} as a reward.".format(reward, currency_name), user.username)


async def broadcast_triggered(packet, payload):

    if not "online" in payload: return

    if payload["online"]:
        await send_announcement("{} is now online: https://mixer.com/{}".format(channel.username, channel.username))
        await chat.send_message("@{} has gone online!".format(channel.username))
    else:
        await chat.send_message("@{} has gone offline :(".format(channel.username))

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
