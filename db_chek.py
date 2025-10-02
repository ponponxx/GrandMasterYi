import pandas as pd
import sqlite3
import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

def db_get_table():
    conn = sqlite3.connect("iching.db")
    cursor = conn.cursor()

    # 查詢所有的資料表名稱
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    print("資料表清單：")
    for t in tables:
        print(t[0])
    conn.close()
    return

def db_pull_rows(num,sheet): #拉特定表的前幾Row
    conn = sqlite3.connect("iching.db")
    df = pd.read_sql_query("SELECT * FROM " + sheet +" LIMIT "+str(num)+";", conn)  # 看前 num 筆 
    df.to_excel("preview.xlsx", index=False)
    conn.close()
    return

def db_pull_lines_by_hexid(hex_id, num=10):  #拉特定掛的爻辭Rows
    conn = sqlite3.connect("iching.db")
    query = f"SELECT * FROM lines WHERE hexagram_id = ? LIMIT {num};"
    df = pd.read_sql_query(query, conn, params=(hex_id,))
    conn.close()
    print(df)
    return df

def db_pull_hex_by_id(num):
    conn = sqlite3.connect("iching.db")
    cursor = conn.cursor()
    # 查乾卦
    cursor.execute(f"SELECT name, judgment FROM hexagrams WHERE id={num}")
    print(cursor.fetchone())
    conn.close()
    return


def AI_write_hexagram_5_hints(hexid):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    conn = sqlite3.connect("iching.db")
    cursor = conn.cursor()

    # 抓該卦的 6 爻辭
    cursor.execute("""
        SELECT position_num, text 
        FROM lines 
        WHERE hexagram_id=? 
        ORDER BY position_num
    """, (hexid,))
    lines_text = cursor.fetchall()

    for position_num, text in lines_text:
        hints = {}
        for hint_type in ["可能是什麼樣的人", "可能發生什麼樣的事", "可能是什麼時候或需要經過多久", "可能是哪裡或可能是哪個方位", "可能是什麼東西"]:
            prompt = f"爻辭：「{text}」\n請回覆此爻辭對「{hint_type}」的意義。"

            response = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一個易經大師，正在協助學生整理爻辭對於要預測:可能是什麼樣的人,可能是什麼樣的事情,可能是什麼時間或需要多少時間,可能是什麼地方或什麼方向,可能是什麼東西的提示，請只回復提示，控制在15字以內。"
                    },
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=3000
            )
            hints[hint_type] = response.choices[0].message.content.strip()
            print(response.choices[0].message.content.strip())

        # 更新寫入 DB
        cursor.execute("""
            UPDATE lines
            SET person_hint = ?,
                event_hint = ?,
                time_hint = ?,
                place_hint = ?,
                object_hint = ?
            WHERE hexagram_id = ? AND position_num = ?;
        """, (
            hints["人"],
            hints["事"],
            hints["時"],
            hints["地"],
            hints["物"],
            hexid,
            position_num
        ))

    conn.commit()
    conn.close()
    print(f"✅ 已完成 hexagram_id={hexid} 的 6 爻人事時地物寫入")

    return

TA = "hexagrams"
TB = "lines"
#db_get_table()
#db_pull_rows(300,TB)
#db_pull_hex_by_id(10)
#db_pull_lines_by_hexid(29)
AI_write_hexagram_5_hints(29)

