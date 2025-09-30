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
            changing_lines.append(i)
        elif val == 7:  # 少陽
            binary_list.append("1")
        elif val == 8:  # 少陰
            binary_list.append("0")
        elif val == 9:  # 老陽
            binary_list.append("1")
            changing_lines.append(i)

    binary_code = "".join(binary_list[::-1])
    
    # ---- 查 DB ----
    conn = sqlite3.connect("iching.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, judgment FROM hexagrams WHERE binary_code=?", (binary_code,))
    hexagram = cursor.fetchone()
    if not hexagram:
        return jsonify({"error": "Invalid hexagram"}), 400

    hex_id, hex_name, judgment = hexagram

    lines_text = []
    if changing_lines:
        qmarks = ",".join("?" * len(changing_lines))
        cursor.execute(
            f"SELECT position, text FROM lines WHERE hexagram_id=? AND position_num IN ({qmarks})",
            [hex_id] + changing_lines
        )
    lines_text = cursor.fetchall()
    conn.close()
    
    # ---- 組 Prompt ----
    promptCore = f"""使用者：{user_name}
    問題：{question}
    本卦：{hex_name}
    卦辭：{judgment}
    變爻：{changing_lines if changing_lines else "無"}"""
    if lines_text:
        promptCore += "\n爻辭：\n" + "\n".join([f"{pos} {txt}" for pos, txt in lines_text])
    prompt = promptCore+"請根據以上資訊，進行500字占卜說明。"

    promptForSystem = "You are an expert I Ching interpreter. First, classify the user's query:- If it's asking for specific predictions like 'who' (person), 'what (event or action), 'when'(time), or 'what thing' (object/outcome), label it as 'SPECIFIC_PREDICTION'.\
    - If it's asking for general advice, guidance, or suggestions based on the hexagram, label it as 'ADVICE'.\
    Examples:\
    - Query: 'What will happen in my career next month?' → SPECIFIC_PREDICTION (what/when)- Query: 'Give me advice on my relationship.' → ADVICE\
- Query: 'Who is the person I'll meet soon?' → SPECIFIC_PREDICTION (who)\
- Query: 'How should I handle this situation?' → ADVICE.\
Based on classification:\
- If SPECIFIC_PREDICTION: Provide a direct, factual interpretation tied to the query's focus (who/what/when/thing). Use traditional I Ching texts for accuracy. Be concise and avoid vagueness.\
  Example response: 'The person (who) is likely a mentor figure, represented by the strong yang lines.'\
- If ADVICE: Offer general guidance, suggestions, or reflections based on the hexagram's wisdom. Encourage positive actions.\
  Example response: '建議: In this situation, maintain patience like the mountain hexagram advises, and seek balance."

    promptForSystem5mini = "你是一個易經大師,先分析用戶問題,如果是問特定人事時地物,請以條列式精簡列出各掛辭爻辭對應該問題的隱含意義,最後以一句話總結,如果是問建議,無須條列掛辭意義.回應長度控制在100字以內,"
    


    response5mini = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": promptForSystem5mini},
            {"role": "user", "content": prompt}
        ],
        max_completion_tokens=3500
    )
    clientgrok = Client(
    api_key=os.getenv("XAI_API_KEY"),
    timeout=3600, # Override default timeout with longer timeout for reasoning models
    )

    chat = clientgrok.chat.create(model="grok-4-fast-reasoning")
    chat.append(system(promptForSystem))
    chat.append(user(prompt))
    responsegrok4FR = chat.sample()


    promptForSystem4o = "你是一個易經老師,請整合用戶提供的所有情報,彙整一合理的預測提供給使用者"
    promptUser4o = promptCore + response5mini.choices[0].message.content + "請根據以上情報提供1000字內建議."

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

    reply5mini = response5mini.choices[0].message.content
    usage5mini = response5mini.usage
    prompt_tokens5mini = usage5mini.prompt_tokens
    completion_tokens5mini = usage5mini.completion_tokens

    
    
    return jsonify({
        "answer4mini": reply4mini,
        "usage4mini": 
            {
            "prompt_tokens": prompt_tokens4mini,
            "completion_tokens": completion_tokens4mini,
            "costper1K" : ((prompt_tokens4mini*0.15+completion_tokens4mini*0.06)/1000)
            },
        "answer5mini": reply5mini,
        "usage5mini": 
            {
            "prompt_tokens": prompt_tokens5mini,
            "completion_tokens": completion_tokens5mini,
            "costper1K" : ((prompt_tokens5mini*0.25+completion_tokens5mini*2)/1000)
            },
        "answergrok4FR": responsegrok4FR,
        "usagegrok4FR": 
            {
            "prompt_tokens",
            "completion_tokens",
            "costper1K"             
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
