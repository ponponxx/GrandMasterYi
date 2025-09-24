import sqlite3

conn = sqlite3.connect("iching.db")
cursor = conn.cursor()

# 查乾卦
cursor.execute("SELECT name, judgment FROM hexagrams WHERE id=50")
print(cursor.fetchone())

# 查乾卦九二
cursor.execute("SELECT position, text FROM lines WHERE hexagram_id=50 AND position='六五'")
print(cursor.fetchone())

conn.close()