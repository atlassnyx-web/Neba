# -*- coding: utf-8 -*-
import os
import json
import sqlite3
import logging
import traceback
import telebot
from flask import Flask, request, jsonify
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, BotCommand, Update
)

# ================== Logging ==================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
log = logging.getLogger(__name__)

# ================== الإعدادات ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8565879739:AAG4Skcd6bfP19ZLxXqceAx7S_-JwVwIFbw")
WEBAPP_URL = "https://atlassnyx-web.github.io/Atlascom/"
DB_FILE = "scores.db"
# ================================================

log.info(f"🚀 Starting bot... token ends with: ...{BOT_TOKEN[-10:]}")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# اختبار الاتصال بتيليجرام عند البدء
try:
    me = bot.get_me()
    log.info(f"✅ Bot connected: @{me.username} (id={me.id})")
except Exception as e:
    log.error(f"❌ Bot get_me FAILED: {e}")


# ================== قاعدة البيانات ==================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            user_id   INTEGER,
            username  TEXT,
            chat_id   INTEGER,
            score     INTEGER,
            level     INTEGER DEFAULT 1,
            updated   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, chat_id)
        )
    """)
    conn.commit()
    conn.close()


def save_score(user_id, username, chat_id, score, level=1):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO scores (user_id, username, chat_id, score, level)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, chat_id) DO UPDATE SET
            score    = MAX(score, excluded.score),
            username = excluded.username,
            level    = CASE WHEN excluded.score > score THEN excluded.level ELSE level END,
            updated  = CURRENT_TIMESTAMP
    """, (user_id, username, chat_id, score, level))
    conn.commit()
    conn.close()


def get_leaderboard(chat_id, limit=10):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""SELECT user_id, username, score, level FROM scores
                 WHERE chat_id = ? ORDER BY score DESC LIMIT ?""", (chat_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows


def get_user_rank(chat_id, user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""SELECT COUNT(*) + 1 FROM scores
                 WHERE chat_id = ? AND score > COALESCE(
                    (SELECT score FROM scores WHERE chat_id = ? AND user_id = ?), 0)""",
              (chat_id, chat_id, user_id))
    rank = c.fetchone()[0]
    c.execute("SELECT score, level FROM scores WHERE chat_id = ? AND user_id = ?",
              (chat_id, user_id))
    row = c.fetchone()
    conn.close()
    return rank, (row[0] if row else 0), (row[1] if row else 1)


init_db()


# ================== أدوات ==================
def play_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text="🐦 العب الآن", web_app=WebAppInfo(url=WEBAPP_URL)))
    return kb


