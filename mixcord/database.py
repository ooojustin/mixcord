import asyncio
import aiosqlite
from enum import Enum

db = None
cursor = None
loop = asyncio.get_event_loop()

# <editor-fold> ID Types
class IDType(Enum):
    USER = "id"
    CHANNEL = "channel"
    DISCORD = "discord"

# if it's an IDType, get the value - otherise, just use the string
idtype_column = lambda x: x.value if isinstance(x, IDType) else x
# </editor-fold>

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
    if not await table_exists("users"):
        await cursor.execute("""
            CREATE TABLE "users" (
            	"id"	INTEGER NOT NULL UNIQUE,
            	"channel"	INTEGER NOT NULL UNIQUE,
            	"balance"	INTEGER NOT NULL DEFAULT 0,
            	"discord"	INTEGER DEFAULT NULL,
            	"access_token"	TEXT DEFAULT NULL,
            	"refresh_token"	TEXT DEFAULT NULL,
            	"expires"	INTEGER DEFAULT NULL,
            	PRIMARY KEY("id")
            );
        """)

async def get_user(id, id_type = "id"):
    column = idtype_column(id_type)
    query = "SELECT * FROM users WHERE {} = ?".format(column)
    await cursor.execute(query, (id,))
    return await cursor.fetchone()

async def insert_user(user_id, channel_id, discord_id = None):
    query = "INSERT INTO users (id, channel_id, discord_id) VALUES (?, ?, ?)"
    params = (user_id, channel_id, discord_id)
    await cursor.execute(query, params)

async def update_tokens(id, access_token, refresh_token, expires, id_type = "id"):
    column = idtype_column(id_type)
    query = "UPDATE users SET access_token = ?, refresh_token = ?, expires = ? WHERE {} = ?".format(column)
    params = (access_token, refresh_token, expires, id)
    await cursor.execute(query, params)

async def add_balance(id, amount, id_type = "id"):
    column = idtype_column(id_type)
    query = "UPDATE users SET balance = balance + ? WHERE {} = ?".format(column)
    params = (amount, id)
    await cursor.execute(query, params)

def init():
    loop.run_until_complete(_init())
