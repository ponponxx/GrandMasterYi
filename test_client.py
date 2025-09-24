import requests

data = {
    "user_name": "彭仁頡",
    "question": "用一格模型我的GrandMasterYi才會紅呢? 是4omini,5mini還是5 nano呢",
    "hexagram": "雷火豐",
    "changing_lines": [3, 6]
}

resp = requests.post("http://127.0.0.1:5000/ask", json=data)
print(resp.json())
