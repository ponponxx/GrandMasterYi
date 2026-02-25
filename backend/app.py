import os
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

from dotenv import load_dotenv
import time
import jwt
from billing_repo import init_billing_schema, grant_ad_coins, can_consume_ask
from users_repo import init_users_schema,get_user_by_id
from history_repo import (
    init_history_schema, record_reading, list_history,
    get_history_detail, set_pin
)

load_dotenv()

# 1️⃣ 先建立 Flask 主應用

app = Flask(__name__)
CORS(app)

#拉BP
from auth_route import auth_bp
from ask_route import ask_bp
from ads_route import ads_bp
from store_route import store_bp
from history_route import history_bp
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(ask_bp, url_prefix="/api/divination")
app.register_blueprint(ads_bp, url_prefix="/api/ads")
app.register_blueprint(store_bp, url_prefix="/api/store")
app.register_blueprint(history_bp, url_prefix="/api/history")




# 啟動時建表
try:
    init_history_schema()
except Exception as e:
    print("DB init skipped:", e)
try:
    init_billing_schema()
except Exception as e:
    print("DB init skipped:", e)
try:
    init_users_schema()
except Exception as e:
    print("DB init skipped:", e)



load_dotenv()  # 自動讀取 .env

'''
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
#APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID")
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "dev-secret")  # 自己加
'''
user_sessions = {}

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)


