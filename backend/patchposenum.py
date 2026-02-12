import sqlite3

# 爻位 → 數字 對應表
map_position = {
    "初": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "上": 6,
    "用": 7
}

def get_position_num(pos_text: str):
    """把 '初九', '九二', '六三', '上九', '用九' 轉成 1~7"""
    if pos_text.startswith("初"):
        return 1
    if pos_text.startswith("上"):
        return 6
    if pos_text.startswith("用"):
        return 7
    # 第二個字決定爻位
    if len(pos_text) >= 2:
        key = pos_text[1]
        return map_position.get(key, None)
    return None

# 開啟 DB
conn = sqlite3.connect("iching.db")
cursor = conn.cursor()

# 嘗試新增欄位（如果已存在就略過）
try:
    cursor.execute("ALTER TABLE lines ADD COLUMN position_num INTEGER;")
    print("✅ 已新增 position_num 欄位")
except sqlite3.OperationalError:
    print("⚠️ 欄位已存在，略過新增")

# 更新每一列
cursor.execute("SELECT id, position FROM lines")
rows = cursor.fetchall()
for line_id, pos in rows:
    pos_num = get_position_num(pos)
    if pos_num is not None:
        cursor.execute("UPDATE lines SET position_num=? WHERE id=?", (pos_num, line_id))

conn.commit()
conn.close()

print("🎉 已修正所有 position_num")
