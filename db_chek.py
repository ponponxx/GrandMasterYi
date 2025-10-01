import pandas as pd
import sqlite3

def dbpullalll(num):
    conn = sqlite3.connect("iching.db")
    df = pd.read_sql_query("SELECT * FROM hexagrams LIMIT "+str(num)+";", conn)  # 看前 num 筆 
    print(df)
    conn.close()
    return

def dbgetdata():
    conn = sqlite3.connect("iching.db")
    cursor = conn.cursor()
    # 查乾卦
    cursor.execute("SELECT name, judgment FROM hexagrams WHERE id=50")
    print(cursor.fetchone())
    # 查乾卦九二
    cursor.execute("SELECT position, text FROM lines WHERE hexagram_id=50 AND position='六五'")
    print(cursor.fetchone())
    conn.close()
    return

dbpullalll(30)
