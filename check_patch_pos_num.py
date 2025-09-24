import sqlite3
conn = sqlite3.connect("iching.db")
cursor = conn.cursor()

cursor.execute("SELECT hexagram_id, position, position_num FROM lines LIMIT 100")
for row in cursor.fetchall():
    print(row)

conn.close()