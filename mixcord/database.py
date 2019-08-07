import sqlite3
from enum import Enum

# database initialization
db = sqlite3.connect('mixcord.db')
db.row_factory = sqlite3.Row # fetched rows will have values mapped to column names
db.isolation_level = None # automatically commit changes to db
cursor = db.cursor()

class IDType(Enum):
    USER = 1
    CHANNEL = 2
    DISCORD = 3

def column_from_type(id_type):
    columns = {
        IDType.USER: "user_id",
        IDType.CHANNEL: "channel_id",
        IDType.DISCORD: "discord_id"
    }
    return columns.get(id_type)

def insert_user(user_id, channel_id, discord_id):
    query = "INSERT INTO mixcord (user_id, channel_id, discord_id) VALUES (?, ?, ?)"
    params = (user_id, channel_id, discord_id)
    cursor.execute(query, params)

def update_tokens(id, access_token, refresh_token, expires, id_type = 1):
    column = column_from_type(id_type)
    query = "UPDATE mixcord SET access_token = ?, refresh_token = ?, expires = ? WHERE ? = ?"
    params = (access_token, refresh_token, expires, column, id)
    cursor.execute(query, params)

def get_user(id, id_type = 1):
    column = column_from_type(id_type)
    cursor.execute("SELECT * FROM mixcord WHERE ? = ?", (column, id))
    return cursor.fetchone()

def init():

    def table_exists(name):
        query = "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?"
        params = (name,)
        cursor.execute(query, params)
        return cursor.fetchone() is not None

    # create the mixcord table, if it doesnt exist
    if not table_exists("mixcord"):
        cursor.execute("""
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
