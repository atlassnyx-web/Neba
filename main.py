# -*- coding: utf-8 -*-
import os
import json
import sqlite3
import logging
import threading
import time
import telebot
from flask import Flask, request, jsonify
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, BotCommand
)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
log = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise Exception("BOT_TOKEN not set!")

WEBAPP_URL = "https://atlassnyx-web.github.io/Atlascom/"
DB_FILE = "scores.db"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)


# ================== قاعدة البيانات ==================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            user_id INTEGER, username TEXT, chat_id INTEGER,
            score INTEGER, level INTEGER DEFAULT 1,
            updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, chat_id)
        )""")
    conn.commit(); conn.close()


def save_score(uid, name, cid, sc, lv=1):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""INSERT INTO scores (user_id, username, chat_id, score, level)
        VALUES (?,?,?,?,?)
        ON CONFLICT(user_id, chat_id) DO UPDATE SET
            score=MAX(score, excluded.score),
            username=excluded.username,
            level=CASE WHEN excluded.score>score THEN excluded.level ELSE level END,
            updated=CURRENT_TIMESTAMP""", (uid, name, cid, sc, lv))
    conn.commit(); conn.close()


def get_lb(cid, limit=10):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""SELECT user_id, username, score, level FROM scores
                 WHERE chat_id=? ORDER BY score DESC LIMIT ?""", (cid, limit))
    r = c.fetchall(); conn.close(); return r


def get_rank(cid, uid):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""SELECT COUNT(*)+1 FROM scores WHERE chat_id=? AND score >
                 COALESCE((SELECT score FROM scores WHERE chat_id=? AND user_id=?), 0)""",
              (cid, cid, uid))
    r = c.fetchone()[0]
    c.execute("SELECT score, level FROM scores WHERE chat_id=? AND user_id=?", (cid, uid))
    row = c.fetchone(); conn.close()
    return r, (row[0] if row else 0), (row[1] if row else 1)


init_db()


def play_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text="🐦 العب الآن", web_app=WebAppInfo(url=WEBAPP_URL)))
    return kb


def esc(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")


# ================== معالجات ==================
@bot.message_handler(commands=['start', 'play'])
def cmd_start(message):
    log.info(f"📩 /start from user={message.from_user.id} chat={message.chat.id} type={message.chat.type}")
    try:
        bot.send_message(message.chat.id, "🐦 <b>فوج النيبة — الطائر</b>", reply_markup=play_kb())
        log.info("✅ replied")
    except Exception as e:
        log.error(f"❌ {e}")


@bot.message_handler(commands=['leaderboard'])
def cmd_lb(message):
    log.info(f"📩 /leaderboard from {message.chat.id}")
    rows = get_lb(message.chat.id, 10)
    if not rows:
        bot.send_message(message.chat.id, "📭 لا توجد نتائج بعد.", reply_markup=play_kb())
        return
    medals = ["🥇","🥈","🥉"]
    text = "🏆 <b>فوج النيبة — أفضل اللاعبين</b>\n\n"
    for i, (uid, name, sc, lvl) in enumerate(rows):
        p = medals[i] if i < 3 else f"{i+1}."
        text += f"{p} <b>{esc(name)}</b> — {sc} نقطة\n"
    bot.send_message(message.chat.id, text, reply_markup=play_kb())


@bot.message_handler(commands=['myrank'])
def cmd_myrank(message):
    rank, sc, lv = get_rank(message.chat.id, message.from_user.id)
    if sc == 0:
        bot.send_message(message.chat.id, "ما لعبت بعد! /play"); return
    bot.send_message(message.chat.id,
        f"👤 <b>{esc(message.from_user.first_name)}</b>\n🏅 {rank}\n🎯 {sc}\n⚡ {lv}")


@bot.message_handler(commands=['help'])
def cmd_help(message):
    bot.send_message(message.chat.id, "📖 /play /leaderboard /myrank")


# ================== API للعبة ==================
def _cors(r):
    r.headers['Access-Control-Allow-Origin'] = '*'
    r.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return r


@app.route('/api/score', methods=['POST', 'OPTIONS'])
def api_score():
    if request.method == 'OPTIONS':
        return _cors(jsonify({'ok': True}))
    try:
        d = request.get_json(force=True)
        cid = int(d.get('chat_id', 0)); uid = int(d.get('user_id', 0))
        sc = int(d.get('score', 0)); lv = int(d.get('level', 1))
        name = str(d.get('name', 'لاعب'))[:50]
    except:
        return _cors(jsonify({'ok': False})), 400
    if cid == 0 or uid == 0:
        return _cors(jsonify({'ok': False})), 400
    save_score(uid, name, cid, sc, lv)
    rank, best, _ = get_rank(cid, uid)
    medal = "🥇" if rank==1 else "🥈" if rank==2 else "🥉" if rank==3 else "🏅"
    try:
        bot.send_message(cid,
            f"🐦 <b>{esc(name)}</b> أنهى جولته!\n\n"
            f"🎯 النقاط: <b>{sc}</b>\n⚡ المستوى: <b>{lv}</b>\n"
            f"{medal} مركزه: <b>{rank}</b>\n💎 أفضل نتيجة: <b>{best}</b>")
    except Exception as e:
        log.error(f"score send error: {e}")
    rows = get_lb(cid, 10)
    lb = [{'user_id':r[0],'name':r[1],'score':r[2],'level':r[3]} for r in rows]
    return _cors(jsonify({'ok': True, 'rank': rank, 'best': best, 'leaderboard': lb}))


@app.route('/')
def home():
    return "🐦 Bot is running with polling"


# ================== Polling في خلفية ==================
def run_polling():
    log.info("🔁 Removing webhook...")
    try:
        bot.remove_webhook()
        time.sleep(2)
    except Exception as e:
        log.error(f"remove_webhook: {e}")
    try:
        bot.set_my_commands([
            BotCommand("play", "🐦 العب الآن"),
            BotCommand("leaderboard", "🏆 أفضل اللاعبين"),
            BotCommand("myrank", "📍 مركزك"),
            BotCommand("help", "📖 المساعدة"),
        ])
    except Exception as e:
        log.error(f"set_commands: {e}")
    log.info("🚀 Polling started...")
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=25,
                                 none_stop=True, skip_pending=True)
        except Exception as e:
            log.error(f"polling crashed: {e}")
            time.sleep(5)


# ================== تشغيل ==================
if __name__ == "__main__":
    # ابدأ Polling في خلفية
    t = threading.Thread(target=run_polling, daemon=True)
    t.start()
    # Flask للـ API فقط
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
