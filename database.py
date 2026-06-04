import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY AUTOINCREMENT,
email TEXT,
first_name TEXT,
last_name TEXT,
age INTEGER,
phone TEXT
)
""")

conn.commit()
conn.close()

print("Database Created")