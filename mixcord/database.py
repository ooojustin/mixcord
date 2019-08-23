import asyncio
import aiosqlite
from enum import Enum

db = None
cursor = None
loop = asyncio.get_event_loop()

class IDType(Enum):
    USER = 1
    CHANNEL = 2
    DISCORD = 3

async def _init():

    # initialize db/cursor
    global db, cursor
    db = await aiosqlite.connect("mixcord.db",
        loop = loop,
        isolation_level = None
    )
    db.row_factory = aiosqlite.Row # ??? maybe
    cursor = await db.cursor()

    # func to check if a table exists
    async def table_exists(name):
        query = "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?"
        params = (name,)
        await cursor.execute(query, params)
        return await cursor.fetchone()

    # create the mixcord table, if it doesnt exist
    if not await table_exists("mixcord"):
        await cursor.execute("""
        CREATE TABLE "mixcord" (
        	"id"	INTEGER PRIMARY KEY AUTOINCREMENT,
        	"user_id"	INTEGER UNIQUE,
            "channel_id" INTEGER UNIQUE,
        	"discord_id"	INTEGER UNIQUE,
            "balance"	INTEGER DEFAULT 1000,
        	"access_token"	TEXT,
        	"refresh_token"	TEXT,
        	"expires"	INTEGER DEFAULT 0
        )
        """)

def column_from_type(id_type):
    columns = {
        IDType.USER: "user_id",
        IDType.CHANNEL: "channel_id",
        IDType.DISCORD: "discord_id"
    }
    id_type = IDType(id_type)
    return columns.get(id_type)

async def get_user(id, id_type = 1):
    column = column_from_type(id_type)
    query = "SELECT * FROM mixcord WHERE {} = ?".format(column)
    await cursor.execute(query, (id,))
    return await cursor.fetchone()

async def insert_user(user_id, channel_id, discord_id):
    query = "INSERT INTO mixcord (user_id, channel_id, discord_id) VALUES (?, ?, ?)"
    params = (user_id, channel_id, discord_id)
    await cursor.execute(query, params)

async def update_tokens(id, access_token, refresh_token, expires, id_type = 1):
    column = column_from_type(id_type)
    query = "UPDATE mixcord SET access_token = ?, refresh_token = ?, expires = ? WHERE {} = ?".format(column)
    params = (access_token, refresh_token, expires, id)
    await cursor.execute(query, params)

async def add_balance(id, amount, id_type = 1):
    column = column_from_type(id_type)
    query = "UPDATE mixcord SET balance = balance + ? WHERE {} = ?".format(column)
    params = (amount, id)
    await cursor.execute(query, params)

def init():
    loop.run_until_complete(_init())
