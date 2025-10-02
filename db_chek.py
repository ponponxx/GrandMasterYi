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
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位精通《易經》與《十翼》的大師，專責將卦辭與爻辭轉換為「提示詞」。輸出規則：1.僅輸出提示詞，不要解釋。2. 提示詞必須具象但帶有象徵性（如:長者,高階管理人,小商販,謹慎之人 或 難題,突破,驚喜,分離,雨降  或 數天,數周,春天,下半年,第一季 或 東方,高處,隱藏之處,水流之處 或 石頭,繩索,車輛,箱子 ）。3. 提供最多四個提示,不要換行。 4. 不要加任何前綴或後綴，只輸出提示詞本身。"
                    },
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=5000
            )
            hints[hint_type] = response.choices[0].message.content.strip()
            print("prompt= "+ prompt + "\n" + "Response:" +response.choices[0].message.content.strip() + "Usage : completion_token," + str(response.usage.completion_tokens) + " / prompt_token,"+ str(response.usage.prompt_tokens))

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
            hints["可能是什麼樣的人"],
            hints["可能發生什麼樣的事"],
            hints["可能是什麼時候或需要經過多久"],
            hints["可能是哪裡或可能是哪個方位"],
            hints["可能是什麼東西"],
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
db_pull_rows(300,TB)
#db_pull_hex_by_id(10)
#db_pull_lines_by_hexid(29)
#AI_write_hexagram_5_hints(29)