def escape_html(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ================== معالجات الرسائل ==================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    log.info(f"📩 /start from {message.from_user.id} in chat {message.chat.id}")
    try:
        bot.send_message(
            message.chat.id,
            "🐦 <b>فوج النيبة — الطائر</b>",
            reply_markup=play_kb()
        )
        log.info("✅ /start reply sent")
    except Exception as e:
        log.error(f"❌ send_message /start failed: {e}")


@bot.message_handler(commands=['play'])
def cmd_play(message):
    log.info(f"📩 /play from {message.from_user.id}")
    cmd_start(message)


@bot.message_handler(commands=['leaderboard'])
def cmd_leaderboard(message):
    log.info(f"📩 /leaderboard from {message.from_user.id}")
    chat_id = message.chat.id
    rows = get_leaderboard(chat_id, 10)
    if not rows:
        bot.send_message(chat_id, "📭 لا توجد نتائج بعد.", reply_markup=play_kb())
        return
    medals = ["🥇", "🥈", "🥉"]
    text = "🏆 <b>فوج النيبة — أفضل اللاعبين</b>\n\n"
    for i, (uid, name, sc, lvl) in enumerate(rows):
        prefix = medals[i] if i < 3 else f"{i+1}."
        text += f"{prefix} <b>{escape_html(name)}</b> — {sc} نقطة (مستوى {lvl})\n"
    bot.send_message(chat_id, text, reply_markup=play_kb())


@bot.message_handler(commands=['myrank'])
def cmd_myrank(message):
    log.info(f"📩 /myrank from {message.from_user.id}")
    chat_id = message.chat.id
    user_id = message.from_user.id
    rank, sc, lvl = get_user_rank(chat_id, user_id)
    if sc == 0:
        bot.send_message(chat_id, "ما لعبت بعد! اضغط /play")
        return
    name = escape_html(message.from_user.first_name or "لاعب")
    bot.send_message(chat_id,
        f"👤 <b>{name}</b>\n🏅 مركزك: <b>{rank}</b>\n"
        f"🎯 أفضل نتيجة: <b>{sc}</b>\n⚡ أعلى مستوى: <b>{lvl}</b>")


@bot.message_handler(commands=['help'])
def cmd_help(message):
    log.info(f"📩 /help from {message.from_user.id}")
    bot.send_message(message.chat.id,
        "📖 <b>الأوامر:</b>\n/play\n/leaderboard\n/myrank\n/help")


# اختبار: أي رسالة غير أمر (يسجّلها فقط)
@bot.message_handler(func=lambda m: True)
def catch_all(message):
    log.info(f"📩 MSG (not command): {message.text!r} from {message.from_user.id}")


# ================== Webhook ==================
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        raw = request.get_data(as_text=True)
        log.info(f"🔔 WEBHOOK HIT — bytes={len(raw)}")
        log.info(f"   body[:300]: {raw[:300]}")
        data = json.loads(raw)
        update = Update.de_json(data)
        if update:
            log.info(f"   update_id={update.update_id}")
            bot.process_new_updates([update])
            log.info(f"   ✅ processed")
        else:
            log.warning("   ⚠️ Update.de_json returned None")
        return 'OK', 200
    except Exception as e:
        log.error(f"❌ WEBHOOK ERROR: {e}")
        log.error(traceback.format_exc())
        return 'Error', 500


@app.route('/set_webhook')
def set_webhook():
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN") or request.host
    webhook_url = f"https://{domain}/webhook"
    try:
        bot.remove_webhook()
        import time; time.sleep(1)
        bot.set_webhook(url=webhook_url, drop_pending_updates=True)
        info = bot.get_webhook_info()
        return jsonify({
            'ok': True,
            'webhook_url': webhook_url,
            'telegram_info': {
                'url': info.url,
                'pending': info.pending_update_count,
                'last_error': info.last_error_message,
            }
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/webhook_info')
def webhook_info():
    """معلومات الويب هوك الحالية"""
    try:
        info = bot.get_webhook_info()
        me = bot.get_me()
        return jsonify({
            'ok': True,
            'bot': {'id': me.id, 'username': me.username},
            'webhook': {
                'url': info.url,
                'pending_update_count': info.pending_update_count,
                'last_error_message': info.last_error_message,
                'last_error_date': info.last_error_date,
                'max_connections': info.max_connections,
            }
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/healthz')
def healthz():
    return "OK", 200


# ================== API للعبة ==================
def _cors(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return resp


@app.route('/api/score', methods=['POST', 'OPTIONS'])
def api_score():
    if request.method == 'OPTIONS':
        return _cors(jsonify({'ok': True}))
    try:
        data = request.get_json(force=True)
    except Exception:
        return _cors(jsonify({'ok': False, 'error': 'bad json'})), 400
    try:
        chat_id = int(data.get('chat_id', 0))
        user_id = int(data.get('user_id', 0))
        score = int(data.get('score', 0))
        level = int(data.get('level', 1))
        name = str(data.get('name', 'لاعب'))[:50]
    except Exception:
        return _cors(jsonify({'ok': False, 'error': 'bad fields'})), 400
    if chat_id == 0 or user_id == 0:
        return _cors(jsonify({'ok': False, 'error': 'missing ids'})), 400

    log.info(f"📊 Score received: {name} ({user_id}) chat={chat_id} score={score} level={level}")

    save_score(user_id, name, chat_id, score, level)
    rank, best, best_lvl = get_user_rank(chat_id, user_id)
    medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "🏅"
    text = (
        f"🐦 <b>{escape_html(name)}</b> أنهى جولته!\n\n"
        f"🎯 النقاط: <b>{score}</b>\n"
        f"⚡ المستوى: <b>{level}</b>\n"
        f"{medal} مركزه: <b>{rank}</b>\n"
        f"💎 أفضل نتيجة له: <b>{best}</b>"
    )
    try:
        bot.send_message(chat_id, text)
        log.info("✅ Score message sent to group")
    except Exception as e:
        log.error(f"❌ send_message score failed: {e}")

    rows = get_leaderboard(chat_id, 10)
    lb = [{'user_id': r[0], 'name': r[1], 'score': r[2], 'level': r[3]} for r in rows]
    return _cors(jsonify({'ok': True, 'rank': rank, 'best': best, 'leaderboard': lb}))


@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


@app.route('/')
def home():
    return "🐦 فوج النيبة — الخادم يعمل"


# ================== تشغيل ==================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
