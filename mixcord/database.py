import sqlite3

# database initialization
db = sqlite3.connect('mixcord.db')
db.row_factory = sqlite3.Row # fetched rows will have values mapped to column names
db.isolation_level = None # automatically commit changes to db
cursor = db.cursor()

def insert_user(user_id, channel_id, discord_id):
    query = "INSERT INTO mixcord (user_id, channel_id, discord_id) VALUES (?, ?, ?)"
    params = (user_id, channel_id, discord_id)
    cursor.execute(query, params)

def update_tokens(discord_id, access_token, refresh_token, expires):
    query = "UPDATE mixcord SET access_token = ?, refresh_token = ?, expires = ? WHERE discord_id = ?"
    params = (access_token, refresh_token, expires, discord_id)
    cursor.execute(query, params)

def user_from_discord(discord_id):
    cursor.execute("SELECT * FROM mixcord WHERE discord_id = ?", (discord_id,))
    return cursor.fetchone()

def user_from_mixer(user_id):
    cursor.execute("SELECT * FROM mixcord WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

def table_exists(name):
    query = "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?"
    params = (name,)
    cursor.execute(query, params)
    return cursor.fetchone() is not None

def init():

    # create the mixcord table, if it doesnt exist
    if not table_exists("mixcord"):
        cursor.execute("""
        CREATE TABLE "mixcord" (
        	"id"	INTEGER PRIMARY KEY AUTOINCREMENT,
        	"user_id"	INTEGER UNIQUE,
            "channel_id" INTEGER UNIQUE,
        	"discord_id"	INTEGER UNIQUE,
        	"access_token"	TEXT,
        	"refresh_token"	TEXT,
        	"expires"	INTEGER DEFAULT 0
        )
        """)
