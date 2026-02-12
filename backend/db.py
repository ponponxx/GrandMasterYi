import os
import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Date
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from dotenv import load_dotenv

# 讀取 .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# 初始化 SQLAlchemy
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# =====================
# 資料表定義
# =====================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String, unique=True, nullable=False)
    email = Column(String)
    name = Column(String)
    coins = Column(Integer, default=0)
    ad_views_today = Column(Integer, default=0)
    last_ad_reset = Column(Date, default=datetime.date.today)
    created_at = Column(DateTime, server_default=func.now())

    readings = relationship("Reading", back_populates="user", cascade="all, delete-orphan")
    tokens = relationship("JWTToken", back_populates="user", cascade="all, delete-orphan")


class JWTToken(Base):
    __tablename__ = "jwt_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    token = Column(Text, nullable=False)
    exp = Column(DateTime)
    is_valid = Column(Boolean, default=True)

    user = relationship("User", back_populates="tokens")


class Reading(Base):
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    question = Column(Text)
    hexagram = Column(String)
    result = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="readings")


# =====================
# 資料庫操作函式
# =====================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- 使用者 ----------
def create_or_get_user(db, google_id, email, name):
    user = db.query(User).filter_by(google_id=google_id).first()
    if not user:
        user = User(google_id=google_id, email=email, name=name)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # 若日期變更，自動重設廣告次數
        if user.last_ad_reset != datetime.date.today():
            user.ad_views_today = 0
            user.last_ad_reset = datetime.date.today()
            db.commit()
    return user


def get_user_by_id(db, user_id):
    return db.query(User).filter_by(id=user_id).first()


def update_user_info(db, user_id, **kwargs):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return None
    for key, value in kwargs.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


# ---------- JWT ----------
def store_jwt(db, user_id, token, exp):
    jwt = JWTToken(user_id=user_id, token=token, exp=exp, is_valid=True)
    db.add(jwt)
    db.commit()


def invalidate_jwt(db, token):
    jwt = db.query(JWTToken).filter_by(token=token).first()
    if jwt:
        jwt.is_valid = False
        db.commit()


def is_jwt_valid(db, token):
    jwt = db.query(JWTToken).filter_by(token=token, is_valid=True).first()
    if not jwt:
        return False
    if jwt.exp and jwt.exp < datetime.datetime.utcnow():
        jwt.is_valid = False
        db.commit()
        return False
    return True


# ---------- Coin / 廣告 ----------
def get_user_coins(db, user_id):
    user = get_user_by_id(db, user_id)
    return user.coins if user else 0


def add_coins(db, user_id, amount):
    user = get_user_by_id(db, user_id)
    if user:
        user.coins += amount
        db.commit()


def deduct_coins(db, user_id, amount):
    user = get_user_by_id(db, user_id)
    if user and user.coins >= amount:
        user.coins -= amount
        db.commit()
        return True
    return False


def record_ad_view(db, user_id, max_views=5, reward_per_ad=1):
    user = get_user_by_id(db, user_id)
    if not user:
        return False, "User not found"

    # 新的一天自動重置
    if user.last_ad_reset != datetime.date.today():
        user.ad_views_today = 0
        user.last_ad_reset = datetime.date.today()

    if user.ad_views_today >= max_views:
        return False, "Max ad views reached"

    user.ad_views_today += 1
    user.coins += reward_per_ad
    db.commit()
    return True, f"Ad viewed: {user.ad_views_today}/{max_views}"


# ---------- 占卜紀錄 ----------
def save_reading(db, user_id, question, hexagram, result):
    reading = Reading(user_id=user_id, question=question, hexagram=hexagram, result=result)
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


def get_user_readings(db, user_id, limit=50):
    return (
        db.query(Reading)
        .filter_by(user_id=user_id)
        .order_by(Reading.created_at.desc())
        .limit(limit)
        .all()
    )


# =====================
# 初始化資料庫（第一次執行用）
# =====================
def init_db():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    print("🔧 Initializing database...")
    init_db()
    print("✅ Done.")
