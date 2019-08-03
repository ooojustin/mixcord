import sqlite3

# database initialization
db = sqlite3.connect('mixcord.db')
db.row_factory = sqlite3.Row # fetched rows will have values mapped to column names
db.isolation_level = None # automatically commit changes to db
cursor = db.cursor()

def table_exists(name):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cursor.fetchone() is not None

def init():

    # make sure the table for mixcord doesn't already exist
    if table_exists("mixcord"):
        return

    # execute the table creation query
    cursor.execute("""
    CREATE TABLE "mixcord" (
    	"id"	INTEGER PRIMARY KEY AUTOINCREMENT,
    	"username"	TEXT,
    	"discord"	INTEGER UNIQUE,
    	"access_token"	TEXT,
    	"refresh_token"	TEXT,
    	"token_expires"	INTEGER
    )
    """)
