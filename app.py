import os
from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
import sqlite3
from xai_sdk import Client
from xai_sdk.chat import user, system
load_dotenv()  # 自動讀取 .env

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

user_sessions = {}

@app.route("/")
def home():
    return app.send_static_file("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    user_name = data.get("user_name", "TheMistry")
    question = data.get("question", "")
    throws = data.get("throws", [])  # 期待前端送 [6,7,8,9,7,8]

    if not user_name or not question or len(throws) != 6:
        return jsonify({"error": "Missing required fields"}), 400

    error = validate_request(data)
    if error:
        return jsonify({"error": error}), 400

    
    # ---- 卦象計算 ----
    changing_lines = []
    binary_list = []

    for i, val in enumerate(throws):
        if val == 6:  # 老陰
            binary_list.append("0")
            changing_lines.append(i+1)
        elif val == 7:  # 少陽
            binary_list.append("1")
        elif val == 8:  # 少陰
            binary_list.append("0")
        elif val == 9:  # 老陽
            binary_list.append("1")
            changing_lines.append(i+1)

    binary_code = "".join(binary_list[::-1])
    
    # ---- 查 DB ----
    conn = sqlite3.connect("iching.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, judgment FROM hexagrams WHERE binary_code=?", (binary_code,))
    hexagram = cursor.fetchone()
    if not hexagram:
        return jsonify({"error": "Invalid hexagram"}), 400

    hex_id, hex_name, judgment = hexagram
    #第幾掛(數字),卦象,掛辭
    lines_text = []
    if changing_lines: #第幾爻有變爻 [1,2,3,4,5,6]
        qmarks = ",".join("?" * len(changing_lines)) #將[1,2,3,4] 變 (?,?,?,?)
        cursor.execute(
            f"SELECT position, text FROM lines WHERE hexagram_id=? AND position_num IN ({qmarks})",  #hexagram_id一個問號, position_num接qmarks的問號
            [hex_id] + changing_lines #把數字塞進?
        )
    lines_text = cursor.fetchall() #因為qmarks可以很多, 所以用fetchall()
    
    # ---- 組 Prompt ----
    promptCore = f"""使用者：{user_name}
    問題：{question}
    本卦：{hex_name}
    卦辭：{judgment}
    變爻：{changing_lines if changing_lines else "無"}"""#最基本掛辭+變爻的號碼

    prompt_no_hint = promptCore
    prompt_w_hint = promptCore
    if lines_text: #fetch all 抓出來的 position +text
        prompt_no_hint += "\n爻辭：\n" + "\n".join([f"{pos} {txt}" for pos, txt in lines_text])
    prompt_no_hint += "請根據以上資料, 根據使用者問題類別，請使用500字說明掛辭爻辭與問題的連結後，幫使用者統整可能的預測或建議。"
    #prompt_no_hint + 爻辭 => 爻辭來自lines_text
    #sysprompt_no_hint => 給grok做分析用, 不給提示辭
    sysprompt_no_hint = """
    You are an expert I Ching interpreter. 
    First, classify the user's query:
    - If it's asking for specific predictions like 'who' (person), 'what (event or action), 'when'(time), or ' what kind of place' or'what thing' (object/outcome), label it as 'SPECIFIC_PREDICTION'.
    - If it's asking for general advice, guidance, or suggestions based on the hexagram, label it as 'ADVICE'.
    Examples:
    - Query: 'What will happen in my career next month?' → SPECIFIC_PREDICTION (what/when)
    - Query: 'Give me advice on my relationship.' → ADVICE
    - Query: 'Who is the person I'll meet soon?' → SPECIFIC_PREDICTION (who)
    - Query: 'How should I handle this situation?' → ADVICE.
    Based on classification:
    - If SPECIFIC_PREDICTION: Provide a direct, factual interpretation tied to the query's focus (who/what/when/where/thing). 參考十翼資料加強準度.
        Example response: 'The person (who) is likely a mentor figure, represented by the strong yang lines.'
    - If ADVICE: Offer general guidance, suggestions, or reflections based on the hexagram's wisdom. Encourage positive actions.
        Example response: '建議: In this situation, maintain patience like the mountain hexagram advises, and seek balance."""
    #System prompt for output hint grok4FR
    sysprompt_f_Q_define = """你是一位精準的問題分類專家，專門分析使用者詢問的內容，僅用於命理或塔羅相關的回應生成。
        請仔細閱讀使用者問題，然後根據以下規則嚴格分類，只輸出單一關鍵字作為回應，絕對不得添加任何額外解釋、文字或符號：
        如果問題詢問'什麼類型的人'、'誰會出現'、'什麼樣的人格'或類似人物特質/身份，輸出：person_hint
        如果問題詢問'可能碰到什麼狀況'、'會發生什麼事'、'什麼事件'或類似情境/發展，輸出：event_hint
        如果問題詢問'什麼時間'、'何時發生'、'最佳時機'或類似時序/日期，輸出：time_hint
        如果問題詢問'什麼地方'、'在哪裡'、'地點相關'或類似位置/環境，輸出：place_hint
        如果問題詢問'什麼東西'、'物件/物品'、'象徵物'或類似實體/道具，輸出：object_hint
        如果問題明確要求'建議'、'怎麼做'、'該如何'或類似指導/行動，輸出：ADVICE
        如果問題詢問'吉凶'、'好壞'、'運勢判斷'或類似預測結果，輸出：吉凶
        強制只輸出以上單一關鍵字：person_hint、event_hint、time_hint、place_hint、object_hint、ADVICE 或 吉凶。無匹配則默認輸出：ADVICE"""

    
    clientgrok = Client(
    api_key=os.getenv("XAI_API_KEY"),
    timeout=7200, # Override default timeout with longer timeout for reasoning models
    )

    #GROK4FRtoJudgeQuestionMeaning:
    grokChatQdefine = clientgrok.chat.create(model="grok-4-fast-reasoning")
    grokChatQdefine.append(system(sysprompt_f_Q_define))
    grokChatQdefine.append(user(question))
    responsegrokQDefine = grokChatQdefine.sample() #responsegrokQDefine應該要出 hint
    
    valid_hints = ["person_hint", "event_hint", "time_hint", "place_hint", "object_hint"]
    hint_type = responsegrokQDefine.content.strip()
    cursor2 = conn.cursor()
    if lines_text:
        if hint_type in valid_hints:   # ✅ 只在這五類時才去撈暗示
            for pos, txt in lines_text: 
                print ("pos =" + pos +", txt = " + txt)
                cursor2.execute(f"""
                    SELECT {hint_type}
                    FROM lines
                    WHERE hexagram_id=? AND position=?
                """, (hex_id, pos))
                result = cursor2.fetchone()
                print(result)
                hint_val = result[0] if result and result[0] else "（無暗示）"
                prompt_w_hint += "\n爻辭:" + txt + ",hint =" + hint_val
        else:
            # 如果 hint_type 是 ADVICE / 吉凶 → 只加爻辭，不加暗示
            prompt_w_hint += "\n爻辭：\n" + "\n".join([f"{pos} {txt}" for pos, txt in lines_text])
    conn.close()
    
    #GROK
    grokChat = clientgrok.chat.create(model="grok-4-fast-reasoning")
    grokChat.append(system(sysprompt_no_hint))
    grokChat.append(user(prompt_no_hint))
    responsegrok4FR = grokChat.sample()



    promptForSystem4o = "你是一個易經老師,請根據hint_type與用戶提供的所有資訊,彙整一合理的預測提供給使用者。 hint_type = " + hint_type
    promptUser4o = prompt_w_hint + "請根據以上情報提供1000字內建議."

    response4mini = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": promptForSystem4o},
            {"role": "user", "content": promptUser4o}
        ],
        max_tokens=1500
    )


    reply4mini = response4mini.choices[0].message.content
    usage4mini = response4mini.usage
    prompt_tokens4mini = usage4mini.prompt_tokens
    completion_tokens4mini = usage4mini.completion_tokens

    replygrok4FR = responsegrok4FR.content
    prompt_tokensgrok4FR = responsegrok4FR.usage.prompt_tokens
    completion_tokensgrok4FR = responsegrok4FR.usage.completion_tokens + responsegrok4FR.usage.reasoning_tokens

    
    
    return jsonify({
        "answer4mini": reply4mini,
        "usage4mini": 
            {
            "prompt_tokens": prompt_tokens4mini,
            "completion_tokens": completion_tokens4mini,
            "costper1K" : ((prompt_tokens4mini*0.15+completion_tokens4mini*0.06)/1000),
            "info" : "systpromt=" + promptForSystem4o + "\nUserprompt = " + prompt_w_hint
            },
        "answergrok4FR": replygrok4FR,
        "usagegrok4FR": 
            {
            "prompt_tokens" : prompt_tokensgrok4FR,
            "completion_tokens": completion_tokensgrok4FR,
            "costper1K" : ((prompt_tokensgrok4FR*0.2+completion_tokensgrok4FR*0.5)/1000),        
            "info" : hint_type
            }
        })

def validate_request(data):
    user_name = data.get("user_name")
    question = data.get("question")

    # 型別檢查
    if not isinstance(user_name, str) or not isinstance(question, str):
        return "Invalid data type"

    # 長度檢查
    if len(user_name) > 50:
        return "user_name too long"
    if len(question) > 500:
        return "question too long"

    return None  # 通過

if __name__ == "__main__":
    app.run(debug=True)
