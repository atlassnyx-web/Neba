#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت Bland Pls 💈 - v22.1
+ شجرة القوائم
+ شحن آسيا سيل تلقائي (خصم من الرصيد)
+ نظام إيموجي مميز (Premium Emoji) لكل الأزرار
+ لوحة تحرير الأزرار (نص + لون + إيموجي)
"""

import os, re, asyncio, logging, html, sqlite3, time, random, traceback, json
import zipfile, tempfile, shutil
from datetime import datetime, timedelta
from collections import defaultdict
import aiohttp
from aiohttp import web

from telegram import (Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand, BotCommandScopeDefault)
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler)

import builtins
import threading
import queue as _queue

try:
    from medocell import Client as MedoClient
    MEDOCELL_OK = True
except ImportError:
    MedoClient = None
    MEDOCELL_OK = False

_orig_input = builtins.input
_capture_by_thread = {}

class InputCapture:
    def __init__(self):
        self.q = _queue.Queue()
    def wait(self, timeout=600):
        try:
            val = self.q.get(timeout=timeout)
            return "" if val is None else val
        except _queue.Empty:
            return ""
    def provide(self, value):
        self.q.put(value)

def _patched_input(prompt=""):
    tid = threading.get_ident()
    cap = _capture_by_thread.get(tid)
    if cap is not None:
        log.info(f"[asia-input intercepted] prompt={prompt!r}")
        return cap.wait()
    return _orig_input(prompt)

def _run_with_capture(fn, capture):
    tid = threading.get_ident()
    _capture_by_thread[tid] = capture
    try:
        return fn()
    finally:
        _capture_by_thread.pop(tid, None)

builtins.input = _patched_input

# ================== الإعدادات ==================
BOT_TOKEN = "8982437459:AAFy2_j09Nl-J0Wwr6oxV1voxDOh3BDjJpQ"
ADMIN_IDS = [7303935047, 8866376314, 7879875504, 7346087340]
ADMIN_ID  = ADMIN_IDS[0]
DB_PATH   = "shop.db"
LOGS_DIR  = "logs"
BOT_NAME  = "Bland Pls"

RECEIVER_PHONE      = "07782591120"
ASIA_PRICE_PER_1000 = 0.60

CHANNEL_URL  = "https://t.me/sdsdew_4"
CHANNEL_ID   = "@sdsdew_4"
SUPPORT_URL  = "https://t.me/Dfsv5"
SUPPORT_USER = "@Dfsv5"

DAILY_GIFT      = 0.01
REFERRAL_REWARD = 0.02
TG_API_ID       = 32127949
TG_API_HASH     = "1e05eca358b673b1dacfe2245cd7ca89"
MAX_SESSIONS_ADDED_PER_DAY = 500
SESSION_CREATION_COOLDOWN  = 5
MAX_CODE_ATTEMPTS          = 8
MAX_OTP_FETCH_RETRIES      = 6

os.makedirs(LOGS_DIR, exist_ok=True)
bot_info = {"username": ""}

try:
    from telethon import TelegramClient, functions, types
    from telethon.sessions import StringSession
    from telethon.errors import (SessionPasswordNeededError, PhoneCodeInvalidError,
        PhoneCodeExpiredError, FloodWaitError, PhoneNumberBannedError,
        PhoneNumberInvalidError, PhoneNumberUnoccupiedError, ApiIdInvalidError,
        PhoneMigrateError, NetworkMigrateError, UserMigrateError, SendCodeUnavailableError)
    TELETHON_OK = True
except ImportError:
    TELETHON_OK = False

logging.basicConfig(format="%(asctime)s | %(levelname)-8s | %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler(os.path.join(LOGS_DIR, "bot.log"), encoding="utf-8"),
              logging.StreamHandler()])
log = logging.getLogger(__name__)

# ================== الدول ==================
def iso_to_flag(iso):
    if not iso or len(iso) != 2: return "🏳"
    try:
        return (chr(0x1F1E6 + ord(iso[0].upper()) - ord('A')) +
                chr(0x1F1E6 + ord(iso[1].upper()) - ord('A')))
    except Exception: return "🏳"

COUNTRY_MAP = {
    "964": ("IQ", "العراق", iso_to_flag("IQ")), "91": ("IN", "الهند", iso_to_flag("IN")),
    "92": ("PK", "باكستان", iso_to_flag("PK")), "20": ("EG", "مصر", iso_to_flag("EG")),
    "966": ("SA", "السعودية", iso_to_flag("SA")), "971": ("AE", "الإمارات", iso_to_flag("AE")),
    "962": ("JO", "الأردن", iso_to_flag("JO")), "963": ("SY", "سوريا", iso_to_flag("SY")),
    "961": ("LB", "لبنان", iso_to_flag("LB")), "965": ("KW", "الكويت", iso_to_flag("KW")),
    "968": ("OM", "عمان", iso_to_flag("OM")), "974": ("QA", "قطر", iso_to_flag("QA")),
    "973": ("BH", "البحرين", iso_to_flag("BH")), "967": ("YE", "اليمن", iso_to_flag("YE")),
    "218": ("LY", "ليبيا", iso_to_flag("LY")), "216": ("TN", "تونس", iso_to_flag("TN")),
    "213": ("DZ", "الجزائر", iso_to_flag("DZ")), "212": ("MA", "المغرب", iso_to_flag("MA")),
    "249": ("SD", "السودان", iso_to_flag("SD")), "90": ("TR", "تركيا", iso_to_flag("TR")),
    "98": ("IR", "إيران", iso_to_flag("IR")), "1": ("US", "أمريكا/كندا", iso_to_flag("US")),
    "44": ("GB", "بريطانيا", iso_to_flag("GB")), "49": ("DE", "ألمانيا", iso_to_flag("DE")),
    "33": ("FR", "فرنسا", iso_to_flag("FR")), "7": ("RU", "روسيا", iso_to_flag("RU")),
    "62": ("ID", "إندونيسيا", iso_to_flag("ID")), "60": ("MY", "ماليزيا", iso_to_flag("MY")),
    "66": ("TH", "تايلاند", iso_to_flag("TH")), "84": ("VN", "فيتنام", iso_to_flag("VN")),
    "63": ("PH", "الفلبين", iso_to_flag("PH")), "880": ("BD", "بنغلاديش", iso_to_flag("BD")),
}

DEVICE_MODELS = ["Samsung Galaxy S24 Ultra", "Samsung Galaxy S24", "Samsung Galaxy S23",
    "Samsung Galaxy S23 Ultra", "Samsung Galaxy S22", "Samsung Galaxy A54",
    "Google Pixel 8 Pro", "Google Pixel 8", "Google Pixel 7a",
    "OnePlus 12", "OnePlus 11", "Xiaomi 14 Pro", "Xiaomi 14",
    "Redmi Note 13 Pro", "Poco F5", "iPhone 15 Pro Max", "iPhone 15 Pro",
    "iPhone 15", "iPhone 14 Pro", "iPhone 14", "iPhone 13",
    "Huawei P60 Pro", "Oppo Find X7", "Vivo X100 Pro", "Realme GT5"]
SYSTEM_VERSIONS = ["Android 14", "Android 13", "Android 12", "iOS 17.2", "iOS 17.1", "iOS 16.6"]
APP_VERSIONS = ["10.15.0", "10.14.0", "10.13.1", "10.12.0", "10.11.1"]

def detect_country(phone):
    p = re.sub(r"\D", "", phone or "")
    if p.startswith("00"): p = p[2:]
    for length in (3, 2, 1):
        if len(p) >= length and p[:length] in COUNTRY_MAP:
            return COUNTRY_MAP[p[:length]]
    return ("XX", "غير معروفة", "🏳")

def flag_for(phone): return detect_country(phone)[2]
def random_device(): return random.choice(DEVICE_MODELS)
def random_system(): return random.choice(SYSTEM_VERSIONS)
def random_app():    return random.choice(APP_VERSIONS)
# ================== الحالات ==================
(
    A_MENU, A_CAT_NAME, A_CAT_PRICE, A_NUMS_PICK, A_NUMS_TEXT,
    A_EDITPICK, A_EDITPRICE, A_DELPICK, A_BAL_ID, A_BAL_AMT,
    A_USERS_VIEW, S_PHONE, S_CODE, S_PASSWORD, S_RESEND_CHOICE,
    A_VIEW_NUMS_PICK,
    A_RC_CODE, A_RC_VALUE, A_RC_MAX,
    U_REDEEM_CODE,
    U_COMPLAINT_TEXT, A_COMPLAINT_REPLY,
    A_EDITCAT_PICK, A_EDITCAT_NAME, A_DELNUM_PICK, A_DELNUM_SELECT,
    A_BULK_ZIP, A_BULK_PHONE, A_BULK_OTP, A_BULK_2FA,
    A_BN_CAT_PICK, A_BN_LIST, A_BN_OTP, A_BN_2FA,
    MT_VIEW, MT_ACTION, MT_IN_TITLE, MT_IN_EMOJI, MT_IN_PRICE,
    MT_IN_COLOR, MT_IN_TYPE,
    ASIA_PHONE, ASIA_OTP, ASIA_AMOUNT, ASIA_CONFIRM,
    BTN_EDIT_TEXT, BTN_EDIT_EMOJI
) = range(47)

# ================== قاعدة البيانات ==================
def db():
    c = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    c.execute("PRAGMA cache_size=-64000")
    return c

def row_get(row, key, default=None):
    if row is None: return default
    try:
        if isinstance(row, dict): return row.get(key, default)
        return row[key] if key in row.keys() else default
    except Exception: return default

def init_db():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
        balance REAL DEFAULT 0, points INTEGER DEFAULT 0, last_gift TEXT,
        total_spent REAL DEFAULT 0, is_banned INTEGER DEFAULT 0, created_at TEXT);
    CREATE TABLE IF NOT EXISTS categories(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE,
        emoji TEXT DEFAULT 'X', price REAL DEFAULT 0, description TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS numbers(
        id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER,
        phone TEXT, code TEXT, password TEXT DEFAULT '',
        status TEXT DEFAULT 'available', sold_to INTEGER, sold_at TEXT, added_at TEXT);
    CREATE TABLE IF NOT EXISTS purchases(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, number_id INTEGER,
        category_id INTEGER, price REAL, purchased_at TEXT);
    CREATE TABLE IF NOT EXISTS sessions(
        phone TEXT PRIMARY KEY, session_string TEXT, country_code TEXT,
        country_name TEXT, flag TEXT, status TEXT DEFAULT 'active',
        added_at TEXT, last_used TEXT, use_count INTEGER DEFAULT 0,
        fail_count INTEGER DEFAULT 0, device_model TEXT, system_version TEXT,
        app_version TEXT, backend TEXT DEFAULT 'telethon');
    CREATE TABLE IF NOT EXISTS otp_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT, user_id INTEGER,
        otp_code TEXT, fetched_at TEXT);
    CREATE TABLE IF NOT EXISTS gift_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, given_at TEXT);
    CREATE TABLE IF NOT EXISTS session_attempts(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, phone TEXT,
        method TEXT, result TEXT, error TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS settings(
        key TEXT PRIMARY KEY, value TEXT, updated_at TEXT);
    CREATE TABLE IF NOT EXISTS referrals(
        id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_id INTEGER,
        referred_id INTEGER UNIQUE, reward REAL DEFAULT 0, created_at TEXT);
    CREATE TABLE IF NOT EXISTS redeem_codes(
        code TEXT PRIMARY KEY, value REAL DEFAULT 0, max_uses INTEGER DEFAULT 1,
        uses INTEGER DEFAULT 0, created_by INTEGER, created_at TEXT,
        is_active INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS redeem_uses(
        id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, user_id INTEGER,
        used_at TEXT, UNIQUE(code, user_id));
    CREATE TABLE IF NOT EXISTS complaints(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, username TEXT, first_name TEXT,
        message TEXT, status TEXT DEFAULT 'pending',
        admin_reply TEXT, replied_by INTEGER,
        created_at TEXT, replied_at TEXT);
    CREATE TABLE IF NOT EXISTS asia_topups(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount_iqd INTEGER,
        amount_usd REAL,
        receiver_phone TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT,
        completed_at TEXT);
    CREATE TABLE IF NOT EXISTS menu_nodes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parent_id INTEGER DEFAULT NULL,
        title TEXT NOT NULL,
        emoji TEXT DEFAULT '',
        color_style TEXT DEFAULT 'primary',
        node_type TEXT DEFAULT 'folder',
        price REAL DEFAULT 0,
        position INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TEXT);
    CREATE INDEX IF NOT EXISTS idx_menu_parent ON menu_nodes(parent_id);
    CREATE INDEX IF NOT EXISTS idx_numbers_cat ON numbers(category_id);
    CREATE TABLE IF NOT EXISTS button_customs(
        btn_key TEXT PRIMARY KEY,
        custom_text TEXT,
        custom_style TEXT,
        updated_at TEXT);
    CREATE TABLE IF NOT EXISTS button_emoji(
        btn_key TEXT PRIMARY KEY,
        emoji_id TEXT,
        updated_at TEXT);
    """)
    c.commit()
    try:
        cnt = c.execute("SELECT COUNT(*) n FROM menu_nodes").fetchone()["n"]
        if cnt == 0:
            cats = c.execute("SELECT * FROM categories ORDER BY id").fetchall()
            for cat in cats:
                try:
                    c.execute("INSERT INTO menu_nodes(id, parent_id, title, emoji, color_style, node_type, price, position, is_active, created_at) "
                              "VALUES(?,?,?,?,?,?,?,?,?,?)",
                              (cat["id"], None, cat["name"], "", "primary", "category",
                               cat["price"] or 0, cat["id"] or 0, 1, datetime.now().isoformat()))
                except Exception as _e:
                    log.warning(f"migrate cat {cat['id']}: {_e}")
            c.commit()
    except Exception as e:
        log.error(f"migrate categories: {e}")
    c.close()

# ================== دوال مساعدة ==================
def is_admin(uid): return uid in ADMIN_IDS
def normalize_phone(p): return re.sub(r"\D", "", p or "")

def register_user(u):
    try:
        c = db()
        r = c.execute("SELECT user_id FROM users WHERE user_id=?", (u.id,)).fetchone()
        is_new = r is None
        if is_new:
            c.execute("INSERT INTO users(user_id, username, first_name, points, created_at) VALUES(?,?,?,?,?)",
                      (u.id, u.username or "", u.first_name or "", 0, datetime.now().isoformat()))
        else:
            c.execute("UPDATE users SET username=?, first_name=? WHERE user_id=?",
                      (u.username or "", u.first_name or "", u.id))
        c.commit(); c.close()
        return is_new
    except Exception as e:
        log.error(f"register_user: {e}")
        return False

def get_user(uid):
    try:
        c = db()
        r = c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
        c.close(); return r
    except Exception: return None

def get_balance(uid):
    r = get_user(uid)
    return r["balance"] if r else 0.0

def is_banned(uid):
    r = get_user(uid)
    if not r: return False
    try: return bool(r["is_banned"])
    except Exception: return False

def get_setting(key, default=None):
    try:
        c = db()
        r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        c.close()
        return r["value"] if r else default
    except Exception: return default

def set_setting(key, value):
    try:
        c = db()
        c.execute("INSERT OR REPLACE INTO settings(key, value, updated_at) VALUES(?,?,?)",
                  (key, str(value), datetime.now().isoformat()))
        c.commit(); c.close()
    except Exception as e: log.error(f"set_setting: {e}")

def is_maintenance():
    return get_setting("maintenance", "0") == "1"

# ================== نظام تحرير الأزرار ==================
COLOR_STYLES = ["primary", "success", "danger"]

BUTTON_DEFAULTS = {
    # ===== أزرار المستخدم =====
    "shop":             ("المتجر",                        "success"),
    "my_purchases":     ("مشترياتي",                      "primary"),
    "balance":          ("رصيدي",                         "primary"),
    "daily_gift":       ("هدية يومية",                    "success"),
    "recharge":         ("شحن الرصيد",                    "success"),
    "redeem":           ("تعبئة كود",                     "primary"),
    "channel":          ("قناة البوت",                    "primary"),
    "complaint":        ("رفع شكوى",                      "danger"),
    "admin_open":       ("لوحة الأدمن",                   "danger"),
    "home":             ("الرئيسية",                      "primary"),
    "join_channel":     ("اشترك في القناة",               "primary"),
    "check_sub":        ("تحقق من الاشتراك",              "success"),
    "asia_auto":        ("شحن آسيا تلقائي",               "success"),
    "shop_now":         ("المتجر",                        "success"),

    # ===== أزرار الرجوع =====
    "admin_back":       ("لوحة الأدمن",                   "primary"),
    "sessions_back":    ("جلسات OTP",                     "primary"),

    # ===== أزرار لوحة الأدمن =====
    "A_stats":          ("📊 الإحصائيات",                  "primary"),
    "A_tree":           ("🛒 إدارة قوائم المتجر (شجرة)",   "success"),
    "A_addcat":         ("➕️ إضافة قسم",                   "success"),
    "A_addnums":        ("📥 إضافة أرقام",                 "success"),
    "A_bulknums":       ("🔢 إضافة مجموعة أرقام",          "success"),
    "A_editprice":      ("💰 تعديل سعر",                   "primary"),
    "A_editcatname":    ("✏️ تعديل اسم قسم",              "primary"),
    "A_delcat":         ("🗑 حذف قسم",                     "danger"),
    "A_delnum":         ("🗑 حذف رقم",                     "danger"),
    "A_viewnums":       ("📝 عرض أرقام قسم",              "primary"),
    "A_addbal":         ("💴 إضافة رصيد",                  "success"),
    "A_addpoints":      ("🎁 إضافة نقاط",                  "success"),
    "A_createcode":     ("🎟 إنشاء كود تعبئة",             "success"),
    "A_listcodes":      ("📍 الأكواد الحاليه",             "primary"),
    "A_users":          ("🔍 المستخدمين",                  "primary"),
    "A_sessions":       ("🔑 جلسات OTP",                   "primary"),
    "A_broadcast":      ("🔔 بث رسالة",                    "primary"),
    "A_maint_on":       ("🟢 تشغيل البوت",                  "success"),
    "A_maint_off":      ("🔴 إطفاء البوت",                 "danger"),
    "A_btn_customs":    ("🎨 تحرير أزرار البوت",           "success"),
}

_btn_cache = {}

def btn_get(key):
    if key in _btn_cache:
        return _btn_cache[key]
    try:
        c = db()
        r = c.execute("SELECT custom_text, custom_style FROM button_customs WHERE btn_key=?",
                      (key,)).fetchone()
        c.close()
        if r:
            val = (r["custom_text"], r["custom_style"])
        else:
            val = (None, None)
        _btn_cache[key] = val
        return val
    except Exception:
        return (None, None)

def btn_invalidate():
    _btn_cache.clear()

def btn_text(key):
    default_text, _ = BUTTON_DEFAULTS.get(key, ("?", "primary"))
    ct, _ = btn_get(key)
    return ct if ct else default_text

def btn_style(key):
    _, default_style = BUTTON_DEFAULTS.get(key, ("?", "primary"))
    _, cs = btn_get(key)
    return cs if cs else default_style

def mk_btn(key, callback_data=None, url=None):
    text = btn_text(key)
    style = btn_style(key)
    emoji_id = btn_emoji_get(key)
    kwargs = {"style": style}
    if emoji_id:
        kwargs["icon_custom_emoji_id"] = emoji_id
    if url:
        return InlineKeyboardButton(text, url=url, **kwargs)
    cb = callback_data if callback_data is not None else key
    return InlineKeyboardButton(text, callback_data=cb, **kwargs)

def btn_set(key, custom_text=None, custom_style=None):
    try:
        c = db()
        c.execute("INSERT OR REPLACE INTO button_customs(btn_key, custom_text, custom_style, updated_at) "
                  "VALUES(?,?,?,?)",
                  (key, custom_text, custom_style, datetime.now().isoformat()))
        c.commit(); c.close()
        btn_invalidate()
    except Exception as e:
        log.error(f"btn_set: {e}")

def btn_reset(key):
    try:
        c = db()
        c.execute("DELETE FROM button_customs WHERE btn_key=?", (key,))
        c.commit(); c.close()
        btn_invalidate()
    except Exception as e:
        log.error(f"btn_reset: {e}")

# ===== دوال الإيموجي المميز =====
_btn_emoji_cache = {}

def btn_emoji_get(key):
    if key in _btn_emoji_cache:
        return _btn_emoji_cache[key]
    try:
        c = db()
        r = c.execute("SELECT emoji_id FROM button_emoji WHERE btn_key=?", (key,)).fetchone()
        c.close()
        val = r["emoji_id"] if r else None
        _btn_emoji_cache[key] = val
        return val
    except Exception:
        return None

def btn_emoji_set(key, emoji_id):
    try:
        c = db()
        c.execute("INSERT OR REPLACE INTO button_emoji(btn_key, emoji_id, updated_at) VALUES(?,?,?)",
                  (key, emoji_id, datetime.now().isoformat()))
        c.commit(); c.close()
        _btn_emoji_cache[key] = emoji_id
    except Exception as e:
        log.error(f"btn_emoji_set: {e}")

def btn_emoji_reset(key):
    try:
        c = db()
        c.execute("DELETE FROM button_emoji WHERE btn_key=?", (key,))
        c.commit(); c.close()
        _btn_emoji_cache.pop(key, None)
    except Exception as e:
        log.error(f"btn_emoji_reset: {e}")
# ================== نهاية النظام ==================

async def send(update, text, kb=None, parse_mode="HTML"):
    markup = InlineKeyboardMarkup(kb) if kb else None
    try:
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(text, reply_markup=markup,
                    parse_mode=parse_mode, disable_web_page_preview=True)
                return
            except Exception:
                try:
                    await update.callback_query.message.reply_text(text, reply_markup=markup,
                        parse_mode=parse_mode, disable_web_page_preview=True)
                    return
                except Exception: pass
        else:
            await update.message.reply_text(text, reply_markup=markup,
                parse_mode=parse_mode, disable_web_page_preview=True)
    except Exception as e: log.error(f"send error: {e}")

async def notify_admins(ctx, text, **kwargs):
    for _aid in ADMIN_IDS:
        try: await ctx.bot.send_message(_aid, text, **kwargs)
        except Exception as e: log.warning(f"notify admin {_aid}: {e}")
# ================== الاشتراك ==================
async def check_subscription(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        status = getattr(member, "status", "")
        status_name = getattr(status, "name", str(status)).upper()
        if "LEFT" in status_name or "KICKED" in status_name: return False
        return True
    except Exception as e:
        log.warning(f"sub check fail uid={user_id}: {e}")
        return False

def sub_required_kb():
    return [
        [mk_btn("join_channel", url=CHANNEL_URL)],
        [mk_btn("check_sub")],
    ]

async def require_subscription(update, ctx, uid):
    if is_admin(uid): return True
    if await check_subscription(ctx.bot, uid): return True
    await send(update,
        "عذراً عزيزي\n\nلازم تكون مشترك بقناة البوت 📢 الرسمية حتى تستخدم البوت.\n\n"
        "اشترك ثم اضغط تحقق.\n\n"
        f"القناة: {CHANNEL_URL}",
        sub_required_kb())
    return False

async def cb_check_sub(update, ctx):
    q = update.callback_query
    uid = q.from_user.id
    if await check_subscription(ctx.bot, uid):
        await q.answer("تم التحقق، أهلاً بك!")
        register_user(q.from_user)
        bal = get_balance(uid)
        text = (f"{iso_to_flag('IQ')} بوت {BOT_NAME}\n\nرصيدك: {bal:.2f}$\n\nمعرفك: {uid}\n\nاختر من القائمة")
        await send(update, text, home_kb(uid))
    else:
        await q.answer("ما زلت غير مشترك بالقناة!", show_alert=True)

# ================== لوحات الأزرار ==================
def back_home():    return [[mk_btn("home")]]
def back_admin():   return [[mk_btn("admin_back")]]
def back_sessions():return [[mk_btn("sessions_back")]]

def home_kb(uid):
    kb = [
        [mk_btn("shop"),           mk_btn("my_purchases")],
        [mk_btn("balance"),        mk_btn("daily_gift")],
        [mk_btn("recharge")],
        [mk_btn("redeem")],
        [mk_btn("channel", url=CHANNEL_URL), mk_btn("complaint")],
    ]
    if is_admin(uid):
        kb.append([mk_btn("admin_open")])
    return kb

def admin_kb():
    maint = is_maintenance()
    toggle_key = "A_maint_on" if maint else "A_maint_off"
    return [
        [mk_btn("A_stats")],
        [mk_btn("A_tree", callback_data="MT_root")],
        [mk_btn("A_addcat"),       mk_btn("A_addnums")],
        [mk_btn("A_bulknums")],
        [mk_btn("A_editprice"),    mk_btn("A_editcatname")],
        [mk_btn("A_delcat"),       mk_btn("A_delnum")],
        [mk_btn("A_viewnums")],
        [mk_btn("A_addbal"),       mk_btn("A_addpoints")],
        [mk_btn("A_createcode"),   mk_btn("A_listcodes")],
        [mk_btn("A_users")],
        [mk_btn("A_sessions")],
        [mk_btn("A_broadcast")],
        [mk_btn("A_btn_customs")],
        [mk_btn(toggle_key, callback_data="A_toggle_maint")],
        [mk_btn("home")],
    ]

# ================== إدارة الجلسات ==================
class SessionManager:
    def __init__(self):
        self._pending = {}
        self._lock = asyncio.Lock()
    async def set(self, uid, data):
        async with self._lock: self._pending[uid] = data
    def get(self, uid): return self._pending.get(uid)
    def pop(self, uid): return self._pending.pop(uid, None)
    async def cleanup(self, uid):
        d = self.pop(uid)
        if d and d.get("client"):
            try: await d["client"].disconnect()
            except Exception: pass

SESSION_MGR = SessionManager()
_last_session_time = defaultdict(float)
_daily_session_count = defaultdict(int)
_daily_session_date = {}

def check_daily_limit(uid):
    today = datetime.now().date().isoformat()
    if _daily_session_date.get(uid) != today:
        _daily_session_date[uid] = today
        _daily_session_count[uid] = 0
    return _daily_session_count[uid] < MAX_SESSIONS_ADDED_PER_DAY

def inc_daily_limit(uid):
    _daily_session_count[uid] += 1

def format_code_method(sent):
    if not hasattr(sent, "type") or sent.type is None: return ""
    tn = type(sent.type).__name__
    type_map = {'SentCodeTypeApp': 'تطبيق', 'SentCodeTypeSms': 'SMS',
        'SentCodeTypeCall': 'مكالمة', 'SentCodeTypeFlashCall': 'Flash',
        'SentCodeTypeMissedCall': 'Missed'}
    return " -> " + type_map.get(tn, tn)

async def try_telethon_default(phone, device_info):
    client = None
    try:
        client = TelegramClient(StringSession(), TG_API_ID, TG_API_HASH,
            connection_retries=3, retry_delay=2, timeout=20,
            device_model=device_info["device_model"],
            system_version=device_info["system_version"],
            app_version=device_info["app_version"],
            lang_code="ar", system_lang_code="ar")
        await client.connect()
        sent = await client.send_code_request(phone)
        if sent: return client, sent, None
        try: await client.disconnect()
        except Exception: pass
        return None, None, "no response"
    except Exception as e:
        if client:
            try: await client.disconnect()
            except Exception: pass
        return None, None, str(e)

async def send_code_telethon(phone_raw):
    device_info = {"device_model": random_device(),
                   "system_version": random_system(),
                   "app_version": random_app()}
    client, sent, err = await try_telethon_default(phone_raw, device_info)
    if client and sent:
        return client, sent, "Telethon", "telethon", None, device_info
    return None, None, None, None, err, device_info

# ================== أوامر المستخدم ==================
async def cmd_start(update, ctx):
    u = update.effective_user
    if is_maintenance() and not is_admin(u.id):
        await update.message.reply_text("⚠️ البوت تحت الصيانه الآن\n\nنعتذر عن الإزعاج، حاول لاحقاً.",
            parse_mode="HTML")
        return
    is_new = register_user(u)
    if is_new:
        try:
            uname = f"@{u.username}" if u.username else "—"
            adm_text = (f"🆕 <b>مستخدم جديد دخل البوت</b>\n\n"
                        f"👤 الاسم: {html.escape(u.first_name or '—')}\n"
                        f"🔗 اليوزر: {uname}\n"
                        f"💳 الآيدي: <code>{u.id}</code>")
            for _aid in ADMIN_IDS:
                try: await ctx.bot.send_message(_aid, adm_text, parse_mode="HTML")
                except Exception: pass
        except Exception as e:
            log.warning(f"notify new user: {e}")
    if is_banned(u.id):
        await update.message.reply_text("أنت محظور."); return
    if not await require_subscription(update, ctx, u.id): return
    bal = get_balance(u.id)
    text = (f"{iso_to_flag('IQ')} بوت {BOT_NAME}\n\nرصيدك: {bal:.2f}$\n\nمعرفك: {u.id}\n\nاختر من القائمة")
    await update.message.reply_text(text,
        reply_markup=InlineKeyboardMarkup(home_kb(u.id)),
        parse_mode="HTML", disable_web_page_preview=True)

async def cmd_cancel(update, ctx):
    uid = update.effective_user.id
    await SESSION_MGR.cleanup(uid)
    _as = asia_sessions.pop(uid, None)
    if _as:
        try:
            if _as.get("client"):
                await _as["client"].disconnect()
        except Exception:
            pass
        if _as.get("capture"):
            _as["capture"].provide("")
    ctx.user_data.clear()
    await update.message.reply_text("تم الإلغاء ❌️.",
        reply_markup=InlineKeyboardMarkup(back_home()))
    return ConversationHandler.END

async def cmd_help(update, ctx):
    await update.message.reply_text(
        f"مساعدة\n\n/start - الرئيسية 🏠\n/cancel - إلغاء ❌️\n/myid - معرفك\n\nالدعم: {SUPPORT_USER}",
        parse_mode="HTML")

async def cmd_myid(update, ctx):
    await update.message.reply_text(f"معرفك: {update.effective_user.id}", parse_mode="HTML")

async def cb_home(update, ctx):
    q = update.callback_query
    await q.answer()
    if is_maintenance() and not is_admin(q.from_user.id):
        await send(update, "⚠️ البوت تحت الصيانه الآن\n\nنعتذر عن الإزعاج، حاول لاحقاً.")
        return
    register_user(q.from_user)
    if not await require_subscription(update, ctx, q.from_user.id): return
    bal = get_balance(q.from_user.id)
    text = (f"{iso_to_flag('IQ')} بوت {BOT_NAME}\n\nرصيدك: {bal:.2f}$\n\nمعرفك: {q.from_user.id}\n\nاختر من القائمة")
    await send(update, text, home_kb(q.from_user.id))

# ================== الهدية اليومية ==================
async def cb_daily_gift(update, ctx):
    q = update.callback_query
    uid = q.from_user.id
    register_user(q.from_user)
    if not await require_subscription(update, ctx, uid): return
    if is_banned(uid):
        await q.answer("محظور", show_alert=True); return
    u = get_user(uid)
    now = datetime.now()
    last = row_get(u, "last_gift")
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
            elapsed = now - last_dt
            if elapsed < timedelta(hours=24):
                remaining = timedelta(hours=24) - elapsed
                hrs = remaining.seconds // 3600
                mins = (remaining.seconds % 3600) // 60
                await q.answer(f"عد بعد {hrs}س {mins}د", show_alert=True)
                return
        except Exception: pass
    c = db()
    c.execute("UPDATE users SET balance = balance + ?, last_gift = ? WHERE user_id=?",
              (DAILY_GIFT, now.isoformat(), uid))
    c.execute("INSERT INTO gift_logs(user_id, amount, given_at) VALUES(?,?,?)",
              (uid, DAILY_GIFT, now.isoformat()))
    c.commit()
    nb = c.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
    c.close()
    await q.answer("تم استلام هديتك!")
    await send(update,
        f"هدية يومية 🎁!\n\nتم إضافة: {DAILY_GIFT}$\n\nرصيدك الجديد: {nb['balance']:.2f}$",
        [[mk_btn("shop_now")], [mk_btn("home")]])

# ================== أكواد التعبئة ==================
async def redeem_start(update, ctx):
    q = update.callback_query
    await q.answer()
    if not await require_subscription(update, ctx, q.from_user.id):
        return ConversationHandler.END
    await send(update,
        "تعبئة كود 🎟\n\nأرسل الكود الآن لتحصل على رصيد:\n\nمثال: WELCOME10\n\nأو /cancel للإلغاء ❌️.",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="redeem_cancel", style="danger")]])
    return U_REDEEM_CODE

async def redeem_receive(update, ctx):
    code = update.message.text.strip().upper()
    uid = update.effective_user.id
    c = db()
    row = c.execute("SELECT * FROM redeem_codes WHERE UPPER(code)=? AND is_active=1", (code,)).fetchone()
    if not row:
        c.close()
        await update.message.reply_text("الكود غير صحيح\n\nتأكد من الكود وحاول مرة ثانية.",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(back_home()))
        return ConversationHandler.END
    if row["uses"] >= row["max_uses"]:
        c.close()
        await update.message.reply_text("انتهى استخدام هذا الكود",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(back_home()))
        return ConversationHandler.END
    used = c.execute("SELECT id FROM redeem_uses WHERE code=? AND user_id=?", (row["code"], uid)).fetchone()
    if used:
        c.close()
        await update.message.reply_text("استخدمت هذا الكود مسبقاً",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(back_home()))
        return ConversationHandler.END
    value = row["value"]
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (value, uid))
    c.execute("UPDATE redeem_codes SET uses = uses + 1 WHERE code=?", (row["code"],))
    c.execute("INSERT INTO redeem_uses(code, user_id, used_at) VALUES(?,?,?)",
              (row["code"], uid, datetime.now().isoformat()))
    c.commit()
    nb = c.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()["balance"]
    c.close()
    await update.message.reply_text(
        f"تم تعبئة الكود بنجاح!\n\nالكود: {row['code']}\n"
        f"القيمة: {value:.2f}$\nرصيدك الجديد: {nb:.2f}$\n\nاستمتع!",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(back_home()))
    for _aid in ADMIN_IDS:
        try: await ctx.bot.send_message(_aid, f"كود مُستخدم\n\n{uid}\n{row['code']}\n{value:.2f}$", parse_mode="HTML")
        except Exception: pass
    return ConversationHandler.END

async def redeem_cancel(update, ctx):
    q = update.callback_query
    await q.answer()
    ctx.user_data.clear()
    await send(update, "تم إلغاء ❌️ تعبئة الكود.", back_home())
    return ConversationHandler.END

# ================== الشكاوى ==================
async def cb_complaint_start(update, ctx):
    q = update.callback_query
    await q.answer()
    if not await require_subscription(update, ctx, q.from_user.id):
        return ConversationHandler.END
    await send(update,
        "رفع شكوى 📩\n\nاكتب شكواك أو استفسارك بالتفصيل وأرسلها الآن.\n\n"
        "سيتم إرسالها إلى الإدارة، وسيتم الرد ✅️ عليك بأقرب وقت.\n\nاكتب كلام محترم فقط.",
        [[InlineKeyboardButton("رجوع 🔙", callback_data="complaint_cancel", style="danger")]])
    return U_COMPLAINT_TEXT

async def complaint_receive(update, ctx):
    user = update.effective_user
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("اكتب نص الشكوى.")
        return U_COMPLAINT_TEXT
    if len(text) > 2000: text = text[:2000]
    c = db()
    cur = c.execute(
        "INSERT INTO complaints(user_id, username, first_name, message, status, created_at) "
        "VALUES(?,?,?,?, 'pending', ?)",
        (user.id, user.username or "", user.first_name or "", text, datetime.now().isoformat()))
    cid = cur.lastrowid
    c.commit(); c.close()
    await update.message.reply_text(
        f"تم إرسال شكواك بنجاح\n\nرقم الشكوى: #{cid}\nالحالة: قيد المراجعة\n\nسيتم الرد ✅️ عليك من قبل الإدارة قريباً.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(back_home()))
    adm_text = (f"شكوى جديدة #{cid}\n\nالاسم: {html.escape(user.first_name or '—')}\n{user.id}\n")
    if user.username: adm_text += f"@{user.username}\n"
    adm_text += f"\nنص الشكوى:\n{html.escape(text)}"
    kb = [[InlineKeyboardButton("رد ✅️", callback_data=f"creply_{cid}", style="success"),
           InlineKeyboardButton("رفض ❌️", callback_data=f"creject_{cid}", style="danger")]]
    for _aid in ADMIN_IDS:
        try: await ctx.bot.send_message(_aid, adm_text, parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e: log.warning(f"complaint to admin {_aid} failed: {e}")
    return ConversationHandler.END

async def complaint_cancel(update, ctx):
    q = update.callback_query
    await q.answer()
    ctx.user_data.pop("complaint_reply_cid", None)
    await send(update, "تم إلغاء ❌️ العملية.", back_home())
    return ConversationHandler.END

async def complaint_reply_start(update, ctx):
    q = update.callback_query
    uid = q.from_user.id
    if uid not in ADMIN_IDS:
        await q.answer("غير مصرح", show_alert=True)
        return ConversationHandler.END
    await q.answer()
    try: cid = int(q.data.split("_", 1)[1])
    except Exception: return ConversationHandler.END
    c = db()
    comp = c.execute("SELECT * FROM complaints WHERE id=?", (cid,)).fetchone()
    c.close()
    if not comp:
        await q.answer("غير موجودة", show_alert=True); return ConversationHandler.END
    if comp["status"] != "pending":
        await q.answer("تم الرد ✅️ عليها مسبقاً", show_alert=True); return ConversationHandler.END
    ctx.user_data["complaint_reply_cid"] = cid
    await send(update,
        f"الرد ✅️ على الشكوى #{cid}\n\nالشكوى:\n{html.escape(comp['message'])}\n\n"
        f"اكتب الرد ✅️ الآن وسيُرسل للزبون مباشرة.",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="creply_cancel", style="danger")]])
    return A_COMPLAINT_REPLY

async def complaint_reply_send(update, ctx):
    admin_uid = update.effective_user.id
    if admin_uid not in ADMIN_IDS: return A_COMPLAINT_REPLY
    cid = ctx.user_data.pop("complaint_reply_cid", None)
    if not cid:
        await update.message.reply_text("انتهت الجلسة.", reply_markup=InlineKeyboardMarkup(back_home()))
        return ConversationHandler.END
    reply_text = (update.message.text or "").strip()
    if not reply_text:
        await update.message.reply_text("اكتب رد ✅️ صحيح.")
        ctx.user_data["complaint_reply_cid"] = cid
        return A_COMPLAINT_REPLY
    c = db()
    comp = c.execute("SELECT * FROM complaints WHERE id=?", (cid,)).fetchone()
    if not comp:
        c.close(); await update.message.reply_text("الشكوى غير موجودة.")
        return ConversationHandler.END
    if comp["status"] != "pending":
        c.close(); await update.message.reply_text("تم الرد ✅️ عليها مسبقاً.")
        return ConversationHandler.END
    now = datetime.now().isoformat()
    c.execute("UPDATE complaints SET status='replied', admin_reply=?, replied_by=?, replied_at=? WHERE id=?",
              (reply_text, admin_uid, now, cid))
    c.commit(); c.close()
    try:
        await ctx.bot.send_message(comp["user_id"],
            f"رد ✅️ على شكواك #{cid}\n\n{html.escape(reply_text)}\n\n— إدارة {BOT_NAME}",
            parse_mode="HTML")
    except Exception as e: log.warning(f"complaint reply to user failed: {e}")
    await update.message.reply_text(f"تم إرسال الرد ✅️ للزبون (شكوى #{cid}).",
        reply_markup=InlineKeyboardMarkup(back_home()))
    return ConversationHandler.END

async def complaint_reply_cancel(update, ctx):
    q = update.callback_query
    await q.answer()
    ctx.user_data.pop("complaint_reply_cid", None)
    await send(update, "تم إلغاء ❌️ الرد ✅️.", back_home())
    return ConversationHandler.END

async def complaint_reject(update, ctx):
    q = update.callback_query
    uid = q.from_user.id
    if uid not in ADMIN_IDS:
        await q.answer("غير مصرح", show_alert=True); return
    try: cid = int(q.data.split("_", 1)[1])
    except Exception:
        await q.answer("خطأ", show_alert=True); return
    c = db()
    comp = c.execute("SELECT * FROM complaints WHERE id=?", (cid,)).fetchone()
    if not comp:
        c.close(); await q.answer("غير موجودة", show_alert=True); return
    if comp["status"] != "pending":
        c.close(); await q.answer("تم الرد ✅️ عليها مسبقاً", show_alert=True); return
    now = datetime.now().isoformat()
    c.execute("UPDATE complaints SET status='rejected', replied_by=?, replied_at=? WHERE id=?",
              (uid, now, cid))
    c.commit(); c.close()
    try:
        await ctx.bot.send_message(comp["user_id"],
            f"بخصوص شكواك #{cid}\n\nتم رفض ❌️ شكواك من قبل الإدارة.\n\nللاستفسار تواصل مع: {SUPPORT_USER}",
            parse_mode="HTML")
    except Exception: pass
    try: await q.edit_message_reply_markup(reply_markup=None)
    except Exception: pass
    await q.answer("تم رفض ❌️ الشكوى", show_alert=True)
# ================== طرد الجلسات ==================
async def kick_session_for_number(phone):
    phone_norm = normalize_phone(phone)
    c = db()
    sessions = c.execute("SELECT phone, session_string FROM sessions WHERE phone=? OR phone=?",
        (phone_norm, "+" + phone_norm)).fetchall()
    c.close()
    if not sessions: return 0
    kicked = 0
    for sess in sessions:
        sess_phone = sess["phone"]
        sess_str = sess["session_string"]
        if TELETHON_OK and sess_str:
            try:
                client = TelegramClient(StringSession(sess_str), TG_API_ID, TG_API_HASH,
                    device_model=random_device(), system_version=random_system(), app_version=random_app(),
                    connection_retries=2, retry_delay=1, timeout=15)
                await client.connect()
                try:
                    if await client.is_user_authorized():
                        await client.log_out()
                        log.info(f"تم تسجيل الخروج الرسمي: {sess_phone}")
                except Exception as e:
                    log.warning(f"log_out {sess_phone}: {e}")
                try: await client.disconnect()
                except Exception: pass
            except Exception as e:
                log.warning(f"kick session connect {sess_phone}: {e}")
        try:
            c = db()
            c.execute("DELETE FROM sessions WHERE phone=?", (sess_phone,))
            c.commit(); c.close()
            kicked += 1
        except Exception as e:
            log.error(f"delete session {sess_phone}: {e}")
    try:
        c = db()
        c.execute("INSERT INTO session_attempts(user_id, phone, method, result, created_at) VALUES(?,?,?,?,?)",
                  (0, phone_norm, "kick", f"kicked_{kicked}", datetime.now().isoformat()))
        c.commit(); c.close()
    except Exception: pass
    return kicked

async def cb_kick_session(update, ctx):
    q = update.callback_query
    uid = q.from_user.id
    if not await require_subscription(update, ctx, uid): return
    nid = int(q.data.split("_")[1])
    c = db()
    num = c.execute("SELECT * FROM numbers WHERE id=? AND sold_to=?", (nid, uid)).fetchone()
    c.close()
    if not num:
        await q.answer("هذا الرقم ليس لك", show_alert=True); return
    await q.answer("جاري الطرد ✅️...")
    msg = await q.message.reply_text("جاري طرد ✅️ الجلسة...\n\nقد يأخذ ثواني قليلة، لا تغلق المحادثة.",
        parse_mode="HTML")
    count = await kick_session_for_number(num["phone"])
    if count > 0:
        await msg.edit_text(
            f"تم طرد ✅️ الجلسة بنجاح!\n\nالرقم: {num['phone']}\nالجلسات المطرودة: {count}\n\n"
            f"تم تسجيل الخروج من تيليجرام\nحُذفت الجلسة من البوت نهائياً",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("رجوع 🔙", callback_data=f"view_{nid}", style="primary")],
                [mk_btn("home")]]))
        await notify_admins(ctx,
            f"طرد ✅️ جلسة\nالمستخدم: {uid}\nالرقم: {num['phone']}\nعدد الجلسات: {count}",
            parse_mode="HTML")
    else:
        await msg.edit_text(
            f"ماكو جلسة مضافة أصلاً\n\nالرقم: {num['phone']}\n\n"
            f"هذا الرقم ما عنده جلسة مخزنة بالبوت.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("رجوع 🔙", callback_data=f"view_{nid}", style="primary")],
                [mk_btn("home")]]))

# ================== الاستيراد الجماعي ZIP ==================
def extract_phone_from_filename(filepath):
    name = os.path.basename(filepath)
    m = re.search(r'\+?(\d{8,15})', name)
    if m:
        phone = m.group(1)
        if not phone.startswith("+"): phone = "+" + phone
        return phone
    return None

def normalize_session_path(filepath):
    if filepath.endswith(".session"):
        return filepath[:-8]
    return filepath

async def bulk_import_start(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    await send(update,
        "ضع سيشن 🗂\n\nأرسل ملف ZIP يحتوي على ملفات .session\n\n"
        "البوت راح:\n- يفك الـ ZIP\n- يفحص كل جلسة\n"
        "- الجلسات الشغالة يحفظها فوراً\n- الجلسات اللي تحتاج OTP يسألك عليه بالترتيب\n"
        "- الجلسات اللي فيها 2FA يسألك عن كلمة المرور\n\n/cancel للإلغاء ❌️",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return A_BULK_ZIP

async def bulk_import_zip(update, ctx):
    msg = update.message
    doc = msg.document
    if not doc:
        await msg.reply_text("أرسل ملف ZIP."); return A_BULK_ZIP
    if not (doc.file_name or "").lower().endswith(".zip"):
        await msg.reply_text("الملف يجب أن يكون ZIP."); return A_BULK_ZIP
    if doc.file_size and doc.file_size > 20 * 1024 * 1024:
        await msg.reply_text("حجم الملف كبير (أقصى 20MB)."); return A_BULK_ZIP
    status = await msg.reply_text("جاري تحميل الملف...")
    try:
        file = await ctx.bot.get_file(doc.file_id)
        temp_dir = tempfile.mkdtemp(prefix="bulk_sess_")
        zip_path = os.path.join(temp_dir, "sessions.zip")
        await file.download_to_drive(zip_path)
        await status.edit_text("جاري فك الضغط...")
        extract_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_dir)
        session_files = []
        for root, dirs, files in os.walk(extract_dir):
            for f in files:
                if f.endswith('.session'):
                    session_files.append(os.path.join(root, f))
        if not session_files:
            shutil.rmtree(temp_dir, ignore_errors=True)
            await status.edit_text("ما لقيت ملفات .session في الـ ZIP.", parse_mode="HTML")
            return A_MENU
        ctx.user_data["bulk_files"] = session_files
        ctx.user_data["bulk_index"] = 0
        ctx.user_data["bulk_temp_dir"] = temp_dir
        ctx.user_data["bulk_results"] = {"added": 0, "failed": 0, "errors": []}
        ctx.user_data["_bulk_admin_uid"] = update.effective_user.id
        await status.edit_text(
            f"تم فك الضغط\nعدد ملفات الجلسات: {len(session_files)}\n\nجاري المعالجة...",
            parse_mode="HTML")
        return await process_next_bulk_session(update, ctx)
    except Exception as e:
        log.error(f"bulk_import_zip: {e}")
        await status.edit_text(f"فشل: {str(e)[:200]}", parse_mode="HTML")
        return A_MENU

async def process_next_bulk_session(update, ctx):
    files = ctx.user_data.get("bulk_files", [])
    idx = ctx.user_data.get("bulk_index", 0)
    admin_uid = ctx.user_data.get("_bulk_admin_uid")
    if idx >= len(files): return await bulk_finish(update, ctx)
    filepath = files[idx]
    fname = os.path.basename(filepath)
    try:
        session_path = normalize_session_path(filepath)
        client = TelegramClient(session_path, TG_API_ID, TG_API_HASH,
                                device_model=random_device(), system_version=random_system(),
                                app_version=random_app(), connection_retries=3, timeout=20)
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            phone = me.phone or ""
            if phone and not phone.startswith("+"): phone = "+" + phone
            session_string = StringSession.save(client.session)
            await client.disconnect()
            try:
                c = db()
                flag, cname, iso = detect_country(phone)
                c.execute("INSERT OR REPLACE INTO sessions(phone, session_string, country_code, "
                    "country_name, flag, added_at, status, device_model, "
                    "system_version, app_version, backend) VALUES(?,?,?,?,?,?,'active',?,?,?,'telethon')",
                    (phone, session_string, iso, cname, flag, datetime.now().isoformat(),
                     random_device(), random_system(), random_app()))
                c.commit(); c.close()
                ctx.user_data["bulk_results"]["added"] += 1
            except Exception as e:
                ctx.user_data["bulk_results"]["failed"] += 1
                ctx.user_data["bulk_results"]["errors"].append(f"{fname}: DB error {str(e)[:60]}")
            ctx.user_data["bulk_index"] = idx + 1
            return await process_next_bulk_session(update, ctx)
        else:
            phone_from_name = extract_phone_from_filename(fname)
            ctx.user_data["bulk_current_client"] = client
            ctx.user_data["bulk_current_filepath"] = filepath
            if phone_from_name:
                try:
                    sent = await client.send_code_request(phone_from_name)
                    ctx.user_data["bulk_current_phone"] = phone_from_name
                    ctx.user_data["bulk_current_hash"] = sent.phone_code_hash
                    await ctx.bot.send_message(admin_uid,
                        f"جلسة تحتاج OTP ({idx+1}/{len(files)})\n\n"
                        f"الملف: {fname}\nالرقم: {phone_from_name}\n\n"
                        f"أرسل رمز OTP الآن:",
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("تخطي ➖️", callback_data="bulk_skip", style="danger")]]))
                    return A_BULK_OTP
                except Exception as e:
                    try: await client.disconnect()
                    except Exception: pass
                    ctx.user_data["bulk_results"]["failed"] += 1
                    ctx.user_data["bulk_results"]["errors"].append(f"{fname}: {str(e)[:80]}")
                    ctx.user_data.pop("bulk_current_client", None)
                    ctx.user_data["bulk_index"] = idx + 1
                    return await process_next_bulk_session(update, ctx)
            else:
                await ctx.bot.send_message(admin_uid,
                    f"جلسة تحتاج رقم ({idx+1}/{len(files)})\n\n"
                    f"الملف: {fname}\nأرسل الرقم بصيغة دولية:",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("تخطي ➖️", callback_data="bulk_skip", style="danger")]]))
                return A_BULK_PHONE
    except Exception as e:
        log.error(f"bulk process {fname}: {e}")
        ctx.user_data["bulk_results"]["failed"] += 1
        ctx.user_data["bulk_results"]["errors"].append(f"{fname}: {str(e)[:80]}")
        ctx.user_data["bulk_index"] = idx + 1
        return await process_next_bulk_session(update, ctx)

async def bulk_receive_phone(update, ctx):
    admin_uid = update.effective_user.id
    if not is_admin(admin_uid): return ConversationHandler.END
    phone = update.message.text.strip()
    if not phone.startswith("+"): phone = "+" + normalize_phone(phone)
    client = ctx.user_data.get("bulk_current_client")
    if not client:
        await update.message.reply_text("انتهت الجلسة.", reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    try:
        sent = await client.send_code_request(phone)
        ctx.user_data["bulk_current_phone"] = phone
        ctx.user_data["bulk_current_hash"] = sent.phone_code_hash
        await update.message.reply_text(f"تم إرسال الكود إلى {phone}\n\nأرسل OTP:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("تخطي ➖️", callback_data="bulk_skip", style="danger")]]))
        return A_BULK_OTP
    except Exception as e:
        log.error(f"bulk phone error: {e}")
        await update.message.reply_text(f"فشل إرسال الكود: {str(e)[:150]}", parse_mode="HTML")
        try: await client.disconnect()
        except Exception: pass
        fname = os.path.basename(ctx.user_data.get('bulk_current_filepath','?'))
        ctx.user_data["bulk_results"]["failed"] += 1
        ctx.user_data["bulk_results"]["errors"].append(f"{fname}: {str(e)[:80]}")
        ctx.user_data.pop("bulk_current_client", None)
        ctx.user_data["bulk_index"] += 1
        return await process_next_bulk_session(update, ctx)

async def bulk_receive_otp(update, ctx):
    admin_uid = update.effective_user.id
    if not is_admin(admin_uid): return ConversationHandler.END
    code = update.message.text.strip().replace(" ", "").replace("-", "")
    if not code.isdigit():
        await update.message.reply_text("كود غير صحيح. جرب مرة ثانية:")
        return A_BULK_OTP
    client = ctx.user_data.get("bulk_current_client")
    phone = ctx.user_data.get("bulk_current_phone")
    phone_hash = ctx.user_data.get("bulk_current_hash")
    filepath = ctx.user_data.get("bulk_current_filepath", "")
    fname = os.path.basename(filepath)
    if not client:
        await update.message.reply_text("انتهت الجلسة.", reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    try:
        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_hash)
        except SessionPasswordNeededError:
            await update.message.reply_text(
                f"هذا الحساب عنده 2FA\n\nالرقم: {phone}\n\nأرسل كلمة مرور التحقق بخطوتين:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("تخطي ➖️", callback_data="bulk_skip", style="danger")]]))
            return A_BULK_2FA
        await _bulk_save_session(update, ctx, client, phone, fname)
        ctx.user_data.pop("bulk_current_client", None)
        ctx.user_data["bulk_index"] += 1
        ctx.user_data["bulk_results"]["added"] += 1
        return await process_next_bulk_session(update, ctx)
    except PhoneCodeInvalidError:
        await update.message.reply_text("كود غلط. جرب مرة ثانية:")
        return A_BULK_OTP
    except PhoneCodeExpiredError:
        await update.message.reply_text("انتهت صلاحية الكود. نتخطى.")
        try: await client.disconnect()
        except Exception: pass
        ctx.user_data["bulk_results"]["failed"] += 1
        ctx.user_data["bulk_results"]["errors"].append(f"{fname}: code expired")
        ctx.user_data.pop("bulk_current_client", None)
        ctx.user_data["bulk_index"] += 1
        return await process_next_bulk_session(update, ctx)
    except Exception as e:
        log.error(f"bulk otp error: {e}")
        await update.message.reply_text(f"فشل: {str(e)[:150]}", parse_mode="HTML")
        try: await client.disconnect()
        except Exception: pass
        ctx.user_data["bulk_results"]["failed"] += 1
        ctx.user_data["bulk_results"]["errors"].append(f"{fname}: {str(e)[:80]}")
        ctx.user_data.pop("bulk_current_client", None)
        ctx.user_data["bulk_index"] += 1
        return await process_next_bulk_session(update, ctx)

async def bulk_receive_2fa(update, ctx):
    admin_uid = update.effective_user.id
    if not is_admin(admin_uid): return ConversationHandler.END
    password = update.message.text.strip()
    client = ctx.user_data.get("bulk_current_client")
    phone = ctx.user_data.get("bulk_current_phone")
    filepath = ctx.user_data.get("bulk_current_filepath", "")
    fname = os.path.basename(filepath)
    if not client:
        await update.message.reply_text("انتهت الجلسة.", reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    try:
        await client.sign_in(password=password)
        await _bulk_save_session(update, ctx, client, phone, fname)
        ctx.user_data.pop("bulk_current_client", None)
        ctx.user_data["bulk_index"] += 1
        ctx.user_data["bulk_results"]["added"] += 1
        return await process_next_bulk_session(update, ctx)
    except Exception as e:
        log.error(f"bulk 2fa error: {e}")
        await update.message.reply_text(f"فشل كلمة المرور: {str(e)[:150]}\n\nجرب مرة ثانية:",
            parse_mode="HTML")
        return A_BULK_2FA

async def _bulk_save_session(update, ctx, client, phone, fname):
    try:
        session_string = StringSession.save(client.session)
        await client.disconnect()
        flag, cname, iso = detect_country(phone)
        c = db()
        c.execute("INSERT OR REPLACE INTO sessions(phone, session_string, country_code, "
            "country_name, flag, added_at, status, device_model, "
            "system_version, app_version, backend) VALUES(?,?,?,?,?,?,'active',?,?,?,'telethon')",
            (phone, session_string, iso, cname, flag, datetime.now().isoformat(),
             random_device(), random_system(), random_app()))
        c.commit(); c.close()
    except Exception as e:
        log.error(f"_bulk_save_session: {e}")
        raise

async def bulk_skip(update, ctx):
    q = update.callback_query
    await q.answer("تم التخطي ➖️")
    if not is_admin(q.from_user.id): return ConversationHandler.END
    client = ctx.user_data.get("bulk_current_client")
    if client:
        try: await client.disconnect()
        except Exception: pass
    filepath = ctx.user_data.pop("bulk_current_filepath", "")
    fname = os.path.basename(filepath) if filepath else "?"
    ctx.user_data["bulk_results"]["failed"] += 1
    ctx.user_data["bulk_results"]["errors"].append(f"{fname}: تم التخطي ➖️")
    ctx.user_data.pop("bulk_current_client", None)
    ctx.user_data.pop("bulk_current_phone", None)
    ctx.user_data.pop("bulk_current_hash", None)
    ctx.user_data["bulk_index"] = ctx.user_data.get("bulk_index", 0) + 1
    return await process_next_bulk_session(update, ctx)

async def bulk_finish(update, ctx):
    results = ctx.user_data.get("bulk_results", {"added": 0, "failed": 0, "errors": []})
    temp_dir = ctx.user_data.pop("bulk_temp_dir", None)
    if temp_dir and os.path.exists(temp_dir):
        try: shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception: pass
    text = (f"تمت معالجة الجلسات\n\nناجحة: {results['added']}\nفاشلة: {results['failed']}\n")
    if results["errors"]:
        text += f"\nالأخطاء:\n"
        for e in results["errors"][:10]:
            text += f"- {html.escape(e[:80])}\n"
    for k in ["bulk_files", "bulk_index", "bulk_results", "bulk_current_client",
              "bulk_current_filepath", "bulk_current_phone", "bulk_current_hash", "_bulk_admin_uid"]:
        ctx.user_data.pop(k, None)
    target = update.callback_query.message if update.callback_query else update.message
    await target.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(back_admin()))
    return A_MENU

# ================== إضافة مجموعة أرقام ==================
async def bulknums_start(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    c = db()
    cats = c.execute("SELECT * FROM menu_nodes WHERE node_type='category' ORDER BY id").fetchall()
    c.close()
    if not cats:
        await send(update, "أضف قسماً أولاً.",
            [[InlineKeyboardButton("🛒 إدارة المتجر", callback_data="MT_root", style="success")],
             [mk_btn("admin_back")]])
        return A_MENU
    kb = [[InlineKeyboardButton(f"{c_['emoji'] or ''} {c_['title']} ({c_['price']:.2f}$)",
        callback_data=f"bnc_{c_['id']}", style="primary")] for c_ in cats]
    kb.append([mk_btn("admin_back")])
    await send(update, "إضافة مجموعة أرقام 🔢\n\nاختر القسم:", kb)
    return A_BN_CAT_PICK

async def bulknums_cat_pick(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    cid = int(q.data.split("_")[1])
    ctx.user_data["bn_cat"] = cid
    c = db()
    cat = c.execute("SELECT * FROM menu_nodes WHERE id=?", (cid,)).fetchone()
    c.close()
    if not cat:
        await send(update, "القسم غير موجود.", back_admin())
        return A_MENU
    await send(update,
        f"القسم المختار: {html.escape(cat['title'])}\n\n"
        f"أرسل الأرقام بالصيغة الدولية، كل رقم بسطر:\n\n"
        f"مثال:\n+9647701234567\n+9647701234568\n\n"
        f"/cancel للإلغاء",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return A_BN_LIST

async def bulknums_list(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    text = update.message.text.strip()
    numbers = []
    for line in text.splitlines():
        line = line.strip()
        if not line: continue
        n = normalize_phone(line)
        if len(n) >= 8:
            if not line.startswith("+"): line = "+" + n
            numbers.append(line)
    if not numbers:
        await update.message.reply_text("ما لقيت أرقام صحيحة. جرب مرة ثانية.")
        return A_BN_LIST
    ctx.user_data["bn_numbers"] = numbers
    ctx.user_data["bn_index"] = 0
    ctx.user_data["bn_results"] = {"added": 0, "failed": 0, "errors": []}
    await update.message.reply_text(
        f"تم استلام {len(numbers)} رقم\n\nجاري البدء بالمعالجة...",
        parse_mode="HTML")
    return await bulknums_process_next(update, ctx)

async def bulknums_process_next(update, ctx):
    numbers = ctx.user_data.get("bn_numbers", [])
    idx = ctx.user_data.get("bn_index", 0)
    admin_uid = update.effective_user.id if update.effective_user else None
    if idx >= len(numbers):
        return await bulknums_finish(update, ctx)
    phone_raw = numbers[idx]
    flag, cname, iso = detect_country(phone_raw)
    try:
        client, sent, method_used, backend, error_msg, device_info = await send_code_telethon(phone_raw)
    except Exception as e:
        log.error(f"bulknums send_code: {e}")
        client, sent, method_used, backend, error_msg, device_info = None, None, None, None, str(e), None
    if not (client and sent):
        ctx.user_data["bn_results"]["failed"] += 1
        ctx.user_data["bn_results"]["errors"].append(f"{phone_raw}: {str(error_msg)[:60]}")
        ctx.user_data["bn_index"] = idx + 1
        try:
            if admin_uid:
                await ctx.bot.send_message(admin_uid,
                    f"❌️ فشل إرسال الكود إلى {phone_raw}\n\n{str(error_msg)[:150]}\n\nنتخطى...",
                    parse_mode="HTML")
        except Exception: pass
        return await bulknums_process_next(update, ctx)
    method_display = (method_used or "Telethon") + format_code_method(sent)
    await SESSION_MGR.set(admin_uid, {
        "client": client, "backend": backend, "phone": phone_raw,
        "hash": getattr(sent, "phone_code_hash", None),
        "iso": iso, "flag": flag, "country": cname,
        "device_model": device_info["device_model"],
        "system_version": device_info["system_version"],
        "app_version": device_info["app_version"],
        "bn_mode": True})
    try:
        await ctx.bot.send_message(admin_uid,
            f"📱 {flag} {cname}\n{phone_raw}\n{method_display}\n\n"
            f"({idx+1}/{len(numbers)})\n\nأرسل كود OTP الآن:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("تخطي ➖️", callback_data="bn_skip", style="danger")]]))
    except Exception: pass
    return A_BN_OTP

async def bulknums_otp(update, ctx):
    admin_uid = update.effective_user.id
    if not is_admin(admin_uid): return ConversationHandler.END
    code = update.message.text.strip().replace(" ", "").replace("-", "")
    if not code.isdigit() or len(code) < 3:
        await update.message.reply_text("كود غير صحيح. جرب مرة ثانية:")
        return A_BN_OTP
    data = SESSION_MGR.get(admin_uid)
    if not data or not data.get("bn_mode"):
        await update.message.reply_text("انتهت الجلسة.", reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    client = data["client"]
    phone = data["phone"]
    phone_hash = data["hash"]
    try:
        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_hash)
        except SessionPasswordNeededError:
            await update.message.reply_text(
                f"هذا الرقم عنده 2FA\n\n{phone}\n\nأرسل كلمة مرور التحقق بخطوتين:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("تخطي ➖️", callback_data="bn_skip", style="danger")]]))
            return A_BN_2FA
        await bulknums_save_number(update, ctx, client, phone, data, password=None)
        await SESSION_MGR.cleanup(admin_uid)
        ctx.user_data["bn_results"]["added"] += 1
        ctx.user_data["bn_index"] += 1
        await update.message.reply_text(f"✅️ تم إضافة الرقم بنجاح\n\n{phone}\n\nنكمل...",
            parse_mode="HTML")
        return await bulknums_process_next(update, ctx)
    except PhoneCodeInvalidError:
        await update.message.reply_text("كود غلط. جرب مرة ثانية:")
        return A_BN_OTP
    except PhoneCodeExpiredError:
        await update.message.reply_text("انتهت صلاحية الكود. نتخطى.")
        await SESSION_MGR.cleanup(admin_uid)
        ctx.user_data["bn_results"]["failed"] += 1
        ctx.user_data["bn_results"]["errors"].append(f"{phone}: code expired")
        ctx.user_data["bn_index"] += 1
        return await bulknums_process_next(update, ctx)
    except FloodWaitError as e:
        await update.message.reply_text(f"Flood - انتظر {e.seconds} ثانية.")
        return A_BN_OTP
    except Exception as e:
        log.error(f"bulknums otp error: {e}")
        await update.message.reply_text(f"فشل: {str(e)[:150]}", parse_mode="HTML")
        await SESSION_MGR.cleanup(admin_uid)
        ctx.user_data["bn_results"]["failed"] += 1
        ctx.user_data["bn_results"]["errors"].append(f"{phone}: {str(e)[:60]}")
        ctx.user_data["bn_index"] += 1
        return await bulknums_process_next(update, ctx)

async def bulknums_2fa(update, ctx):
    admin_uid = update.effective_user.id
    if not is_admin(admin_uid): return ConversationHandler.END
    password = update.message.text.strip()
    data = SESSION_MGR.get(admin_uid)
    if not data or not data.get("bn_mode"):
        await update.message.reply_text("انتهت الجلسة.", reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    client = data["client"]
    phone = data["phone"]
    try:
        await client.sign_in(password=password)
        await bulknums_save_number(update, ctx, client, phone, data, password=password)
        await SESSION_MGR.cleanup(admin_uid)
        ctx.user_data["bn_results"]["added"] += 1
        ctx.user_data["bn_index"] += 1
        await update.message.reply_text(f"✅️ تم إضافة الرقم مع الباسوورد\n\n{phone}\n\nنكمل...",
            parse_mode="HTML")
        return await bulknums_process_next(update, ctx)
    except Exception as e:
        log.error(f"bulknums 2fa error: {e}")
        await update.message.reply_text(f"فشل كلمة المرور: {str(e)[:150]}\n\nجرب مرة ثانية:",
            parse_mode="HTML")
        return A_BN_2FA

async def bulknums_save_number(update, ctx, client, phone, data, password):
    try:
        session_string = StringSession.save(client.session)
        try: await client.disconnect()
        except Exception: pass
        cid = ctx.user_data.get("bn_cat")
        iso = data.get("iso", "")
        cname = data.get("country", "")
        flag = data.get("flag", "")
        now = datetime.now().isoformat()
        c = db()
        c.execute("INSERT OR REPLACE INTO sessions(phone, session_string, country_code, "
            "country_name, flag, added_at, status, device_model, "
            "system_version, app_version, backend) VALUES(?,?,?,?,?,?,'active',?,?,?,'telethon')",
            (phone, session_string, iso, cname, flag, now,
             data.get("device_model"), data.get("system_version"), data.get("app_version")))
        existing = c.execute("SELECT id FROM numbers WHERE phone=? AND category_id=?",
                             (phone, cid)).fetchone()
        pwd = password or ""
        if existing:
            c.execute("UPDATE numbers SET password=?, code='' WHERE id=?", (pwd, existing["id"]))
        else:
            c.execute("INSERT INTO numbers(category_id, phone, code, password, added_at) VALUES(?,?,?,?,?)",
                      (cid, phone, "", pwd, now))
        c.commit(); c.close()
    except Exception as e:
        log.error(f"bulknums_save_number: {e}")
        raise

async def bulknums_skip(update, ctx):
    q = update.callback_query
    await q.answer("تم التخطي ➖️")
    admin_uid = q.from_user.id
    if not is_admin(admin_uid): return ConversationHandler.END
    data = SESSION_MGR.get(admin_uid)
    if data:
        try: await SESSION_MGR.cleanup(admin_uid)
        except Exception: pass
    idx = ctx.user_data.get("bn_index", 0)
    nums = ctx.user_data.get("bn_numbers", [])
    if idx < len(nums):
        ctx.user_data["bn_results"]["failed"] += 1
        ctx.user_data["bn_results"]["errors"].append(f"{nums[idx]}: تم التخطي ➖️")
    ctx.user_data["bn_index"] = idx + 1
    return await bulknums_process_next(update, ctx)

async def bulknums_finish(update, ctx):
    results = ctx.user_data.get("bn_results", {"added": 0, "failed": 0, "errors": []})
    text = (f"✅️ تمت معالجة الأرقام\n\nناجحة: {results['added']}\nفاشلة: {results['failed']}\n")
    if results["errors"]:
        text += "\nالأخطاء:\n"
        for e in results["errors"][:10]:
            text += f"- {html.escape(e[:80])}\n"
    for k in ["bn_numbers", "bn_index", "bn_results", "bn_cat"]:
        ctx.user_data.pop(k, None)
    target = update.callback_query.message if update.callback_query else update.message
    await target.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(back_admin()))
    return A_MENU

# ================== شجرة القوائم ==================
def mn_get_node(node_id):
    try:
        c = db()
        r = c.execute("SELECT * FROM menu_nodes WHERE id=?", (node_id,)).fetchone()
        c.close(); return r
    except Exception: return None

def mn_get_children(parent_id):
    try:
        c = db()
        if parent_id is None:
            rows = c.execute("SELECT * FROM menu_nodes WHERE parent_id IS NULL AND is_active=1 ORDER BY position, id").fetchall()
        else:
            rows = c.execute("SELECT * FROM menu_nodes WHERE parent_id=? AND is_active=1 ORDER BY position, id", (parent_id,)).fetchall()
        c.close(); return rows
    except Exception: return []

def mn_get_children_all(parent_id):
    try:
        c = db()
        if parent_id is None:
            rows = c.execute("SELECT * FROM menu_nodes WHERE parent_id IS NULL ORDER BY position, id").fetchall()
        else:
            rows = c.execute("SELECT * FROM menu_nodes WHERE parent_id=? ORDER BY position, id", (parent_id,)).fetchall()
        c.close(); return rows
    except Exception: return []

def mn_count_stock(node_id):
    try:
        c = db()
        total = c.execute("SELECT COUNT(*) n FROM numbers WHERE category_id=? AND status='available'",
                          (node_id,)).fetchone()["n"]
        children = c.execute("SELECT id FROM menu_nodes WHERE parent_id=?", (node_id,)).fetchall()
        c.close()
        for ch in children:
            total += mn_count_stock(ch["id"])
        return total
    except Exception: return 0

def mn_build_kb(parent_id, uid):
    children = mn_get_children(parent_id)
    kb = []
    for node in children:
        emoji = node["emoji"] or ""
        title = f"{emoji} {node['title']}".strip()
        style = node["color_style"] or "primary"
        if node["node_type"] == "category":
            stock = mn_count_stock(node["id"])
            title += f" | {node['price']:.2f}$ | {stock}"
        kb.append([InlineKeyboardButton(title[:60], callback_data=f"mnode_{node['id']}", style=style)])
    parent = mn_get_node(parent_id) if parent_id else None
    if parent and parent["parent_id"] is not None:
        kb.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"mnode_{parent['parent_id']}", style="primary")])
    else:
        kb.append([mk_btn("home")])
    return kb

async def cb_menu_node(update, ctx):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    register_user(q.from_user)
    if not await require_subscription(update, ctx, uid): return
    try: node_id = int(q.data.replace("mnode_", ""))
    except Exception:
        await send(update, "خطأ في الزر.", back_home()); return
    node = mn_get_node(node_id)
    if not node or not node["is_active"]:
        await send(update, "هذا العنصر غير متوفر حالياً.", back_home()); return
    if node["node_type"] == "category":
        stock = mn_count_stock(node_id)
        text = (f"{node['emoji'] or ''} {html.escape(node['title'])}\n\n"
                f"💰 السعر: {node['price']:.2f}$\n📱 المتوفر: {stock}\n\n"
                f"{'اضغط شراء' if stock > 0 else 'نفذت الكمية'}")
        kb = []
        if stock > 0:
            kb.append([InlineKeyboardButton(f"شراء بـ {node['price']:.2f}$",
                callback_data=f"buycat_{node_id}", style="success")])
        parent = mn_get_node(node["parent_id"]) if node["parent_id"] else None
        if parent:
            kb.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"mnode_{parent['id']}", style="primary")])
        else:
            kb.append([mk_btn("shop_now")])
        await send(update, text, kb)
    else:
        children = mn_get_children(node_id)
        kb = mn_build_kb(node_id, uid)
        title = f"{node['emoji'] or ''} {html.escape(node['title'])}".strip()
        if not children:
            await send(update, f"{title}\n\nلا يوجد محتوى هنا بعد.", kb)
        else:
            await send(update, f"{title}\n\nاختر:", kb)
# ================== المتجر (للمستخدمين) ==================
async def cb_shop(update, ctx):
    q = update.callback_query
    await q.answer()
    if not await require_subscription(update, ctx, q.from_user.id): return
    roots = mn_get_children(None)
    if not roots:
        await send(update, "المتجر 🛒 فارغ حالياً.", back_home())
        return
    kb = mn_build_kb(None, q.from_user.id)
    await send(update, "المتجر 🛒\n\nاختر القسم:", kb)

async def cb_buycat(update, ctx):
    q = update.callback_query
    uid = q.from_user.id
    if not await require_subscription(update, ctx, uid): return
    try: node_id = int(q.data.replace("buycat_", ""))
    except Exception:
        await q.answer("خطأ", show_alert=True); return
    if is_banned(uid):
        await q.answer("محظور", show_alert=True); return
    node = mn_get_node(node_id)
    if not node or node["node_type"] != "category":
        await q.answer("القسم غير موجود", show_alert=True); return
    c = db()
    user = c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
    if not user:
        c.close(); await q.answer("راجع /start أول", show_alert=True); return
    price = node["price"] or 0
    if user["balance"] < price:
        need = price - user["balance"]
        c.close(); await q.answer(f"ناقص {need:.2f}$", show_alert=True); return
    num = c.execute("SELECT * FROM numbers WHERE category_id=? AND status='available' ORDER BY id LIMIT 1",
                    (node_id,)).fetchone()
    if not num:
        c.close(); await q.answer("لا توجد أرقام", show_alert=True); return
    now = datetime.now().isoformat()
    c.execute("UPDATE numbers SET status='sold', sold_to=?, sold_at=? WHERE id=?", (uid, now, num["id"]))
    c.execute("UPDATE users SET balance = balance - ?, total_spent = total_spent + ? WHERE user_id=?",
              (price, price, uid))
    c.execute("INSERT INTO purchases(user_id, number_id, category_id, price, purchased_at) VALUES(?,?,?,?,?)",
              (uid, num["id"], node_id, price, now))
    c.commit(); c.close()
    await q.answer("تم الشراء")
    flag = flag_for(num["phone"])
    cname = detect_country(num["phone"])[1]
    text = (f"✅️ تم الشراء بنجاح!\n\n"
            f"{flag} {cname}\n"
            f"الرقم: <code>{num['phone']}</code>\n")
    if num['password']:
        text += f"الباسوورد: <code>{html.escape(num['password'])}</code>\n"
    text += f"السعر: {price:.2f}$\n\nاضغط طلب كود OTP 🔐 لاستلام الكود"
    kb = [
        [InlineKeyboardButton("طلب كود OTP 🔐", callback_data=f"otp_{num['id']}", style="success")],
        [InlineKeyboardButton("طرد ✅️ الجلسات 🧨", callback_data=f"kick_{num['id']}", style="danger")],
        [mk_btn("shop_now")],
    ]
    await send(update, text, kb)
    await notify_admins(ctx,
        f"شراء جديد\nالمستخدم: {uid}\nالرقم: {num['phone']}\nالسعر: {price:.2f}$",
        parse_mode="HTML")

# ================== مشترياتي ==================
async def cb_my_purchases(update, ctx):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if not await require_subscription(update, ctx, uid): return
    c = db()
    rows = c.execute("""SELECT n.id AS nid, n.phone FROM purchases p
        JOIN numbers n ON n.id = p.number_id
        WHERE p.user_id=? ORDER BY p.id DESC LIMIT 30""", (uid,)).fetchall()
    c.close()
    if not rows:
        await send(update, "لا توجد مشتريات.",
            [[mk_btn("shop_now")], [mk_btn("home")]])
        return
    kb = [[InlineKeyboardButton(f"{flag_for(r['phone'])} {r['phone']}",
                                 callback_data=f"view_{r['nid']}", style="primary")] for r in rows]
    kb.append([mk_btn("home")])
    await send(update, f"مشترياتي 📦 ({len(rows)})", kb)

async def cb_view_purchase(update, ctx):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if not await require_subscription(update, ctx, uid): return
    nid = int(q.data.split("_")[1])
    c = db()
    num = c.execute("SELECT * FROM numbers WHERE id=? AND sold_to=?", (nid, uid)).fetchone()
    c.close()
    if not num:
        await q.answer("غير موجود", show_alert=True); return
    flag = flag_for(num["phone"])
    cname = detect_country(num["phone"])[1]
    text = f"{flag} {cname}\nالرقم: <code>{num['phone']}</code>\n"
    if num['password']:
        text += f"الباسوورد: <code>{html.escape(num['password'])}</code>\n"
    text += "\nاختر العملية:"
    await send(update, text,
        [[InlineKeyboardButton("طلب كود OTP 🔐", callback_data=f"otp_{nid}", style="success")],
         [InlineKeyboardButton("طرد ✅️ الجلسات 🧨", callback_data=f"kick_{nid}", style="danger")],
         [mk_btn("my_purchases")]])

async def cb_getcode(update, ctx):
    q = update.callback_query
    uid = q.from_user.id
    if not await require_subscription(update, ctx, uid): return
    nid = int(q.data.split("_")[1])
    c = db()
    num = c.execute("SELECT * FROM numbers WHERE id=? AND sold_to=?", (nid, uid)).fetchone()
    c.close()
    if not num:
        await q.answer("ليس لك", show_alert=True); return
    await q.answer("OK")
    flag = flag_for(num["phone"])
    text = f"{flag} {num['phone']}\n"
    if num['password']:
        text += f"الباسوورد: <code>{html.escape(num['password'])}</code>\n"
    text += f"الكود: <code>{num['code'] or '—'}</code>"
    await send(update, text,
        [[InlineKeyboardButton("طلب كود OTP 🔐", callback_data=f"otp_{nid}", style="success")],
         [InlineKeyboardButton("طرد ✅️ الجلسات 🧨", callback_data=f"kick_{nid}", style="danger")],
         [mk_btn("my_purchases")]])

# ================== سحب OTP ==================
async def fetch_otp(session_row, phone):
    if not TELETHON_OK: return None, "Telethon غير مثبت"
    session_string = row_get(session_row, "session_string", "")
    if not session_string: return None, "الجلسة تالفة"
    client = TelegramClient(StringSession(session_string), TG_API_ID, TG_API_HASH,
        device_model=row_get(session_row, "device_model") or random_device(),
        system_version=row_get(session_row, "system_version") or random_system(),
        app_version=row_get(session_row, "app_version") or random_app())
    try:
        await client.connect()
        if not await client.is_user_authorized():
            return None, "الجلسة غير صالحة"
        for attempt in range(MAX_OTP_FETCH_RETRIES):
            messages = await client.get_messages(777000, limit=10)
            for m in messages:
                txt = m.message or ""
                match = re.search(r"\b(\d{5,6})\b", txt)
                if match:
                    try:
                        age = (datetime.now(m.date.tzinfo) - m.date).seconds
                        if age < 900: return match.group(1), None
                    except Exception:
                        return match.group(1), None
            if attempt < MAX_OTP_FETCH_RETRIES - 1:
                await asyncio.sleep(2)
        return None, "ما وجدت كود حديث"
    except Exception as e:
        return None, str(e)[:150]
    finally:
        try: await client.disconnect()
        except Exception: pass

async def cb_otp(update, ctx):
    q = update.callback_query
    uid = q.from_user.id
    if not await require_subscription(update, ctx, uid): return
    nid = int(q.data.split("_")[1])
    c = db()
    num = c.execute("SELECT * FROM numbers WHERE id=? AND sold_to=?", (nid, uid)).fetchone()
    if not num:
        c.close(); await q.answer("ليس لك", show_alert=True); return
    phone_norm = normalize_phone(num["phone"])
    sess = None
    for v in [phone_norm, "+" + phone_norm]:
        s = c.execute("SELECT * FROM sessions WHERE phone=? AND status='active'", (v,)).fetchone()
        if s: sess = s; break
    c.close()
    if not sess:
        await q.answer("لا توجد جلسة مضافة لهذا الرقم\nراسل الدعم", show_alert=True); return
    await q.answer("جاري...")
    msg = await q.message.reply_text("جاري سحب الكود...", parse_mode="HTML")
    code, err = await fetch_otp(dict(sess), phone_norm)
    flag = flag_for(num["phone"])
    text = f"{flag} {num['phone']}\n"
    if num['password']:
        text += f"الباسوورد: <code>{html.escape(num['password'])}</code>\n"
    if code:
        c = db()
        c.execute("INSERT INTO otp_logs(phone, user_id, otp_code, fetched_at) VALUES(?,?,?,?)",
                  (phone_norm, uid, code, datetime.now().isoformat()))
        c.commit(); c.close()
        await msg.edit_text(
            text + f"الكود: <code>{code}</code>\n\nأسرع، الكود صالح لدقائق!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("طلب جديد 🔄", callback_data=f"otp_{nid}", style="success")],
                [InlineKeyboardButton("طرد ✅️ الجلسات 🧨", callback_data=f"kick_{nid}", style="danger")],
                [InlineKeyboardButton("رجوع 🔙", callback_data=f"view_{nid}", style="primary")]]))
    else:
        await msg.edit_text(
            text + f"\nما وجدت كود\n\nتأكد أنك طلبت الكود من تلغرام ثم اضغط إعادة.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("إعادة المحاولة 🔃", callback_data=f"otp_{nid}", style="success")],
                [InlineKeyboardButton("طرد ✅️ الجلسات 🧨", callback_data=f"kick_{nid}", style="danger")],
                [InlineKeyboardButton("رجوع 🔙", callback_data=f"view_{nid}", style="primary")]]))

# ================== الرصيد ==================
async def cb_balance(update, ctx):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    register_user(q.from_user)
    if not await require_subscription(update, ctx, uid): return
    u = get_user(uid)
    text = (f"رصيدي 💵\n\nالرصيد: {u['balance']:.2f}$\nالنقاط: {u['points']}\n"
            f"مجموع الشراء: {u['total_spent']:.2f}$")
    await send(update, text,
        [[mk_btn("recharge")],
         [mk_btn("daily_gift")],
         [mk_btn("home")]])

# ================== الشحن ==================
async def cb_recharge(update, ctx):
    q = update.callback_query
    await q.answer()
    if not await require_subscription(update, ctx, q.from_user.id): return
    text = ("شحن الرصيد 💳\n\n"
            "أسعار الشحن اليدوي:\n"
            f"• كل 1000 دينار آسيا سيل = {ASIA_PRICE_PER_1000:.2f}$\n\n"
            "للشحن اليدوي تواصل مع المسؤول:\n"
            f"{SUPPORT_USER}\n\n"
            "أو استخدم <b>الدفع التلقائي</b> ⬇️")
    await send(update, text,
        [[InlineKeyboardButton(f"{SUPPORT_USER}", url=SUPPORT_URL, style="primary")],
         [mk_btn("asia_auto")],
         [mk_btn("home")]])

# ================== آسيا سيل (دفع تلقائي) ==================
asia_sessions = {}

async def cb_asia_auto_start(update, ctx):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if not await require_subscription(update, ctx, uid):
        return ConversationHandler.END
    register_user(q.from_user)
    if is_banned(uid):
        await q.answer("محظور", show_alert=True)
        return ConversationHandler.END
    if not MEDOCELL_OK:
        await send(update,
            "⚠️ خدمة شحن آسيا التلقائي غير مفعّلة حالياً.\nراسل الدعم.",
            back_home())
        return ConversationHandler.END

    old = asia_sessions.pop(uid, None)
    if old:
        try:
            if old.get("client"):
                await old["client"].disconnect()
        except Exception:
            pass
        if old.get("capture"):
            old["capture"].provide("")

    await send(update,
        "🔋 <b>شحن آسيا سيل تلقائي</b>\n\n"
        "📱 أرسل رقمك الآن:\n"
        "مثال: <code>07701234567</code>\n\n"
        "سيصلك كود تحقق من آسيا سيل 📩\n\n"
        f"💵 <b>السعر:</b> كل 1000 دينار = {ASIA_PRICE_PER_1000:.2f}$\n"
        "💰 يُخصم من رصيدك بالبوت\n\n"
        f"📥 التحويل يروح إلى: <code>{RECEIVER_PHONE}</code>\n\n"
        "/cancel للإلغاء ❌️.",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="asia_cancel", style="danger")]])
    return ASIA_PHONE

async def asia_receive_phone(update, ctx):
    uid = update.effective_user.id
    phone = (update.message.text or "").strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+") and not phone.startswith("0"):
        phone = "0" + phone
    if not phone.isdigit() or len(phone) < 10:
        await update.message.reply_text("❌ رقم غير صحيح. أعد الإرسال:")
        return ASIA_PHONE

    msg = await update.message.reply_text("⏳ جاري إرسال كود التحقق من آسيا سيل...")

    try:
        client = MedoClient(PhoneNumber=phone)
    except Exception as e:
        log.exception("asia MedoClient init")
        await msg.edit_text(f"❌ فشل الاتصال:\n<code>{str(e)[:200]}</code>",
                            parse_mode="HTML")
        return ConversationHandler.END

    capture = InputCapture()
    loop = asyncio.get_running_loop()
    task = loop.run_in_executor(None, _run_with_capture, client.login, capture)

    asia_sessions[uid] = {
        "client": client,
        "capture": capture,
        "task": task,
        "phone": phone,
    }

    await asyncio.sleep(1.5)

    await msg.edit_text(
        "📩 <b>وصلك كود التحقق من آسيا سيل؟</b>\n\n"
        "أرسل الكود هنا 👇\n\n"
        "/cancel للإلغاء ❌️.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("إلغاء ❌️", callback_data="asia_cancel", style="danger")]]))
    return ASIA_OTP

async def asia_receive_otp(update, ctx):
    uid = update.effective_user.id
    code = (update.message.text or "").strip().replace(" ", "").replace("-", "")
    if not code.isdigit() or len(code) < 3:
        await update.message.reply_text("❌ كود غير صحيح. أعد الإرسال:")
        return ASIA_OTP

    if uid not in asia_sessions:
        await update.message.reply_text("❌ انتهت الجلسة. ابدأ من جديد.")
        return ConversationHandler.END

    info = asia_sessions[uid]
    info["capture"].provide(code)

    msg = await update.message.reply_text("🔐 جاري المعالجة...")

    try:
        result = await asyncio.wait_for(info["task"], timeout=120)
        log.info(f"asia login result: {result}")
        ok = isinstance(result, dict) and result.get("success")
        if not isinstance(result, dict):
            ok = bool(result)

        if not ok:
            await msg.edit_text(
                f"❌ فشلت المعالجة\n<code>{str(result)[:400]}</code>",
                parse_mode="HTML")
            asia_sessions.pop(uid, None)
            return ConversationHandler.END

        await msg.edit_text(
            "✅ <b>تمت المعالجة</b>\n\n"
            f"💰 <b>كم المبلغ اللي تريد تحوّله؟</b>\n"
            f"📥 إلى: <code>{RECEIVER_PHONE}</code>\n\n"
            f"💵 السعر: كل 1000 دينار = {ASIA_PRICE_PER_1000:.2f}$\n"
            "أرسل المبلغ بالدينار مثلاً 1000 👇\n\n"
            "/cancel للإلغاء ❌️.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("إلغاء ❌️", callback_data="asia_cancel", style="danger")]]))
        return ASIA_AMOUNT

    except asyncio.TimeoutError:
        await msg.edit_text("❌ انتهى الوقت، ما استجاب السيرفر.")
        asia_sessions.pop(uid, None)
        return ConversationHandler.END
    except Exception as e:
        log.exception("asia login")
        await msg.edit_text(f"❌ <code>{str(e)[:300]}</code>", parse_mode="HTML")
        asia_sessions.pop(uid, None)
        return ConversationHandler.END

async def asia_receive_amount(update, ctx):
    uid = update.effective_user.id
    text = (update.message.text or "").strip().replace(",", "")
    if not text.isdigit():
        await update.message.reply_text("❌ أرسل رقم صحيح (مثال: 1000):")
        return ASIA_AMOUNT
    amount = int(text)
    if amount < 1000:
        await update.message.reply_text("❌ الحد الأدنى 1000 دينار:")
        return ASIA_AMOUNT

    if uid not in asia_sessions:
        await update.message.reply_text("❌ انتهت الجلسة.")
        return ConversationHandler.END

    info = asia_sessions[uid]
    client = info["client"]

    cost_usd = round((amount / 1000.0) * ASIA_PRICE_PER_1000, 2)
    user_bal = get_balance(uid)
    if user_bal < cost_usd:
        await update.message.reply_text(
            f"❌ <b>رصيدك غير كافي</b>\n\n"
            f"💵 المطلوب: <b>{cost_usd:.2f}$</b>\n"
            f"💰 رصيدك: <b>{user_bal:.2f}$</b>\n"
            f"📱 مقابل: {amount:,} دينار\n\n"
            f"عبّي رصيدك أول من زر (شحن الرصيد 💳)",
            parse_mode="HTML")
        asia_sessions.pop(uid, None)
        return ConversationHandler.END

    msg = await update.message.reply_text(
        f"⏳ جاري بدء التحويل...\n\n"
        f"📤 المبلغ: <b>{amount:,} دينار</b>\n"
        f"💵 التكلفة: <b>{cost_usd:.2f}$</b>",
        parse_mode="HTML")

    try:
        loop = asyncio.get_running_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: client.transfer_initiate(phone_number=RECEIVER_PHONE, amount=amount)),
            timeout=60)
        log.info(f"asia transfer_initiate: {result}")
    except asyncio.TimeoutError:
        await msg.edit_text("❌ السيرفر ما استجاب خلال 60 ثانية. جرب مرة ثانية.")
        asia_sessions.pop(uid, None)
        return ConversationHandler.END
    except Exception as e:
        log.exception("asia transfer_initiate")
        await msg.edit_text(f"❌ خطأ: <code>{str(e)[:200]}</code>", parse_mode="HTML")
        asia_sessions.pop(uid, None)
        return ConversationHandler.END

    if isinstance(result, dict):
        blob = str(result)
        nx = result.get("nextAction") or ""
        try:
            import urllib.parse as _up
            decoded = _up.unquote(nx)
        except Exception:
            decoded = nx
        if ("رصيد" in blob) or ("رصيد" in nx) or ("رصيد" in decoded) or ("balance" in blob.lower()):
            bal_line = ""
            m = re.search(r"رصيدك\s*الحالي\s*([\d,\.]+)\s*IQD", decoded)
            if m:
                bal_line = f"\n\n💵 رصيد رقم آسيا: <b>{m.group(1)} دينار</b>"
            await msg.edit_text(
                f"❌ <b>رصيد رقم آسيا غير كافٍ</b>{bal_line}",
                parse_mode="HTML")
            asia_sessions.pop(uid, None)
            return ConversationHandler.END

    if not isinstance(result, dict) or not result.get("success"):
        await msg.edit_text(
            f"❌ فشل بدء التحويل\n<code>{str(result)[:300]}</code>",
            parse_mode="HTML")
        asia_sessions.pop(uid, None)
        return ConversationHandler.END

    pid = result.get("pid") or result.get("PID")
    if not pid:
        await msg.edit_text(
            f"⚠️ ما وصل PID\n<code>{str(result)[:300]}</code>",
            parse_mode="HTML")
        asia_sessions.pop(uid, None)
        return ConversationHandler.END

    c = db()
    c.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (cost_usd, uid))
    c.commit()
    new_bal = c.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()["balance"]
    c.close()

    info["pid"] = pid
    info["amount"] = amount
    info["cost_usd"] = cost_usd

    await msg.edit_text(
        f"📩 <b>وصلك كود تأكيد التحويل من آسيا سيل؟</b>\n\n"
        f"📤 إلى: <code>{RECEIVER_PHONE}</code>\n"
        f"💵 المبلغ: <b>{amount:,} دينار</b>\n"
        f"💰 خُصم من رصيدك: <b>{cost_usd:.2f}$</b>\n"
        f"💳 رصيدك الآن: <b>{new_bal:.2f}$</b>\n\n"
        "أرسل كود التأكيد 👇\n\n"
        "/cancel للإلغاء ❌️.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("إلغاء ❌️", callback_data="asia_cancel", style="danger")]]))
    return ASIA_CONFIRM

async def asia_receive_confirm(update, ctx):
    uid = update.effective_user.id
    code = (update.message.text or "").strip().replace(" ", "").replace("-", "")
    if not code.isdigit() or len(code) < 3:
        await update.message.reply_text("❌ كود غير صحيح. أعد الإرسال:")
        return ASIA_CONFIRM

    if uid not in asia_sessions or "pid" not in asia_sessions[uid]:
        await update.message.reply_text("❌ لا يوجد تحويل معلّق.")
        return ConversationHandler.END

    info = asia_sessions[uid]
    client = info["client"]
    pid = info["pid"]
    amount = info.get("amount", 0)
    cost_usd = info.get("cost_usd", 0)

    msg = await update.message.reply_text("⏳ جاري تأكيد التحويل...")

    try:
        loop = asyncio.get_running_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: client.transfer_confirm(pid=pid, passcode=code)),
            timeout=60)
        log.info(f"asia transfer_confirm: {result}")

        ok = isinstance(result, dict) and result.get("success")
        if ok:
            c = db()
            c.execute("INSERT INTO asia_topups(user_id, amount_iqd, amount_usd, receiver_phone, status, created_at, completed_at) "
                      "VALUES(?,?,?,?,?,?,?)",
                      (uid, amount, cost_usd, RECEIVER_PHONE, "completed",
                       datetime.now().isoformat(), datetime.now().isoformat()))
            c.commit(); c.close()
            await msg.edit_text(
                f"✅ <b>تم التحويل بنجاح!</b>\n\n"
                f"📤 إلى: <code>{RECEIVER_PHONE}</code>\n"
                f"💵 المبلغ: <b>{amount:,} دينار</b>\n"
                f"💰 التكلفة: <b>{cost_usd:.2f}$</b>",
                parse_mode="HTML")
        else:
            if cost_usd > 0:
                c = db()
                c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (cost_usd, uid))
                c.commit(); c.close()
                refund_note = f"\n\n💵 تم إرجاع <b>{cost_usd:.2f}$</b> لرصيدك"
            else:
                refund_note = ""
            await msg.edit_text(
                f"❌ فشل التأكيد{refund_note}\n<code>{str(result)[:300]}</code>",
                parse_mode="HTML")
    except asyncio.TimeoutError:
        if cost_usd > 0:
            c = db()
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (cost_usd, uid))
            c.commit(); c.close()
        await msg.edit_text(
            f"❌ انتهى الوقت\n\n💵 تم إرجاع <b>{cost_usd:.2f}$</b> لرصيدك",
            parse_mode="HTML")
    except Exception as e:
        log.exception("asia transfer_confirm")
        if cost_usd > 0:
            try:
                c = db()
                c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (cost_usd, uid))
                c.commit(); c.close()
            except Exception: pass
        await msg.edit_text(
            f"❌ خطأ: <code>{str(e)[:200]}</code>\n\n"
            f"💵 تم إرجاع <b>{cost_usd:.2f}$</b> لرصيدك",
            parse_mode="HTML")
    finally:
        s = asia_sessions.pop(uid, None)
        if s and s.get("capture"):
            s["capture"].provide("")

    return ConversationHandler.END

async def asia_cancel(update, ctx):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    info = asia_sessions.pop(uid, None)
    if info:
        try:
            if info.get("client"):
                await info["client"].disconnect()
        except Exception:
            pass
        if info.get("capture"):
            info["capture"].provide("")
    await send(update, "❌ تم إلغاء عملية الشحن.", back_home())
    return ConversationHandler.END
# ================== لوحة الأدمن ==================
async def cb_admin_open(update, ctx):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("غير مصرح", show_alert=True)
        return ConversationHandler.END
    await q.answer()
    await send(update, "لوحة الأدمن ⚙️", admin_kb())
    return A_MENU

async def cb_admin_back(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    await send(update, "لوحة الأدمن ⚙️", admin_kb())
    return A_MENU

async def cb_toggle_maintenance(update, ctx):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("غير مصرح", show_alert=True)
        return ConversationHandler.END
    current = is_maintenance()
    set_setting("maintenance", "0" if current else "1")
    if current:
        await q.answer("تم تشغيل البوت 🟢", show_alert=True)
    else:
        await q.answer("تم إطفاء البوت 🔴", show_alert=True)
    await send(update, "لوحة الأدمن ⚙️", admin_kb())
    return A_MENU

async def admin_cancel(update, ctx):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    try: await SESSION_MGR.cleanup(uid)
    except Exception: pass
    _as = asia_sessions.pop(uid, None)
    if _as:
        try:
            if _as.get("client"):
                await _as["client"].disconnect()
        except Exception: pass
        if _as.get("capture"):
            _as["capture"].provide("")
    ctx.user_data.clear()
    await send(update, "تم الإلغاء ❌️.", admin_kb())
    return A_MENU

# ================== الإحصائيات ==================
async def cb_stats(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return
    c = db()
    users = c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
    banned = c.execute("SELECT COUNT(*) n FROM users WHERE is_banned=1").fetchone()["n"]
    nodes = c.execute("SELECT COUNT(*) n FROM menu_nodes").fetchone()["n"]
    cats = c.execute("SELECT COUNT(*) n FROM menu_nodes WHERE node_type='category'").fetchone()["n"]
    total = c.execute("SELECT COUNT(*) n FROM numbers").fetchone()["n"]
    avail = c.execute("SELECT COUNT(*) n FROM numbers WHERE status='available'").fetchone()["n"]
    sold = c.execute("SELECT COUNT(*) n FROM numbers WHERE status='sold'").fetchone()["n"]
    rev = c.execute("SELECT COALESCE(SUM(price),0) s FROM purchases").fetchone()["s"]
    sess = c.execute("SELECT COUNT(*) n FROM sessions WHERE status='active'").fetchone()["n"]
    sess_total = c.execute("SELECT COUNT(*) n FROM sessions").fetchone()["n"]
    otps = c.execute("SELECT COUNT(*) n FROM otp_logs").fetchone()["n"]
    gifts = c.execute("SELECT COUNT(*) n FROM gift_logs").fetchone()["n"]
    refs = c.execute("SELECT COUNT(*) n FROM referrals").fetchone()["n"]
    codes = c.execute("SELECT COUNT(*) n FROM redeem_codes WHERE is_active=1").fetchone()["n"]
    comps = c.execute("SELECT COUNT(*) n FROM complaints WHERE status='pending'").fetchone()["n"]
    asia_cnt = c.execute("SELECT COUNT(*) n FROM asia_topups WHERE status='completed'").fetchone()["n"]
    asia_sum = c.execute("SELECT COALESCE(SUM(amount_usd),0) s FROM asia_topups WHERE status='completed'").fetchone()["s"]
    asia_iqd = c.execute("SELECT COALESCE(SUM(amount_iqd),0) s FROM asia_topups WHERE status='completed'").fetchone()["s"]
    c.close()
    await send(update,
        f"📊 إحصائيات البوت\n\n"
        f"👥 المستخدمين: {users} (محظور: {banned})\n"
        f"🌳 عناصر المتجر: {nodes} (أقسام: {cats})\n"
        f"📱 الأرقام: {total} (متوفر: {avail} | مباع: {sold})\n"
        f"💰 الربح: {rev:.2f}$\n\n"
        f"🔋 شحن آسيا: {asia_cnt} عملية | {asia_iqd:,} دينار | {asia_sum:.2f}$\n\n"
        f"🔑 الجلسات: {sess}/{sess_total}\n"
        f"🔐 OTP: {otps}\n"
        f"🎁 الهدايا: {gifts}\n"
        f"🎯 الإحالات: {refs}\n"
        f"🎟 الأكواد: {codes}\n"
        f"📩 شكاوى معلقة: {comps}",
        back_admin())
    return A_MENU

# ================== المستخدمين ==================
async def cb_users(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return
    c = db()
    rows = c.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT 30").fetchall()
    total = c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
    c.close()
    if not rows:
        await send(update, "لا يوجد مستخدمين.", back_admin())
        return A_MENU
    lines = [f"👥 آخر 30 مستخدم (المجموع: {total})\n"]
    for r in rows:
        un = f"@{r['username']}" if r['username'] else "—"
        ban = "🔴" if r["is_banned"] else "🟢"
        lines.append(f"{ban} | <code>{r['user_id']}</code> | {html.escape(r['first_name'] or '')} | {un} | {r['balance']:.2f}$")
    await send(update, "\n".join(lines),
        [[InlineKeyboardButton("حظر/فك 🟢🔴", callback_data="A_banuser", style="danger")],
         [mk_btn("admin_back")]])
    return A_MENU

async def cb_banuser_start(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    ctx.user_data["ban_mode"] = True
    await send(update,
        "🚫 حظر/فك حظر\n\nأرسل ايدي المستخدم:\n\n/cancel للإلغاء ❌️.",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return A_USERS_VIEW

async def cb_banuser_do(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    try:
        uid = int(update.message.text.strip())
    except Exception:
        await update.message.reply_text("ايدي غير صحيح. جرب مرة ثانية:")
        return A_USERS_VIEW
    c = db()
    r = c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
    if not r:
        c.close()
        await update.message.reply_text("المستخدم غير موجود.",
            reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    new_state = 0 if r["is_banned"] else 1
    c.execute("UPDATE users SET is_banned=? WHERE user_id=?", (new_state, uid))
    c.commit(); c.close()
    txt = "🔴 تم الحظر" if new_state else "🟢 تم فك الحظر"
    kb = [[InlineKeyboardButton("🔁 حظر/فك آخر", callback_data="A_banuser", style="danger")],
          [mk_btn("admin_back")]]
    await update.message.reply_text(f"{txt}\n\nالآيدي: <code>{uid}</code>",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
    return A_MENU

# ================== إنشاء أكواد ==================
async def createcode_start(update, ctx):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("غير مصرح", show_alert=True)
        return ConversationHandler.END
    await q.answer()
    await send(update,
        "إنشاء كود تعبئة 🎟\n\nالخطوة 1: أرسل الكود\n\nمثال: WELCOME10\n\n/cancel للإلغاء ❌️.",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return A_RC_CODE

async def createcode_code(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    code = update.message.text.strip().upper()
    if len(code) < 2 or len(code) > 30:
        await update.message.reply_text("الكود لازم 2-30 حرف:")
        return A_RC_CODE
    c = db()
    exists = c.execute("SELECT code FROM redeem_codes WHERE code=?", (code,)).fetchone()
    c.close()
    if exists:
        await update.message.reply_text("يوجد كود بنفس الاسم، جرب اسم ثاني:")
        return A_RC_CODE
    ctx.user_data["rc_code"] = code
    await update.message.reply_text(
        f"✅️ الكود: <code>{code}</code>\n\nالخطوة 2: أرسل قيمة الكود بالدولار\n\nمثال: 10",
        parse_mode="HTML")
    return A_RC_VALUE

async def createcode_value(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    try:
        value = float(update.message.text.strip())
        if value <= 0 or value > 10000: raise ValueError
    except Exception:
        await update.message.reply_text("رقم صحيح (0-10000):")
        return A_RC_VALUE
    ctx.user_data["rc_value"] = value
    await update.message.reply_text(
        f"💰 القيمة: {value}$\n\nالخطوة 3: كم شخص يمكنه استخدامه؟\n\nمثال: 1 أو 10",
        parse_mode="HTML")
    return A_RC_MAX

async def createcode_max(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    try:
        max_uses = int(update.message.text.strip())
        if max_uses < 1 or max_uses > 10000: raise ValueError
    except Exception:
        await update.message.reply_text("رقم صحيح (1-10000):")
        return A_RC_MAX
    code = ctx.user_data.pop("rc_code", None)
    value = ctx.user_data.pop("rc_value", 0)
    if not code or not value:
        await update.message.reply_text("انتهت الجلسة.",
            reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    c = db()
    c.execute("INSERT INTO redeem_codes(code, value, max_uses, uses, created_by, created_at, is_active) "
              "VALUES(?,?,?,0,?,?,1)",
              (code, value, max_uses, update.effective_user.id, datetime.now().isoformat()))
    c.commit(); c.close()
    await update.message.reply_text(
        f"✅️ تم إنشاء الكود!\n\n🎟 <code>{code}</code>\n💰 {value:.2f}$\n👥 {max_uses} شخص",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(back_admin()))
    return A_MENU

async def cb_listcodes(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return
    c = db()
    rows = c.execute("SELECT * FROM redeem_codes ORDER BY created_at DESC LIMIT 30").fetchall()
    c.close()
    if not rows:
        await send(update, "لا توجد أكواد", back_admin())
        return A_MENU
    lines = [f"🎟 الأكواد ({len(rows)})\n"]
    for r in rows:
        status = "🟢" if r["is_active"] and r["uses"] < r["max_uses"] else "🔴"
        lines.append(f"{status} | <code>{r['code']}</code> | {r['value']:.2f}$ | {r['uses']}/{r['max_uses']}")
    await send(update, "\n".join(lines),
        [[InlineKeyboardButton("🗑 حذف كود", callback_data="A_delcode", style="danger")],
         [mk_btn("admin_back")]])
    return A_MENU

async def cb_delcode_list(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    c = db()
    rows = c.execute("SELECT code FROM redeem_codes ORDER BY created_at DESC LIMIT 50").fetchall()
    c.close()
    if not rows:
        await send(update, "لا توجد أكواد.", back_admin())
        return A_MENU
    kb = []
    for r in rows:
        kb.append([InlineKeyboardButton(f"🗑 حذف {r['code']}", callback_data=f"delcode_{r['code']}", style="danger")])
    kb.append([InlineKeyboardButton("رجوع", callback_data="A_listcodes", style="primary")])
    await send(update, "اختر الكود للحذف:", kb)
    return A_MENU

async def cb_delcode_do(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    code = q.data.replace("delcode_", "", 1).strip()
    c = db()
    c.execute("DELETE FROM redeem_codes WHERE code=?", (code,))
    c.execute("DELETE FROM redeem_uses WHERE code=?", (code,))
    c.commit(); c.close()
    await q.answer(f"تم حذف {code}", show_alert=True)
    await cb_listcodes(update, ctx)
    return A_MENU

# ================== إضافة رصيد ==================
async def addbal_start(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    ctx.user_data["admin_mode"] = "bal"
    await send(update,
        "💴 إضافة رصيد\n\nأرسل ايدي المستخدم:\n\n/cancel للإلغاء ❌️.",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return A_BAL_ID

async def addbal_id(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    try:
        uid = int(update.message.text.strip())
    except Exception:
        await update.message.reply_text("ايدي غير صحيح:")
        return A_BAL_ID
    ctx.user_data["bal_uid"] = uid
    await update.message.reply_text("💰 أرسل المبلغ بالدولار:")
    return A_BAL_AMT

async def addbal_amt(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    try:
        amt = float(update.message.text.strip())
    except Exception:
        await update.message.reply_text("رقم صحيح:")
        return A_BAL_AMT
    uid = ctx.user_data.pop("bal_uid", None)
    c = db()
    r = c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
    if not r:
        c.close()
        await update.message.reply_text("المستخدم غير موجود.", reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, uid))
    c.commit()
    nb = c.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()["balance"]
    c.close()
    await update.message.reply_text(f"✅️ تم إضافة {amt:.2f}$\nرصيده الجديد: {nb:.2f}$",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(back_admin()))
    try: await ctx.bot.send_message(uid, f"💵 تم إضافة {amt:.2f}$\nرصيدك الجديد: {nb:.2f}$")
    except Exception: pass
    return A_MENU

# ================== إضافة نقاط ==================
async def addpoints_start(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    ctx.user_data["admin_mode"] = "points"
    await send(update,
        "🎁 إضافة نقاط\n\nأرسل ايدي المستخدم:\n\n/cancel للإلغاء ❌️.",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return A_BAL_ID

async def addpoints_id(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    try:
        uid = int(update.message.text.strip())
    except Exception:
        await update.message.reply_text("ايدي غير صحيح:")
        return A_BAL_ID
    c = db()
    r = c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
    if not r:
        c.close()
        await update.message.reply_text("غير موجود.", reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    c.execute("UPDATE users SET points = points + 1, balance = balance + ? WHERE user_id=?",
              (REFERRAL_REWARD, uid))
    c.commit()
    pts = c.execute("SELECT points FROM users WHERE user_id=?", (uid,)).fetchone()["points"]
    c.close()
    await update.message.reply_text(f"✅️ تم إضافة 1 نقطة\nنقاطه: {pts}",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(back_admin()))
    return A_MENU

# ================== البث ==================
async def broadcast_start(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    ctx.user_data["broadcast_mode"] = True
    await send(update,
        "🔔 بث رسالة\n\nأرسل الرسالة:\n\n/cancel للإلغاء ❌️.",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return A_USERS_VIEW

async def broadcast_do(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    msg = update.message
    c = db()
    users = c.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()
    c.close()
    sent = 0; failed = 0
    status = await msg.reply_text(f"📤 جاري الإرسال لـ {len(users)} مستخدم...")
    for i, u in enumerate(users):
        try:
            await msg.copy(chat_id=u["user_id"])
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
        if (i + 1) % 50 == 0:
            try: await status.edit_text(f"📤 نجح: {sent} | فشل: {failed}")
            except Exception: pass
    await status.edit_text(
        f"✅️ اكتمل البث\n\n✅️ نجح: {sent}\n❌️ فشل: {failed}",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(back_admin()))
    return A_MENU

# ================== إضافة قسم سريع ==================
async def addcat_start(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    await send(update,
        "➕️ إضافة قسم سريع\n\nأرسل اسم القسم:\n\n/cancel للإلغاء ❌️.",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return A_CAT_NAME

async def addcat_name(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    name = update.message.text.strip()
    if len(name) < 1 or len(name) > 60:
        await update.message.reply_text("الاسم 1-60 حرف:")
        return A_CAT_NAME
    ctx.user_data["cat_name"] = name
    await update.message.reply_text("💰 أرسل السعر بالدولار:")
    return A_CAT_PRICE

async def addcat_price(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    try:
        price = float(update.message.text.strip())
        if price < 0 or price > 100000: raise ValueError
    except Exception:
        await update.message.reply_text("رقم صحيح:")
        return A_CAT_PRICE
    name = ctx.user_data.pop("cat_name", "قسم")
    c = db()
    try:
        c.execute("INSERT INTO menu_nodes(parent_id, title, emoji, color_style, node_type, price, position, is_active, created_at) "
                  "VALUES(NULL,?,?,?,?,?,?,1,?)",
                  (name, "", "primary", "category", price, 0, datetime.now().isoformat()))
        c.commit()
        await update.message.reply_text(f"✅️ تم إنشاء القسم:\n\n📦 {html.escape(name)}\n💰 {price:.2f}$",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(back_admin()))
    except Exception as e:
        log.error(f"addcat_price: {e}")
        await update.message.reply_text(f"فشل: {str(e)[:150]}",
            reply_markup=InlineKeyboardMarkup(back_admin()))
    finally:
        c.close()
    return A_MENU

# ================== إضافة أرقام لقسم ==================
async def addnums_start(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    c = db()
    cats = c.execute("SELECT * FROM menu_nodes WHERE node_type='category' ORDER BY id").fetchall()
    c.close()
    if not cats:
        await send(update, "لا توجد أقسام.",
            [[InlineKeyboardButton("➕️ إضافة قسم", callback_data="A_addcat", style="success")],
             [InlineKeyboardButton("🛒 إدارة المتجر", callback_data="MT_root", style="success")],
             [mk_btn("admin_back")]])
        return A_MENU
    kb = []
    for c_ in cats:
        e = c_["emoji"] or ""
        kb.append([InlineKeyboardButton(f"{e} {c_['title']} | {c_['price']:.2f}$",
            callback_data=f"nums_{c_['id']}", style="primary")])
    kb.append([mk_btn("admin_back")])
    await send(update, "📥 اختر القسم:", kb)
    return A_NUMS_PICK

async def addnums_pick(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    try: cid = int(q.data.split("_")[1])
    except Exception: return ConversationHandler.END
    ctx.user_data["nums_cat"] = cid
    c = db()
    cat = c.execute("SELECT * FROM menu_nodes WHERE id=?", (cid,)).fetchone()
    c.close()
    if not cat:
        await send(update, "القسم غير موجود.", back_admin())
        return A_MENU
    await send(update,
        f"📥 إضافة أرقام\n\n📦 {html.escape(cat['title'])}\n\n"
        f"الصيغة (كل رقم بسطر):\n<code>الرقم,الباسوورد</code>\n\n"
        f"مثال:\n<code>+9647700000001,MyPass123</code>\n<code>+9647700000002,</code>\n\n"
        f"/cancel للإلغاء ❌️.",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return A_NUMS_TEXT

async def addnums_save(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    cid = ctx.user_data.pop("nums_cat", None)
    if not cid:
        await update.message.reply_text("انتهت الجلسة.",
            reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    added = 0; errors = 0
    c = db()
    now = datetime.now().isoformat()
    for line in update.message.text.strip().splitlines():
        line = line.strip()
        if not line: continue
        parts = line.split(",")
        phone = parts[0].strip() if len(parts) > 0 else ""
        password = parts[1].strip() if len(parts) > 1 else ""
        if not phone: continue
        if not phone.startswith("+"):
            phone = "+" + normalize_phone(phone)
        try:
            c.execute("INSERT INTO numbers(category_id, phone, code, password, added_at) VALUES(?,?,?,?,?)",
                      (cid, phone, "", password, now))
            added += 1
        except Exception:
            errors += 1
    c.commit(); c.close()
    txt = f"✅️ تم إضافة {added} رقم."
    if errors: txt += f"\n⚠️ فشل: {errors}"
    await update.message.reply_text(txt, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(back_admin()))
    return A_MENU

# ================== عرض أرقام قسم ==================
async def viewnums_start(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    c = db()
    cats = c.execute("SELECT * FROM menu_nodes WHERE node_type='category' ORDER BY id").fetchall()
    c.close()
    if not cats:
        await send(update, "لا توجد أقسام.", back_admin())
        return A_MENU
    kb = []
    for c_ in cats:
        e = c_["emoji"] or ""
        kb.append([InlineKeyboardButton(f"{e} {c_['title']}",
            callback_data=f"viewn_{c_['id']}", style="primary")])
    kb.append([mk_btn("admin_back")])
    await send(update, "📝 اختر القسم:", kb)
    return A_VIEW_NUMS_PICK

async def viewnums_pick(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    try: cid = int(q.data.split("_")[1])
    except Exception: return ConversationHandler.END
    c = db()
    cat = c.execute("SELECT * FROM menu_nodes WHERE id=?", (cid,)).fetchone()
    rows = c.execute("SELECT * FROM numbers WHERE category_id=? AND status='available' ORDER BY id LIMIT 50",
                     (cid,)).fetchall()
    total = c.execute("SELECT COUNT(*) n FROM numbers WHERE category_id=? AND status='available'",
                      (cid,)).fetchone()["n"]
    c.close()
    if not cat:
        await send(update, "القسم غير موجود.", back_admin())
        return A_MENU
    if not rows:
        await send(update, f"📦 {html.escape(cat['title'])}\n\nلا توجد أرقام.", back_admin())
        return A_MENU
    lines = [f"📦 {html.escape(cat['title'])} ({total} رقم)\n"]
    for r in rows:
        pwd = f" | 🔐 {r['password']}" if r['password'] else ""
        lines.append(f"{flag_for(r['phone'])} <code>{r['phone']}</code>{pwd}")
    if total > 50: lines.append(f"\n... و {total-50} آخر")
    await send(update, "\n".join(lines), back_admin())
    return A_MENU

# ================== تعديل سعر ==================
async def editprice_start(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    c = db()
    cats = c.execute("SELECT * FROM menu_nodes WHERE node_type='category' ORDER BY id").fetchall()
    c.close()
    if not cats:
        await send(update, "لا توجد أقسام.", back_admin())
        return A_MENU
    kb = []
    for c_ in cats:
        e = c_["emoji"] or ""
        kb.append([InlineKeyboardButton(f"{e} {c_['title']} | {c_['price']:.2f}$",
            callback_data=f"editp_{c_['id']}", style="primary")])
    kb.append([mk_btn("admin_back")])
    await send(update, "💰 اختر القسم:", kb)
    return A_EDITPICK

async def editprice_pick(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    try: cid = int(q.data.split("_")[1])
    except Exception: return ConversationHandler.END
    ctx.user_data["editp_cat"] = cid
    c = db()
    cat = c.execute("SELECT * FROM menu_nodes WHERE id=?", (cid,)).fetchone()
    c.close()
    if not cat:
        await send(update, "غير موجود.", back_admin())
        return A_MENU
    await send(update,
        f"💰 تعديل السعر\n\n📦 {html.escape(cat['title'])}\n💵 الحالي: {cat['price']:.2f}$\n\nأرسل السعر الجديد:",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return A_EDITPRICE

async def editprice_save(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    cid = ctx.user_data.pop("editp_cat", None)
    try:
        np = float(update.message.text.strip())
        if np < 0 or np > 100000: raise ValueError
    except Exception:
        await update.message.reply_text("رقم صحيح:")
        return A_EDITPRICE
    if not cid:
        await update.message.reply_text("انتهت الجلسة.",
            reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    c = db()
    c.execute("UPDATE menu_nodes SET price=? WHERE id=?", (np, cid))
    c.commit(); c.close()
    await update.message.reply_text(f"✅️ تم التحديث إلى {np:.2f}$",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(back_admin()))
    return A_MENU

# ================== تعديل اسم ==================
async def editcatname_start(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    c = db()
    cats = c.execute("SELECT * FROM menu_nodes ORDER BY id LIMIT 50").fetchall()
    c.close()
    if not cats:
        await send(update, "لا توجد عناصر.", back_admin())
        return A_MENU
    kb = []
    for c_ in cats:
        e = c_["emoji"] or ""
        kb.append([InlineKeyboardButton(f"{e} {c_['title']}",
            callback_data=f"editcn_{c_['id']}", style="primary")])
    kb.append([mk_btn("admin_back")])
    await send(update, "✏️ اختر العنصر:", kb)
    return A_EDITCAT_PICK

async def editcatname_pick(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    try: cid = int(q.data.split("_")[1])
    except Exception: return ConversationHandler.END
    ctx.user_data["editcn_cat"] = cid
    c = db()
    cat = c.execute("SELECT * FROM menu_nodes WHERE id=?", (cid,)).fetchone()
    c.close()
    if not cat:
        await send(update, "غير موجود.", back_admin())
        return A_MENU
    await send(update,
        f"✏️ تعديل الاسم\n\nالحالي: {html.escape(cat['title'])}\n\nأرسل الاسم الجديد:",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return A_EDITCAT_NAME

async def editcatname_save(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    cid = ctx.user_data.pop("editcn_cat", None)
    if not cid:
        await update.message.reply_text("انتهت الجلسة.",
            reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    new_name = update.message.text.strip()
    if len(new_name) < 1 or len(new_name) > 60:
        await update.message.reply_text("الاسم 1-60 حرف:")
        return A_EDITCAT_NAME
    c = db()
    try:
        old = c.execute("SELECT title FROM menu_nodes WHERE id=?", (cid,)).fetchone()
        if not old:
            c.close()
            await update.message.reply_text("غير موجود.",
                reply_markup=InlineKeyboardMarkup(back_admin()))
            return A_MENU
        old_name = old["title"]
        c.execute("UPDATE menu_nodes SET title=? WHERE id=?", (new_name, cid))
        c.commit(); c.close()
        await update.message.reply_text(
            f"✅️ تم التعديل\n\nالقديم: {html.escape(old_name)}\nالجديد: {html.escape(new_name)}",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(back_admin()))
    except Exception as e:
        c.close()
        log.error(f"editcatname_save: {e}")
        await update.message.reply_text(f"فشل: {str(e)[:150]}",
            reply_markup=InlineKeyboardMarkup(back_admin()))
    return A_MENU

# ================== حذف قسم ==================
async def delcat_start(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    c = db()
    cats = c.execute("SELECT * FROM menu_nodes WHERE node_type='category' ORDER BY id").fetchall()
    c.close()
    if not cats:
        await send(update, "لا توجد أقسام.", back_admin())
        return A_MENU
    kb = []
    for c_ in cats:
        e = c_["emoji"] or ""
        kb.append([InlineKeyboardButton(f"🗑 {e} {c_['title']}",
            callback_data=f"delc_{c_['id']}", style="danger")])
    kb.append([mk_btn("admin_back")])
    await send(update, "🗑 اختر القسم:\n\n⚠️ سيُحذف نهائياً.", kb)
    return A_DELPICK

async def delcat_do(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    try: cid = int(q.data.split("_")[1])
    except Exception: return ConversationHandler.END
    c = db()
    c.execute("DELETE FROM numbers WHERE category_id=?", (cid,))
    c.execute("DELETE FROM menu_nodes WHERE id=?", (cid,))
    c.commit(); c.close()
    await q.answer("تم الحذف ✅️", show_alert=True)
    await send(update, "لوحة الأدمن ⚙️", admin_kb())
    return A_MENU

# ================== حذف رقم ==================
async def delnum_start(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    c = db()
    cats = c.execute("SELECT * FROM menu_nodes WHERE node_type='category' ORDER BY id").fetchall()
    c.close()
    if not cats:
        await send(update, "لا توجد أقسام.", back_admin())
        return A_MENU
    kb = []
    for c_ in cats:
        e = c_["emoji"] or ""
        kb.append([InlineKeyboardButton(f"{e} {c_['title']}",
            callback_data=f"dnumcat_{c_['id']}", style="primary")])
    kb.append([mk_btn("admin_back")])
    await send(update, "🗑 اختر القسم:", kb)
    return A_DELNUM_PICK

async def delnum_cat_pick(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    try: cid = int(q.data.split("_")[1])
    except Exception: return ConversationHandler.END
    c = db()
    cat = c.execute("SELECT * FROM menu_nodes WHERE id=?", (cid,)).fetchone()
    if not cat:
        c.close()
        await send(update, "غير موجود.", back_admin())
        return A_MENU
    nums = c.execute("SELECT * FROM numbers WHERE category_id=? AND status='available' ORDER BY id LIMIT 30",
        (cid,)).fetchall()
    total = c.execute("SELECT COUNT(*) n FROM numbers WHERE category_id=? AND status='available'",
        (cid,)).fetchone()["n"]
    c.close()
    if not nums:
        await send(update, f"📦 {html.escape(cat['title'])}\n\nلا توجد أرقام.", back_admin())
        return A_MENU
    kb = []
    for n in nums:
        kb.append([InlineKeyboardButton(f"🗑 {n['phone']}",
            callback_data=f"dnum_{n['id']}", style="danger")])
    kb.append([mk_btn("admin_back")])
    await send(update,
        f"🗑 اختر رقم للحذف\n\n📦 {html.escape(cat['title'])}\n📊 المتوفر: {total}",
        kb)
    return A_DELNUM_SELECT

async def delnum_do(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    try: nid = int(q.data.split("_")[1])
    except Exception: return ConversationHandler.END
    c = db()
    num = c.execute("SELECT * FROM numbers WHERE id=?", (nid,)).fetchone()
    if not num:
        c.close(); await q.answer("غير موجود", show_alert=True); return A_MENU
    phone = num["phone"]; cat_id = num["category_id"]
    c.execute("DELETE FROM numbers WHERE id=?", (nid,))
    c.commit(); c.close()
    await q.answer(f"تم حذف {phone}", show_alert=True)
    c = db()
    cat = c.execute("SELECT * FROM menu_nodes WHERE id=?", (cat_id,)).fetchone()
    nums = c.execute("SELECT * FROM numbers WHERE category_id=? AND status='available' ORDER BY id LIMIT 30",
        (cat_id,)).fetchall()
    total = c.execute("SELECT COUNT(*) n FROM numbers WHERE category_id=? AND status='available'",
        (cat_id,)).fetchone()["n"]
    c.close()
    if not nums or not cat:
        await send(update, "لوحة الأدمن ⚙️", admin_kb())
        return A_MENU
    kb = []
    for n in nums:
        kb.append([InlineKeyboardButton(f"🗑 {n['phone']}",
            callback_data=f"dnum_{n['id']}", style="danger")])
    kb.append([mk_btn("admin_back")])
    await send(update,
        f"✅️ تم حذف {phone}\n\n📦 {html.escape(cat['title'])}\n📊 المتوفر الآن: {total}",
        kb)
    return A_DELNUM_SELECT
# ================== جلسات OTP ==================
async def sess_menu(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    c = db()
    rows = c.execute("SELECT * FROM sessions ORDER BY added_at DESC").fetchall()
    c.close()
    kb = [[InlineKeyboardButton("➕️ إضافة جلسة", callback_data="A_sess_add", style="primary")]]
    if rows:
        kb.append([InlineKeyboardButton("🗑 حذف جلسة", callback_data="A_sess_del", style="danger")])
        kb.append([InlineKeyboardButton("🔍 فحص جلسة", callback_data="A_sess_test", style="primary")])
        kb.append([InlineKeyboardButton("🗑 حذف الكل", callback_data="A_sess_delall", style="danger")])
    kb.append([mk_btn("admin_back")])
    if not rows:
        text = "🔑 جلسات OTP\n\nلا توجد جلسات."
    else:
        lines = [f"🔑 جلسات OTP ({len(rows)})\n"]
        for r in rows[:30]:
            icon = "🟢" if r["status"] == "active" else "🔴"
            lines.append(f"{icon} {flag_for(r['phone'])} <code>{r['phone']}</code>")
        if len(rows) > 30: lines.append(f"\n... و {len(rows)-30}")
        text = "\n".join(lines)
    await send(update, text, kb)
    return A_MENU

async def sess_add_start(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    uid = q.from_user.id
    if not check_daily_limit(uid):
        await send(update, f"وصلت الحد ({MAX_SESSIONS_ADDED_PER_DAY}).", back_sessions())
        return A_MENU
    elapsed = time.time() - _last_session_time.get(uid, 0)
    if elapsed < SESSION_CREATION_COOLDOWN:
        wait = int(SESSION_CREATION_COOLDOWN - elapsed)
        await send(update, f"⏳ انتظر {wait} ثانية.", back_sessions())
        return A_MENU
    await send(update,
        "🔑 إضافة جلسة OTP\n\nأرسل الرقم:\n<code>+9647700000000</code>\n\n/cancel للإلغاء ❌️.",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return S_PHONE

async def sess_phone(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    phone_raw = update.message.text.strip()
    if not phone_raw.startswith("+"): phone_raw = "+" + normalize_phone(phone_raw)
    if len(phone_raw) < 8:
        await update.message.reply_text("رقم غير صحيح:")
        return S_PHONE
    uid = update.effective_user.id
    flag, country_name, iso = detect_country(phone_raw)
    status_msg = await update.message.reply_text(
        f"📤 جاري إرسال الكود...\n\n{flag} {country_name}\n<code>{phone_raw}</code>",
        parse_mode="HTML")
    try:
        client, sent, method_used, backend, error_msg, device_info = await send_code_telethon(phone_raw)
    except Exception as e:
        log.error(f"send_code error: {e}")
        client, sent, method_used, backend, error_msg, device_info = None, None, None, None, str(e), None
    if client and sent:
        method_display = (method_used or "Telethon") + format_code_method(sent)
        await SESSION_MGR.set(uid, {
            "client": client, "backend": backend, "phone": phone_raw,
            "hash": getattr(sent, "phone_code_hash", None),
            "attempts": 0, "resend_count": 0,
            "iso": iso, "flag": flag, "country": country_name,
            "device_model": device_info["device_model"],
            "system_version": device_info["system_version"],
            "app_version": device_info["app_version"]})
        c = db()
        c.execute("INSERT INTO session_attempts(user_id, phone, method, result, created_at) VALUES(?,?,?,?,?)",
                  (uid, phone_raw, method_used, "sent", datetime.now().isoformat()))
        c.commit(); c.close()
        _last_session_time[uid] = time.time()
        inc_daily_limit(uid)
        kb = [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]]
        await status_msg.edit_text(
            f"✅️ تم إرسال الكود!\n\n{flag} {country_name}\n<code>{phone_raw}</code>\n📨 {method_display}\n\n📝 أدخل الكود:",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
        return S_CODE
    err_low = (error_msg or "").lower()
    if "flood" in err_low:
        hint = "⚠️ Flood - انتظر ساعة."
    elif "banned" in err_low:
        hint = "🔴 الرقم محظور."
    else:
        hint = "❌️ فشل إرسال الكود.\n\nجرب:\n- تأكد أنه عنده حساب تلغرام\n- جرب رقم آخر"
    if client:
        try: await client.disconnect()
        except Exception: pass
    await status_msg.edit_text(hint, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔃 إعادة", callback_data="A_sess_add", style="success")],
            [mk_btn("sessions_back")]]))
    return A_MENU

async def sess_code(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    code = update.message.text.strip().replace(" ", "").replace("-", "")
    if not code.isdigit() or len(code) < 3:
        await update.message.reply_text("كود غير صحيح:")
        return S_CODE
    uid = update.effective_user.id
    data = SESSION_MGR.get(uid)
    if not data:
        await update.message.reply_text("انتهت الجلسة.",
            reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    client = data["client"]
    phone = data["phone"]
    phone_hash = data["hash"]
    data["attempts"] = data.get("attempts", 0) + 1
    await SESSION_MGR.set(uid, data)
    if data["attempts"] > MAX_CODE_ATTEMPTS:
        await SESSION_MGR.cleanup(uid)
        await update.message.reply_text(f"❌️ تجاوزت الحد ({MAX_CODE_ATTEMPTS})",
            reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    try:
        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_hash)
        except SessionPasswordNeededError:
            await update.message.reply_text("🔐 الحساب عنده 2FA\n\nأرسل كلمة المرور:")
            return S_PASSWORD
        return await _save_session(update, ctx, client, phone, data)
    except PhoneCodeInvalidError:
        remaining = MAX_CODE_ATTEMPTS - data["attempts"]
        await update.message.reply_text(f"❌️ كود غلط. باقي {remaining}:")
        return S_CODE
    except PhoneCodeExpiredError:
        await SESSION_MGR.cleanup(uid)
        await update.message.reply_text("⌛ انتهت الصلاحية.",
            reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    except FloodWaitError as e:
        await update.message.reply_text(f"⏳ انتظر {e.seconds} ثانية:")
        return S_CODE
    except Exception as e:
        log.error(f"signin error: {e}")
        await update.message.reply_text(f"❌️ فشل: {str(e)[:200]}",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU

async def sess_password(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    password = update.message.text.strip()
    uid = update.effective_user.id
    data = SESSION_MGR.get(uid)
    if not data:
        await update.message.reply_text("انتهت الجلسة.",
            reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    client = data["client"]
    phone = data["phone"]
    try:
        await client.sign_in(password=password)
    except Exception as e:
        log.error(f"2FA: {e}")
        await update.message.reply_text(f"❌️ خطأ: {str(e)[:200]}\n\nجرب:")
        return S_PASSWORD
    return await _save_session(update, ctx, client, phone, data)

async def _save_session(update, ctx, client, phone, data):
    try:
        session_string = StringSession.save(client.session)
        await client.disconnect()
    except Exception as e:
        log.error(f"save session: {e}")
        await update.message.reply_text(f"❌️ فشل الحفظ: {e}",
            reply_markup=InlineKeyboardMarkup(back_admin()))
        SESSION_MGR.pop(update.effective_user.id)
        return A_MENU
    iso = data.get("iso", "")
    cname = data.get("country", "")
    flag = data.get("flag", "")
    c = db()
    c.execute("INSERT OR REPLACE INTO sessions(phone, session_string, country_code, "
        "country_name, flag, added_at, status, device_model, "
        "system_version, app_version, backend) VALUES(?,?,?,?,?,?,'active',?,?,?,'telethon')",
        (phone, session_string, iso, cname, flag, datetime.now().isoformat(),
         data.get("device_model"), data.get("system_version"), data.get("app_version")))
    c.commit(); c.close()
    SESSION_MGR.pop(update.effective_user.id)
    await update.message.reply_text(
        f"✅️ تم إضافة الجلسة!\n\n{flag} {cname}\n<code>{phone}</code>",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(back_admin()))
    return A_MENU

async def sess_del_list(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    c = db()
    rows = c.execute("SELECT * FROM sessions ORDER BY added_at DESC LIMIT 50").fetchall()
    c.close()
    if not rows:
        await send(update, "لا توجد جلسات.", back_admin())
        return A_MENU
    kb = []
    for r in rows:
        kb.append([InlineKeyboardButton(f"🗑 {r['phone']}",
            callback_data=f"sessdel_{r['phone']}", style="danger")])
    kb.append([mk_btn("sessions_back")])
    await send(update, f"🗑 اختر الجلسة ({len(rows)}):", kb)
    return A_MENU

async def sess_del_do(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    phone = q.data.replace("sessdel_", "", 1).strip()
    c = db()
    r = c.execute("SELECT phone FROM sessions WHERE phone=?", (phone,)).fetchone()
    if not r:
        c.close(); await q.answer("غير موجودة", show_alert=True); return A_MENU
    c.execute("DELETE FROM sessions WHERE phone=?", (phone,))
    c.commit(); c.close()
    await q.answer(f"تم حذف {phone}", show_alert=True)
    await sess_menu(update, ctx)
    return A_MENU

async def sess_del_all(update, ctx):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("غير مصرح", show_alert=True)
        return ConversationHandler.END
    c = db()
    n = c.execute("SELECT COUNT(*) n FROM sessions").fetchone()["n"]
    c.execute("DELETE FROM sessions")
    c.commit(); c.close()
    await q.answer(f"تم حذف {n} جلسة", show_alert=True)
    await sess_menu(update, ctx)
    return A_MENU

async def sess_test_start(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    await send(update,
        "🔍 فحص جلسة\n\nأرسل رقم الجلسة:\n\n/cancel للإلغاء ❌️.",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return S_RESEND_CHOICE

async def sess_test_do(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    phone = update.message.text.strip()
    c = db()
    sess = c.execute("SELECT * FROM sessions WHERE phone=?", (phone,)).fetchone()
    c.close()
    if not sess:
        await update.message.reply_text("غير موجودة.",
            reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    msg = await update.message.reply_text("🔍 جاري الفحص...")
    try:
        client = TelegramClient(StringSession(sess["session_string"]), TG_API_ID, TG_API_HASH)
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            await msg.edit_text(
                f"✅️ الجلسة شغالة\n\n📱 {phone}\n👤 {html.escape(me.first_name or '—')}\n💳 <code>{me.id}</code>",
                parse_mode="HTML", reply_markup=InlineKeyboardMarkup(back_admin()))
        else:
            await msg.edit_text("🔴 غير مصرح لها",
                reply_markup=InlineKeyboardMarkup(back_admin()))
        await client.disconnect()
    except Exception as e:
        log.error(f"sess_test: {e}")
        await msg.edit_text(f"❌️ فشل: {str(e)[:200]}",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(back_admin()))
    return A_MENU

# ================== إدارة الشجرة ==================
async def _mt_answer(q, text=None, alert=False):
    if q:
        try: await q.answer(text or "", show_alert=alert)
        except Exception: pass

async def _mt_show(update, ctx, text, kb=None):
    markup = InlineKeyboardMarkup(kb) if kb else None
    try:
        if update.callback_query and update.callback_query.message:
            try:
                await update.callback_query.edit_message_text(
                    text, reply_markup=markup, parse_mode="HTML",
                    disable_web_page_preview=True)
                ctx.user_data["mt_msg_id"] = update.callback_query.message.message_id
                ctx.user_data["mt_chat_id"] = update.callback_query.message.chat_id
                return
            except Exception: pass
        if update.message:
            try: await update.message.delete()
            except Exception: pass
        chat_id = update.effective_chat.id if update.effective_chat else ctx.user_data.get("mt_chat_id")
        if not chat_id:
            return
        new_msg = await ctx.bot.send_message(chat_id, text, reply_markup=markup,
                                              parse_mode="HTML", disable_web_page_preview=True)
        ctx.user_data["mt_msg_id"] = new_msg.message_id
        ctx.user_data["mt_chat_id"] = new_msg.chat_id
    except Exception as e:
        log.error(f"_mt_show: {e}")

async def _mt_render(update, ctx, node_id):
    node = mn_get_node(node_id)
    if not node:
        await _mt_show(update, ctx, "❌ العنصر غير موجود.", back_admin())
        return MT_ACTION
    children = mn_get_children_all(node_id)
    emoji = node["emoji"] or ""
    vis = "🟢 ظاهر" if node["is_active"] else "🔴 مخفي"
    is_cat = node["node_type"] == "category"
    text = (f"{emoji} <b>{html.escape(node['title'])}</b>\n\n"
            f"النوع: {'📦 قسم أرقام' if is_cat else '📁 مجلد'}\n"
            f"الحالة: {vis}\n"
            f"اللون: {node['color_style']}\n")
    if is_cat:
        text += f"💰 السعر: {node['price']:.2f}$\n"
        text += f"📱 المتوفر: {mn_count_stock(node_id)}\n"
    text += f"📂 الأزرار الفرعية: {len(children)}"

    kb = []
    for ch in children:
        e = ch["emoji"] or ""
        v = "" if ch["is_active"] else " 🚫"
        suffix = ""
        if ch["node_type"] == "category":
            suffix = f" | {ch['price']:.2f}$"
        kb.append([InlineKeyboardButton(
            f"{e} {ch['title']}{v}{suffix}"[:60],
            callback_data=f"MTv_{ch['id']}",
            style=ch["color_style"] or "primary")])

    kb.append([InlineKeyboardButton("➕️ إضافة زر داخل هذا",
             callback_data=f"MT_add_child_{node_id}", style="success")])

    if is_cat:
        kb.append([InlineKeyboardButton("📥 إضافة أرقام",
                 callback_data=f"MT_addnums_{node_id}", style="success")])
        kb.append([InlineKeyboardButton("✏️ تعديل السعر",
                 callback_data=f"MT_price_{node_id}", style="primary")])
        kb.append([InlineKeyboardButton("🗑 حذف أرقام القسم",
                 callback_data=f"MT_clearnums_{node_id}", style="danger")])
    else:
        kb.append([InlineKeyboardButton("💰 تحويل لقسم أرقام",
                 callback_data=f"MT_tocat_{node_id}", style="primary")])

    kb.append([InlineKeyboardButton("✏️ الاسم", callback_data=f"MT_name_{node_id}", style="primary"),
               InlineKeyboardButton("😀 الإيموجي", callback_data=f"MT_emoji_{node_id}", style="primary")])
    kb.append([InlineKeyboardButton("🎨 اللون", callback_data=f"MT_color_{node_id}", style="primary")])
    kb.append([InlineKeyboardButton("👁 إظهار/إخفاء", callback_data=f"MT_toggle_{node_id}", style="primary")])
    kb.append([InlineKeyboardButton("🗑 حذف هذا الزر", callback_data=f"MT_del_{node_id}", style="danger")])

    parent_id = node["parent_id"]
    if parent_id is None:
        kb.append([InlineKeyboardButton("🔙 رجوع للجذر", callback_data="MT_root", style="primary")])
    else:
        kb.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"MTv_{parent_id}", style="primary")])

    await _mt_show(update, ctx, text, kb)
    return MT_ACTION

async def mt_root(update, ctx):
    q = update.callback_query
    await _mt_answer(q)
    if not is_admin(q.from_user.id): return ConversationHandler.END
    for k in ["mt_mode", "mt_edit_id", "mt_new_parent", "mt_new_title",
              "mt_new_emoji", "mt_new_color", "mt_new_price", "mt_new_type"]:
        ctx.user_data.pop(k, None)
    roots = mn_get_children_all(None)
    kb = []
    for node in roots:
        emoji = node["emoji"] or ""
        vis = "" if node["is_active"] else " 🚫"
        suffix = ""
        if node["node_type"] == "category":
            suffix = f" | {node['price']:.2f}$"
        kb.append([InlineKeyboardButton(
            f"{emoji} {node['title']}{vis}{suffix}"[:60],
            callback_data=f"MTv_{node['id']}",
            style=node["color_style"] or "primary")])
    kb.append([InlineKeyboardButton("➕️ إضافة زر رئيسي جديد", callback_data="MT_add_root", style="success")])
    kb.append([mk_btn("admin_back")])
    text = ("🛒 <b>إدارة قوائم المتجر</b>\n\n"
            "🏗️ كيف تبني الشجرة:\n"
            "1️⃣ أضف زر رئيسي (مجلد)\n"
            "2️⃣ ادخل عليه وأضف أزرار فرعية\n"
            "3️⃣ الأزرار الأخيرة تكون \"📦 قسم أرقام\" (لها سعر)\n\n"
            "📁 <b>مجلد</b> = يحتوي على أزرار\n"
            "📦 <b>قسم أرقام</b> = يحتوي على أرقام للبيع\n\n"
            f"📂 الأزرار الرئيسية: {len(roots)}")
    await _mt_show(update, ctx, text, kb)
    return MT_VIEW

async def mt_view_node(update, ctx):
    q = update.callback_query
    await _mt_answer(q)
    if not is_admin(q.from_user.id): return ConversationHandler.END
    try: nid = int(q.data.replace("MTv_", ""))
    except Exception:
        await _mt_show(update, ctx, "❌ معرف غير صالح.", back_admin())
        return MT_ACTION
    return await _mt_render(update, ctx, nid)

async def mt_add_root_start(update, ctx):
    q = update.callback_query
    await _mt_answer(q)
    if not is_admin(q.from_user.id): return ConversationHandler.END
    ctx.user_data["mt_new_parent"] = None
    ctx.user_data["mt_mode"] = "new"
    ctx.user_data.pop("mt_edit_id", None)
    await _mt_show(update, ctx,
        "➕️ <b>إضافة زر رئيسي جديد</b>\n\n"
        "📝 أرسل اسم الزر:\n\n"
        "أمثلة:\n• أرقام واتساب\n• أرقام تليجرام\n• أرقام احتيالية\n\n"
        "/cancel للإلغاء ❌️.",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return MT_IN_TITLE

async def mt_add_child_start(update, ctx):
    q = update.callback_query
    await _mt_answer(q)
    if not is_admin(q.from_user.id): return ConversationHandler.END
    try: parent_id = int(q.data.replace("MT_add_child_", ""))
    except Exception: return ConversationHandler.END
    parent = mn_get_node(parent_id)
    if not parent:
        await _mt_show(update, ctx, "❌ الزر الأب غير موجود.", back_admin())
        return A_MENU
    ctx.user_data["mt_new_parent"] = parent_id
    ctx.user_data["mt_mode"] = "new"
    ctx.user_data.pop("mt_edit_id", None)
    await _mt_show(update, ctx,
        f"➕️ <b>إضافة زر داخل: {html.escape(parent['title'])}</b>\n\n"
        f"📝 أرسل اسم الزر الجديد:\n\n"
        f"مثال: أرقام واتساب عراقية\n\n/cancel للإلغاء ❌️.",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return MT_IN_TITLE

async def mt_in_title(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    title = update.message.text.strip()
    if len(title) < 1 or len(title) > 60:
        await _mt_show(update, ctx, "⚠️ الاسم لازم 1-60 حرف. أرسل مرة ثانية:")
        return MT_IN_TITLE
    ctx.user_data["mt_new_title"] = title
    await _mt_show(update, ctx,
        f"✅ الاسم: <b>{html.escape(title)}</b>\n\n"
        f"😀 أرسل الإيموجي (أو أرسل <code>.</code> إذا ما تريد):")
    return MT_IN_EMOJI

async def mt_in_emoji(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    emoji = update.message.text.strip()
    if emoji == ".": emoji = ""
    if len(emoji) > 12: emoji = emoji[:12]
    ctx.user_data["mt_new_emoji"] = emoji
    await _mt_show(update, ctx,
        f"✅ الإيموجي: {emoji or '(بدون)'}\n\n🎨 اختر لون الزر:",
        [[InlineKeyboardButton("🟦 أزرق", callback_data="MT_newcolor_primary", style="primary")],
         [InlineKeyboardButton("🟩 أخضر", callback_data="MT_newcolor_success", style="success")],
         [InlineKeyboardButton("🟥 أحمر", callback_data="MT_newcolor_danger", style="danger")],
         [InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return MT_IN_COLOR

async def mt_newcolor_pick(update, ctx):
    q = update.callback_query
    await _mt_answer(q)
    if not is_admin(q.from_user.id): return ConversationHandler.END
    style = q.data.replace("MT_newcolor_", "")
    if style not in COLOR_STYLES: style = "primary"
    ctx.user_data["mt_new_color"] = style
    await _mt_show(update, ctx,
        f"✅ اللون: {style}\n\n"
        f"📂 <b>شنو نوع هذا الزر؟</b>\n\n"
        f"📁 <b>مجلد</b> = راح يحتوي على أزرار فرعية داخله\n"
        f"📦 <b>قسم أرقام</b> = راح يحتوي على أرقام للبيع (له سعر)",
        [[InlineKeyboardButton("📁 مجلد (أزرار فرعية)", callback_data="MT_newtype_folder", style="primary")],
         [InlineKeyboardButton("📦 قسم أرقام (للبيع)", callback_data="MT_newtype_category", style="success")],
         [InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return MT_IN_TYPE

async def mt_newtype_pick(update, ctx):
    q = update.callback_query
    await _mt_answer(q)
    if not is_admin(q.from_user.id): return ConversationHandler.END
    ntype = "category" if q.data == "MT_newtype_category" else "folder"
    ctx.user_data["mt_new_type"] = ntype
    if ntype == "category":
        await _mt_show(update, ctx,
            "💰 <b>سعر قسم الأرقام</b>\n\n"
            "أرسل السعر بالدولار (مثال: 1.5):")
        return MT_IN_PRICE
    ctx.user_data["mt_new_price"] = 0
    return await mt_save_new(update, ctx)

async def mt_in_price(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    try:
        price = float(update.message.text.strip())
        if price < 0 or price > 100000: raise ValueError
    except Exception:
        await _mt_show(update, ctx, "⚠️ أرسل رقم صحيح (مثال: 1.5):")
        return MT_IN_PRICE
    ctx.user_data["mt_new_price"] = price
    return await mt_save_new(update, ctx)

async def mt_save_new(update, ctx):
    title = ctx.user_data.pop("mt_new_title", None)
    emoji = ctx.user_data.pop("mt_new_emoji", "")
    color = ctx.user_data.pop("mt_new_color", "primary")
    ntype = ctx.user_data.pop("mt_new_type", "folder")
    price = ctx.user_data.pop("mt_new_price", 0)
    parent_id = ctx.user_data.pop("mt_new_parent", None)
    ctx.user_data.pop("mt_mode", None)
    if not title:
        await _mt_show(update, ctx, "❌ انتهت الجلسة.", back_admin())
        return A_MENU
    try:
        c = db()
        if parent_id is None:
            pos = c.execute("SELECT COALESCE(MAX(position),0)+1 p FROM menu_nodes WHERE parent_id IS NULL").fetchone()["p"]
        else:
            pos = c.execute("SELECT COALESCE(MAX(position),0)+1 p FROM menu_nodes WHERE parent_id=?", (parent_id,)).fetchone()["p"]
        cur = c.execute(
            "INSERT INTO menu_nodes(parent_id, title, emoji, color_style, node_type, price, position, is_active, created_at) "
            "VALUES(?,?,?,?,?,?,?,1,?)",
            (parent_id, title, emoji, color, ntype, price, pos, datetime.now().isoformat()))
        new_id = cur.lastrowid
        c.commit(); c.close()
        return await _mt_render(update, ctx, new_id)
    except Exception as e:
        log.error(f"mt_save_new: {e}")
        await _mt_show(update, ctx, f"❌ فشل: {str(e)[:150]}", back_admin())
        return A_MENU

async def mt_name_start(update, ctx):
    q = update.callback_query
    await _mt_answer(q)
    if not is_admin(q.from_user.id): return ConversationHandler.END
    try: nid = int(q.data.replace("MT_name_", ""))
    except Exception: return ConversationHandler.END
    node = mn_get_node(nid)
    if not node: return ConversationHandler.END
    ctx.user_data["mt_edit_id"] = nid
    ctx.user_data["mt_mode"] = "edit_name"
    await _mt_show(update, ctx,
        f"✏️ <b>تعديل الاسم</b>\n\nالحالي: {html.escape(node['title'])}\n\n"
        f"📝 أرسل الاسم الجديد:",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return MT_IN_TITLE

async def mt_name_save(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    nid = ctx.user_data.pop("mt_edit_id", None)
    ctx.user_data.pop("mt_mode", None)
    if not nid:
        await _mt_show(update, ctx, "❌ انتهت الجلسة.", back_admin())
        return A_MENU
    new_name = update.message.text.strip()
    if len(new_name) < 1 or len(new_name) > 60:
        ctx.user_data["mt_edit_id"] = nid
        ctx.user_data["mt_mode"] = "edit_name"
        await _mt_show(update, ctx, "⚠️ الاسم 1-60 حرف. أرسل مرة ثانية:")
        return MT_IN_TITLE
    c = db()
    c.execute("UPDATE menu_nodes SET title=? WHERE id=?", (new_name, nid))
    c.commit(); c.close()
    return await _mt_render(update, ctx, nid)

async def mt_emoji_start(update, ctx):
    q = update.callback_query
    await _mt_answer(q)
    if not is_admin(q.from_user.id): return ConversationHandler.END
    try: nid = int(q.data.replace("MT_emoji_", ""))
    except Exception: return ConversationHandler.END
    node = mn_get_node(nid)
    if not node: return ConversationHandler.END
    ctx.user_data["mt_edit_id"] = nid
    ctx.user_data["mt_mode"] = "edit_emoji"
    await _mt_show(update, ctx,
        f"😀 <b>تعديل الإيموجي</b>\n\nالحالي: {node['emoji'] or '(بدون)'}\n\n"
        f"أرسل الإيموجي الجديد (أو <code>.</code> لحذفه):",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return MT_IN_EMOJI

async def mt_emoji_save(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    nid = ctx.user_data.pop("mt_edit_id", None)
    ctx.user_data.pop("mt_mode", None)
    if not nid:
        await _mt_show(update, ctx, "❌ انتهت الجلسة.", back_admin())
        return A_MENU
    emoji = update.message.text.strip()
    if emoji == ".": emoji = ""
    if len(emoji) > 12: emoji = emoji[:12]
    c = db()
    c.execute("UPDATE menu_nodes SET emoji=? WHERE id=?", (emoji, nid))
    c.commit(); c.close()
    return await _mt_render(update, ctx, nid)

async def mt_color_menu(update, ctx):
    q = update.callback_query
    await _mt_answer(q)
    if not is_admin(q.from_user.id): return ConversationHandler.END
    try: nid = int(q.data.replace("MT_color_", ""))
    except Exception: return ConversationHandler.END
    node = mn_get_node(nid)
    if not node: return ConversationHandler.END
    await _mt_show(update, ctx,
        f"🎨 <b>تغيير اللون</b>\n\nالحالي: {node['color_style']}\n\nاختر اللون الجديد:",
        [[InlineKeyboardButton("🟦 أزرق", callback_data=f"MT_setcolor_{nid}_primary", style="primary")],
         [InlineKeyboardButton("🟩 أخضر", callback_data=f"MT_setcolor_{nid}_success", style="success")],
         [InlineKeyboardButton("🟥 أحمر", callback_data=f"MT_setcolor_{nid}_danger", style="danger")],
         [InlineKeyboardButton("🔙 رجوع", callback_data=f"MTv_{nid}", style="primary")]])
    return MT_ACTION

async def mt_color_set(update, ctx):
    q = update.callback_query
    if not is_admin(q.from_user.id): return ConversationHandler.END
    parts = q.data.replace("MT_setcolor_", "").split("_")
    try:
        nid = int(parts[0]); style = parts[1]
    except Exception: return ConversationHandler.END
    if style not in COLOR_STYLES: style = "primary"
    c = db()
    c.execute("UPDATE menu_nodes SET color_style=? WHERE id=?", (style, nid))
    c.commit(); c.close()
    return await _mt_render(update, ctx, nid)

async def mt_toggle_node(update, ctx):
    q = update.callback_query
    if not is_admin(q.from_user.id): return ConversationHandler.END
    try: nid = int(q.data.replace("MT_toggle_", ""))
    except Exception: return ConversationHandler.END
    c = db()
    row = c.execute("SELECT is_active FROM menu_nodes WHERE id=?", (nid,)).fetchone()
    if not row: c.close(); return ConversationHandler.END
    new_val = 0 if row["is_active"] else 1
    c.execute("UPDATE menu_nodes SET is_active=? WHERE id=?", (new_val, nid))
    c.commit(); c.close()
    return await _mt_render(update, ctx, nid)

async def mt_price_start(update, ctx):
    q = update.callback_query
    await _mt_answer(q)
    if not is_admin(q.from_user.id): return ConversationHandler.END
    try: nid = int(q.data.replace("MT_price_", ""))
    except Exception: return ConversationHandler.END
    node = mn_get_node(nid)
    if not node: return ConversationHandler.END
    ctx.user_data["mt_edit_id"] = nid
    ctx.user_data["mt_mode"] = "edit_price"
    await _mt_show(update, ctx,
        f"💰 <b>تعديل السعر</b>\n\nالحالي: {node['price']:.2f}$\n\n"
        f"أرسل السعر الجديد:",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return MT_IN_PRICE

async def mt_price_save(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    nid = ctx.user_data.pop("mt_edit_id", None)
    ctx.user_data.pop("mt_mode", None)
    if not nid:
        await _mt_show(update, ctx, "❌ انتهت الجلسة.", back_admin())
        return A_MENU
    try:
        price = float(update.message.text.strip())
        if price < 0 or price > 100000: raise ValueError
    except Exception:
        ctx.user_data["mt_edit_id"] = nid
        ctx.user_data["mt_mode"] = "edit_price"
        await _mt_show(update, ctx, "⚠️ أرسل رقم صحيح:")
        return MT_IN_PRICE
    c = db()
    c.execute("UPDATE menu_nodes SET price=? WHERE id=?", (price, nid))
    c.commit(); c.close()
    return await _mt_render(update, ctx, nid)

async def mt_tocat(update, ctx):
    q = update.callback_query
    await _mt_answer(q)
    if not is_admin(q.from_user.id): return ConversationHandler.END
    try: nid = int(q.data.replace("MT_tocat_", ""))
    except Exception: return ConversationHandler.END
    node = mn_get_node(nid)
    if not node: return ConversationHandler.END
    ctx.user_data["mt_edit_id"] = nid
    ctx.user_data["mt_mode"] = "tocat"
    await _mt_show(update, ctx,
        f"💰 <b>تحويل المجلد إلى قسم أرقام</b>\n\n"
        f"📦 {html.escape(node['title'])}\n\n"
        f"⚠️ راح يصير قسم قابل للبيع، والأزرار الفرعية تبقى.\n\n"
        f"📝 أرسل سعر القسم:",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return MT_IN_PRICE

async def mt_tocat_save(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    nid = ctx.user_data.pop("mt_edit_id", None)
    ctx.user_data.pop("mt_mode", None)
    if not nid:
        await _mt_show(update, ctx, "❌ انتهت الجلسة.", back_admin())
        return A_MENU
    try:
        price = float(update.message.text.strip())
        if price < 0 or price > 100000: raise ValueError
    except Exception:
        ctx.user_data["mt_edit_id"] = nid
        ctx.user_data["mt_mode"] = "tocat"
        await _mt_show(update, ctx, "⚠️ أرسل رقم صحيح:")
        return MT_IN_PRICE
    c = db()
    c.execute("UPDATE menu_nodes SET node_type='category', price=? WHERE id=?", (price, nid))
    c.commit(); c.close()
    return await _mt_render(update, ctx, nid)

async def mt_del_node(update, ctx):
    q = update.callback_query
    await _mt_answer(q)
    if not is_admin(q.from_user.id): return ConversationHandler.END
    try: nid = int(q.data.replace("MT_del_", ""))
    except Exception: return ConversationHandler.END
    node = mn_get_node(nid)
    if not node: return ConversationHandler.END
    children = mn_get_children_all(nid)
    warn = ""
    if children:
        warn = f"\n⚠️ فيه {len(children)} زر فرعي — راح ينحذفون كلهن!"
    await _mt_show(update, ctx,
        f"🗑 <b>حذف الزر</b>\n\n{html.escape(node['title'])}{warn}\n\n"
        f"هل أنت متأكد؟",
        [[InlineKeyboardButton("🗑 نعم احذف الكل", callback_data=f"MT_delok_{nid}", style="danger")],
         [InlineKeyboardButton("🔙 إلغاء", callback_data=f"MTv_{nid}", style="primary")]])
    return MT_ACTION

def _mt_delete_recursive(c, node_id):
    children = c.execute("SELECT id FROM menu_nodes WHERE parent_id=?", (node_id,)).fetchall()
    for ch in children:
        _mt_delete_recursive(c, ch["id"])
    c.execute("DELETE FROM numbers WHERE category_id=?", (node_id,))
    c.execute("DELETE FROM menu_nodes WHERE id=?", (node_id,))

async def mt_del_ok(update, ctx):
    q = update.callback_query
    if not is_admin(q.from_user.id): return ConversationHandler.END
    try: nid = int(q.data.replace("MT_delok_", ""))
    except Exception: return ConversationHandler.END
    node = mn_get_node(nid)
    if not node:
        await _mt_answer(q, "❌ غير موجود", alert=True)
        return ConversationHandler.END
    parent_id = node["parent_id"]
    try:
        c = db()
        _mt_delete_recursive(c, nid)
        c.commit(); c.close()
        await _mt_answer(q, "✅ تم الحذف", alert=True)
    except Exception as e:
        log.error(f"mt_del_ok: {e}")
        await _mt_answer(q, f"فشل: {str(e)[:80]}", alert=True)
        return ConversationHandler.END
    if parent_id is None:
        return await mt_root(update, ctx)
    return await _mt_render(update, ctx, parent_id)

async def mt_addnums_start(update, ctx):
    q = update.callback_query
    await _mt_answer(q)
    if not is_admin(q.from_user.id): return ConversationHandler.END
    try: nid = int(q.data.replace("MT_addnums_", ""))
    except Exception: return ConversationHandler.END
    ctx.user_data["bn_cat"] = nid
    node = mn_get_node(nid)
    if not node:
        await _mt_show(update, ctx, "❌ القسم غير موجود.", back_admin())
        return ConversationHandler.END
    await _mt_show(update, ctx,
        f"📥 <b>إضافة أرقام</b>\n\n"
        f"📦 {html.escape(node['title'])}\n💰 {node['price']:.2f}$\n\n"
        f"أرسل الأرقام بصيغة دولية، كل رقم بسطر:\n\n"
        f"مثال:\n<code>+9647701234567</code>\n<code>+9647701234568</code>\n\n"
        f"/cancel للإلغاء ❌️.",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return A_BN_LIST

async def mt_clearnums(update, ctx):
    q = update.callback_query
    await _mt_answer(q)
    if not is_admin(q.from_user.id): return ConversationHandler.END
    try: nid = int(q.data.replace("MT_clearnums_", ""))
    except Exception: return ConversationHandler.END
    node = mn_get_node(nid)
    if not node: return ConversationHandler.END
    c = db()
    cnt = c.execute("SELECT COUNT(*) n FROM numbers WHERE category_id=? AND status='available'", (nid,)).fetchone()["n"]
    c.close()
    await _mt_show(update, ctx,
        f"🗑 <b>حذف أرقام القسم</b>\n\n{html.escape(node['title'])}\n\n"
        f"عدد الأرقام المتوفرة: {cnt}\n\n"
        f"سيتم حذف الأرقام المتوفرة فقط (المبيعة تبقى).",
        [[InlineKeyboardButton(f"🗑 احذف {cnt} رقم", callback_data=f"MT_clearnums_ok_{nid}", style="danger")],
         [InlineKeyboardButton("🔙 إلغاء", callback_data=f"MTv_{nid}", style="primary")]])
    return MT_ACTION

async def mt_clearnums_ok(update, ctx):
    q = update.callback_query
    if not is_admin(q.from_user.id): return ConversationHandler.END
    try: nid = int(q.data.replace("MT_clearnums_ok_", ""))
    except Exception: return ConversationHandler.END
    c = db()
    n = c.execute("SELECT COUNT(*) n FROM numbers WHERE category_id=? AND status='available'", (nid,)).fetchone()["n"]
    c.execute("DELETE FROM numbers WHERE category_id=? AND status='available'", (nid,))
    c.commit(); c.close()
    await _mt_answer(q, f"✅ تم حذف {n} رقم", alert=True)
    return await _mt_render(update, ctx, nid)

# ================== Routers ==================
async def _mt_title_router(update, ctx):
    if ctx.user_data.get("mt_mode") == "edit_name":
        return await mt_name_save(update, ctx)
    return await mt_in_title(update, ctx)

async def _mt_emoji_router(update, ctx):
    if ctx.user_data.get("mt_mode") == "edit_emoji":
        return await mt_emoji_save(update, ctx)
    return await mt_in_emoji(update, ctx)

async def _mt_price_router(update, ctx):
    mode = ctx.user_data.get("mt_mode")
    if mode == "edit_price":
        return await mt_price_save(update, ctx)
    elif mode == "tocat":
        return await mt_tocat_save(update, ctx)
    return await mt_in_price(update, ctx)

async def _bal_router(update, ctx):
    if ctx.user_data.get("admin_mode") == "points":
        return await addpoints_id(update, ctx)
    return await addbal_id(update, ctx)

async def _users_view_router(update, ctx):
    if ctx.user_data.get("broadcast_mode"):
        ctx.user_data.pop("broadcast_mode", None)
        return await broadcast_do(update, ctx)
    ctx.user_data.pop("ban_mode", None)
    return await cb_banuser_do(update, ctx)
# ================== 🎨 لوحة تحرير الأزرار ==================
async def btn_panel_root(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    ctx.user_data.pop("btn_edit_key", None)
    kb = [
        [InlineKeyboardButton("🏠 أزرار المستخدم", callback_data="BTN_cat_home", style="success")],
        [InlineKeyboardButton("⚙️ أزرار لوحة الأدمن", callback_data="BTN_cat_admin", style="primary")],
        [InlineKeyboardButton("🔙 أزرار الرجوع", callback_data="BTN_cat_back", style="primary")],
        [mk_btn("admin_back")],
    ]
    await send(update,
        "🎨 <b>تحرير أزرار البوت</b>\n\n"
        "اختر الفئة اللي تريد تعدّل أزرارها:\n\n"
        "• <b>🏠 أزرار المستخدم</b> — الأزرار الرئيسية اللي يشوفها المستخدم\n"
        "• <b>⚙️ أزرار لوحة الأدمن</b> — الأزرار داخل لوحتك\n"
        "• <b>🔙 أزرار الرجوع</b> — أزرار الرجوع للخلف\n\n"
        "💡 <b>معلومات:</b>\n"
        "• تقدر تغيّر <b>النص</b>\n"
        "• تقدر تغيّر <b>اللون</b> (أزرق/أخضر/أحمر)\n"
        "• تقدر تضيف <b>✨ إيموجي متحرك</b> (Premium)\n"
        "• زر الإعادة يرجّع الزر لحالته الأصلية",
        kb)
    return A_MENU

async def btn_cat_view(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    cat = q.data.replace("BTN_cat_", "")
    if cat == "home":
        keys = ["shop","my_purchases","balance","daily_gift","recharge",
                "redeem","channel","complaint","admin_open","asia_auto","shop_now"]
        title = "🏠 <b>أزرار المستخدم</b>"
    elif cat == "admin":
        keys = ["A_stats","A_tree","A_addcat","A_addnums","A_bulknums","A_editprice",
                "A_editcatname","A_delcat","A_delnum","A_viewnums","A_addbal","A_addpoints",
                "A_createcode","A_listcodes","A_users","A_sessions","A_broadcast",
                "A_btn_customs","A_maint_on","A_maint_off"]
        title = "⚙️ <b>أزرار لوحة الأدمن</b>"
    elif cat == "back":
        keys = ["home","admin_back","sessions_back","join_channel","check_sub"]
        title = "🔙 <b>أزرار الرجوع</b>"
    else:
        await send(update, "❌ فئة غير معروفة.", back_admin())
        return A_MENU

    kb = []
    for k in keys:
        if k not in BUTTON_DEFAULTS: continue
        default_txt = BUTTON_DEFAULTS[k][0]
        cur_txt = btn_text(k)
        cur_style = btn_style(k)
        has_emoji = "✨" if btn_emoji_get(k) else ""
        mark = "✏️" if cur_txt != default_txt else "▫️"
        label = f"{mark}{has_emoji} {cur_txt}"[:60]
        kb.append([InlineKeyboardButton(label, callback_data=f"BTN_edit_{k}", style=cur_style)])
    kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="BTN_root", style="primary")])
    await send(update,
        f"{title}\n\n"
        f"✏️ = معدّل يدوياً | ✨ = فيه إيموجي مميز | ▫️ = افتراضي\n\n"
        f"اضغط على أي زر لتعديله:",
        kb)
    return A_MENU

async def btn_action_text(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    key = ctx.user_data.get("btn_edit_key")
    if not key:
        await send(update, "❌ انتهت الجلسة.", back_admin())
        return A_MENU
    cur_txt = btn_text(key)
    await send(update,
        f"📝 <b>تغيير نص الزر</b>\n\n"
        f"<b>النص الحالي:</b>\n{html.escape(cur_txt)}\n\n"
        f"أرسل النص الجديد الآن.\n\n"
        f"💡 <b>ملاحظات:</b>\n"
        f"• الحد الأقصى: 60 حرف\n"
        f"• أرسل <code>.</code> لإرجاع النص الافتراضي\n\n"
        f"/cancel للإلغاء ❌️.",
        [[InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return BTN_EDIT_TEXT

async def btn_text_save(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    key = ctx.user_data.get("btn_edit_key")
    if not key:
        await update.message.reply_text("❌ انتهت الجلسة.",
            reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    new_text = (update.message.text or "").strip()
    if not new_text:
        await update.message.reply_text("⚠️ أرسل نص صحيح:")
        return BTN_EDIT_TEXT
    if len(new_text) > 60:
        new_text = new_text[:60]
    if new_text == ".":
        _, cur_style = btn_get(key)
        default_txt, default_style = BUTTON_DEFAULTS.get(key, ("?", "primary"))
        btn_set(key, None, cur_style)
        await update.message.reply_text(
            f"♻️ تم إرجاع النص الافتراضي:\n{html.escape(default_txt)}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    _, cur_style = btn_get(key)
    default_txt, default_style = BUTTON_DEFAULTS.get(key, ("?", "primary"))
    style_to_save = cur_style if cur_style else default_style
    btn_set(key, new_text, style_to_save)
    await update.message.reply_text(
        f"✅ <b>تم حفظ النص الجديد</b>\n\n"
        f"{html.escape(new_text)}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(back_admin()))
    return A_MENU

async def btn_action_emoji(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    key = ctx.user_data.get("btn_edit_key")
    if not key:
        await send(update, "❌ انتهت الجلسة.", back_admin())
        return A_MENU
    cur = btn_emoji_get(key)
    cur_line = f"<code>{cur}</code>" if cur else "(بدون)"
    await send(update,
        f"✨ <b>إيموجي متحرك للزر</b>\n\n"
        f"<b>المعرّف الحالي:</b> {cur_line}\n\n"
        f"<b>طريقة الإضافة:</b>\n\n"
        f"1️⃣ افتح الإيموجيات المميزة في تيليجرام\n"
        f"2️⃣ اختر الإيموجي اللي تريده\n"
        f"3️⃣ <b>انسخه</b> (اضغط عليه طويلاً → Copy)\n"
        f"4️⃣ ارسله هنا كرسالة\n\n"
        f"البوت راح يقرأ الـ custom_emoji_id ويحفظه تلقائياً ✅\n\n"
        f"⚠️ <b>مهم:</b> حسابك لازم يكون عنده <b>Telegram Premium</b>\n\n"
        f"• أرسل <code>.</code> لمسح الإيموجي\n\n"
        f"/cancel للإلغاء ❌️.",
        [[InlineKeyboardButton("🗑 مسح الإيموجي", callback_data="BTN_emoji_clear", style="danger")],
         [InlineKeyboardButton("إلغاء ❌️", callback_data="admin_cancel", style="danger")]])
    return BTN_EDIT_EMOJI

async def btn_emoji_save(update, ctx):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    key = ctx.user_data.get("btn_edit_key")
    if not key:
        await update.message.reply_text("❌ انتهت الجلسة.",
            reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    msg = update.message
    text = (msg.text or "").strip()
    if text == ".":
        btn_emoji_reset(key)
        await msg.reply_text("🗑 تم مسح الإيموجي المميز من الزر.",
            reply_markup=InlineKeyboardMarkup(back_admin()))
        return A_MENU
    emoji_id = None
    if msg.entities:
        for ent in msg.entities:
            ent_type = str(getattr(ent, "type", ""))
            if "custom_emoji" in ent_type.lower():
                emoji_id = getattr(ent, "custom_emoji_id", None)
                if emoji_id: break
    if not emoji_id:
        await msg.reply_text(
            "❌ <b>ما لقيت إيموجي مميز</b>\n\n"
            "تأكد من:\n"
            "• إنك ترسل <b>إيموجي مميز</b> (مو عادي)\n"
            "• إن حسابك فيه <b>Telegram Premium</b>\n"
            "• إنك نسخت الإيموجي بشكل صحيح\n\n"
            "جرّب مرة ثانية، أو أرسل <code>.</code> للإلغاء:",
            parse_mode="HTML")
        return BTN_EDIT_EMOJI
    btn_emoji_set(key, str(emoji_id))
    await msg.reply_text(
        f"✅ <b>تم حفظ الإيموجي المميز</b>\n\n"
        f"🆔 المعرّف: <code>{emoji_id}</code>\n\n"
        f"راح يظهر على الزر مباشرة.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(back_admin()))
    return A_MENU

async def _render_btn_edit_panel(update, ctx, key):
    if not key or key not in BUTTON_DEFAULTS:
        await send(update, "❌ زر غير معروف.", back_admin())
        return A_MENU
    ctx.user_data["btn_edit_key"] = key
    cur_txt = btn_text(key)
    cur_style = btn_style(key)
    cur_emoji = btn_emoji_get(key)
    emoji_line = f"<code>{cur_emoji}</code>" if cur_emoji else "(بدون)"

    kb = [
        [InlineKeyboardButton("📝 تغيير النص", callback_data="BTN_action_text", style="success")],
        [InlineKeyboardButton("✨ إيموجي متحرك (Premium)", callback_data="BTN_action_emoji", style="success")],
        [InlineKeyboardButton("🎨 تغيير اللون", callback_data="BTN_action_color", style="primary")],
        [InlineKeyboardButton("♻️ إعادة للافتراضي", callback_data="BTN_action_reset", style="danger")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="BTN_root", style="primary")],
    ]
    await send(update,
        f"🛠 <b>تحرير زر</b>\n\n"
        f"<b>المفتاح:</b> <code>{html.escape(key)}</code>\n\n"
        f"📌 <b>النص الحالي:</b>\n{html.escape(cur_txt)}\n\n"
        f"📌 <b>اللون الحالي:</b> {cur_style}\n\n"
        f"✨ <b>إيموجي مميز:</b> {emoji_line}\n\n"
        f"اختر العملية:",
        kb)
    return A_MENU

async def btn_edit_start(update, ctx):
    q = update.callback_query
    try:
        await q.answer()
    except Exception:
        pass
    if not is_admin(q.from_user.id): return ConversationHandler.END
    key = q.data.replace("BTN_edit_", "")
    return await _render_btn_edit_panel(update, ctx, key)

async def btn_emoji_clear(update, ctx):
    q = update.callback_query
    try:
        await q.answer("🗑 تم المسح", show_alert=True)
    except Exception:
        pass
    if not is_admin(q.from_user.id): return ConversationHandler.END
    key = ctx.user_data.get("btn_edit_key")
    if key:
        btn_emoji_reset(key)
    return await _render_btn_edit_panel(update, ctx, key)

async def btn_action_color(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    key = ctx.user_data.get("btn_edit_key")
    if not key:
        await send(update, "❌ انتهت الجلسة.", back_admin())
        return A_MENU
    cur_style = btn_style(key)
    await send(update,
        f"🎨 <b>تغيير لون الزر</b>\n\n"
        f"<b>اللون الحالي:</b> {cur_style}\n\n"
        f"اختر اللون الجديد:",
        [[InlineKeyboardButton("🟦 أزرق", callback_data="BTN_color_primary", style="primary")],
         [InlineKeyboardButton("🟩 أخضر", callback_data="BTN_color_success", style="success")],
         [InlineKeyboardButton("🟥 أحمر", callback_data="BTN_color_danger", style="danger")],
         [InlineKeyboardButton("🔙 رجوع", callback_data="BTN_root", style="primary")]])
    return A_MENU

async def btn_color_set(update, ctx):
    q = update.callback_query
    if not is_admin(q.from_user.id): return ConversationHandler.END
    key = ctx.user_data.get("btn_edit_key")
    if not key:
        await q.answer("❌ انتهت الجلسة", show_alert=True)
        return ConversationHandler.END
    style = q.data.replace("BTN_color_", "")
    if style not in COLOR_STYLES:
        await q.answer("لون غير صالح", show_alert=True)
        return ConversationHandler.END
    cur_txt, _ = btn_get(key)
    default_txt, default_style = BUTTON_DEFAULTS.get(key, ("?", "primary"))
    text_to_save = cur_txt if cur_txt else None
    btn_set(key, text_to_save, style)
    await q.answer(f"تم تغيير اللون إلى {style}", show_alert=True)
    return await _render_btn_edit_panel(update, ctx, key)

async def btn_action_reset(update, ctx):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id): return ConversationHandler.END
    key = ctx.user_data.get("btn_edit_key")
    if not key:
        await send(update, "❌ انتهت الجلسة.", back_admin())
        return A_MENU
    btn_reset(key)
    btn_emoji_reset(key)
    await q.answer("✅ تم الإرجاع للافتراضي", show_alert=True)
    default_txt, default_style = BUTTON_DEFAULTS.get(key, ("?", "primary"))
    await send(update,
        f"♻️ <b>تم الإرجاع للافتراضي</b>\n\n"
        f"النص: {html.escape(default_txt)}\n"
        f"اللون: {default_style}",
        [[InlineKeyboardButton("🔙 رجوع", callback_data="BTN_root", style="primary")]])
    return A_MENU

# ================== Error Handler ==================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.error(f"Error: {context.error}")
    try:
        log.error("".join(traceback.format_exception(None, context.error, context.error.__traceback__)))
    except Exception: pass
    try:
        if isinstance(update, Update):
            if update.effective_message:
                await update.effective_message.reply_text("⚠️ صار خطأ مؤقت. حاول مرة ثانية.")
            elif update.callback_query:
                await update.callback_query.answer("حاول مرة ثانية", show_alert=True)
    except Exception: pass

# ================== post_init ==================
async def post_init(app):
    try:
        init_db()
        log.info(f"✅ قاعدة البيانات: {os.path.abspath(DB_PATH)}")
        log.info(f"✅ مجلد السجلات: {os.path.abspath(LOGS_DIR)}")
    except Exception as e:
        log.error(f"init_db (post_init) error: {e}")
    try:
        me = await app.bot.get_me()
        bot_info["username"] = me.username or ""
        log.info(f"🤖 Bot username: {bot_info['username']}")
    except Exception as e:
        log.error(f"get_me error: {e}")
    try:
        await app.bot.set_my_commands([
            BotCommand("start", "الرئيسية 🏠"),
            BotCommand("help", "مساعدة"),
            BotCommand("myid", "معرفي"),
            BotCommand("cancel", "إلغاء ❌️"),
        ], scope=BotCommandScopeDefault())
    except Exception as e:
        log.error(f"set_my_commands: {e}")
# ================== نقطة التشغيل ==================
def main():
    init_db()
    log.info(f"اسم البوت: {BOT_NAME}")
    log.info(f"الأدمنية: {ADMIN_IDS}")
    log.info(f"القناة: {CHANNEL_ID}")
    log.info(f"Telethon: {'OK' if TELETHON_OK else 'NO'}")
    log.info(f"MedoCell: {'OK' if MEDOCELL_OK else 'NO'}")
    log.info(f"Receiver Phone (Asia): {RECEIVER_PHONE}")
    log.info(f"ASIA Price per 1000 IQD: {ASIA_PRICE_PER_1000}$")

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # ========================================================
    # ============ محادثة لوحة الأدمن ============
    # ========================================================
    admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_admin_open, pattern="^admin_open$")],
        states={
            A_MENU: [
                CallbackQueryHandler(cb_stats, pattern="^A_stats$"),
                CallbackQueryHandler(addcat_start, pattern="^A_addcat$"),
                CallbackQueryHandler(addnums_start, pattern="^A_addnums$"),
                CallbackQueryHandler(bulknums_start, pattern="^A_bulknums$"),
                CallbackQueryHandler(editprice_start, pattern="^A_editprice$"),
                CallbackQueryHandler(editcatname_start, pattern="^A_editcatname$"),
                CallbackQueryHandler(delcat_start, pattern="^A_delcat$"),
                CallbackQueryHandler(delnum_start, pattern="^A_delnum$"),
                CallbackQueryHandler(addbal_start, pattern="^A_addbal$"),
                CallbackQueryHandler(addpoints_start, pattern="^A_addpoints$"),
                CallbackQueryHandler(cb_users, pattern="^A_users$"),
                CallbackQueryHandler(cb_banuser_start, pattern="^A_banuser$"),
                CallbackQueryHandler(createcode_start, pattern="^A_createcode$"),
                CallbackQueryHandler(cb_listcodes, pattern="^A_listcodes$"),
                CallbackQueryHandler(cb_delcode_list, pattern="^A_delcode$"),
                CallbackQueryHandler(cb_delcode_do, pattern="^delcode_"),
                CallbackQueryHandler(sess_menu, pattern="^A_sessions$"),
                CallbackQueryHandler(sess_add_start, pattern="^A_sess_add$"),
                CallbackQueryHandler(sess_test_start, pattern="^A_sess_test$"),
                CallbackQueryHandler(sess_del_list, pattern="^A_sess_del$"),
                CallbackQueryHandler(sess_del_all, pattern="^A_sess_delall$"),
                CallbackQueryHandler(sess_del_do, pattern="^sessdel_"),
                CallbackQueryHandler(broadcast_start, pattern="^A_broadcast$"),
                CallbackQueryHandler(viewnums_start, pattern="^A_viewnums$"),
                CallbackQueryHandler(bulk_import_start, pattern="^A_bulk_sessions$"),
                CallbackQueryHandler(cb_admin_back, pattern="^A_back$"),
                CallbackQueryHandler(cb_toggle_maintenance, pattern="^A_toggle_maint$"),
                CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"),
                # ============ إدارة الشجرة ============
                CallbackQueryHandler(mt_root, pattern="^MT_root$"),
                CallbackQueryHandler(mt_view_node, pattern="^MTv_\\d+$"),
                CallbackQueryHandler(mt_add_root_start, pattern="^MT_add_root$"),
                CallbackQueryHandler(mt_add_child_start, pattern="^MT_add_child_\\d+$"),
                # ============ لوحة تحرير الأزرار ============
                CallbackQueryHandler(btn_panel_root, pattern="^A_btn_customs$"),
                CallbackQueryHandler(btn_panel_root, pattern="^BTN_root$"),
                CallbackQueryHandler(btn_cat_view, pattern="^BTN_cat_(home|admin|back)$"),
                CallbackQueryHandler(btn_edit_start, pattern="^BTN_edit_"),
                CallbackQueryHandler(btn_action_text, pattern="^BTN_action_text$"),
                CallbackQueryHandler(btn_action_emoji, pattern="^BTN_action_emoji$"),
                CallbackQueryHandler(btn_emoji_clear, pattern="^BTN_emoji_clear$"),
                CallbackQueryHandler(btn_action_color, pattern="^BTN_action_color$"),
                CallbackQueryHandler(btn_action_reset, pattern="^BTN_action_reset$"),
                CallbackQueryHandler(btn_color_set, pattern="^BTN_color_(primary|success|danger)$"),
            ],
            A_CAT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, addcat_name)],
            A_CAT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, addcat_price)],
            A_NUMS_PICK: [CallbackQueryHandler(addnums_pick, pattern="^nums_\\d+$")],
            A_NUMS_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, addnums_save)],
            A_EDITPICK: [CallbackQueryHandler(editprice_pick, pattern="^editp_\\d+$")],
            A_EDITPRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, editprice_save)],
            A_EDITCAT_PICK: [CallbackQueryHandler(editcatname_pick, pattern="^editcn_\\d+$")],
            A_EDITCAT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, editcatname_save)],
            A_DELPICK: [CallbackQueryHandler(delcat_do, pattern="^delc_\\d+$")],
            A_DELNUM_PICK: [CallbackQueryHandler(delnum_cat_pick, pattern="^dnumcat_\\d+$")],
            A_DELNUM_SELECT: [CallbackQueryHandler(delnum_do, pattern="^dnum_\\d+$")],
            A_BAL_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, _bal_router)],
            A_BAL_AMT: [MessageHandler(filters.TEXT & ~filters.COMMAND, addbal_amt)],
            A_USERS_VIEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, _users_view_router)],
            A_VIEW_NUMS_PICK: [CallbackQueryHandler(viewnums_pick, pattern="^viewn_\\d+$")],
            A_RC_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, createcode_code)],
            A_RC_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, createcode_value)],
            A_RC_MAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, createcode_max)],
            S_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, sess_phone)],
            S_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, sess_code)],
            S_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, sess_password)],
            S_RESEND_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, sess_test_do)],
            A_BULK_ZIP: [MessageHandler(filters.Document.ALL, bulk_import_zip)],
            A_BULK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bulk_receive_phone),
                           CallbackQueryHandler(bulk_skip, pattern="^bulk_skip$")],
            A_BULK_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, bulk_receive_otp),
                         CallbackQueryHandler(bulk_skip, pattern="^bulk_skip$")],
            A_BULK_2FA: [MessageHandler(filters.TEXT & ~filters.COMMAND, bulk_receive_2fa),
                         CallbackQueryHandler(bulk_skip, pattern="^bulk_skip$")],
            A_BN_CAT_PICK: [CallbackQueryHandler(bulknums_cat_pick, pattern="^bnc_\\d+$")],
            A_BN_LIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, bulknums_list)],
            A_BN_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, bulknums_otp),
                       CallbackQueryHandler(bulknums_skip, pattern="^bn_skip$")],
            A_BN_2FA: [MessageHandler(filters.TEXT & ~filters.COMMAND, bulknums_2fa),
                       CallbackQueryHandler(bulknums_skip, pattern="^bn_skip$")],
            # ============ شجرة الإدارة ============
            MT_VIEW: [
                CallbackQueryHandler(mt_root, pattern="^MT_root$"),
                CallbackQueryHandler(mt_view_node, pattern="^MTv_\\d+$"),
                CallbackQueryHandler(mt_add_root_start, pattern="^MT_add_root$"),
                CallbackQueryHandler(mt_add_child_start, pattern="^MT_add_child_\\d+$"),
                CallbackQueryHandler(cb_admin_back, pattern="^A_back$"),
            ],
            MT_ACTION: [
                CallbackQueryHandler(mt_root, pattern="^MT_root$"),
                CallbackQueryHandler(mt_view_node, pattern="^MTv_\\d+$"),
                CallbackQueryHandler(mt_add_root_start, pattern="^MT_add_root$"),
                CallbackQueryHandler(mt_add_child_start, pattern="^MT_add_child_\\d+$"),
                CallbackQueryHandler(mt_name_start, pattern="^MT_name_\\d+$"),
                CallbackQueryHandler(mt_emoji_start, pattern="^MT_emoji_\\d+$"),
                CallbackQueryHandler(mt_price_start, pattern="^MT_price_\\d+$"),
                CallbackQueryHandler(mt_tocat, pattern="^MT_tocat_\\d+$"),
                CallbackQueryHandler(mt_color_menu, pattern="^MT_color_\\d+$"),
                CallbackQueryHandler(mt_color_set, pattern="^MT_setcolor_\\d+_(primary|success|danger)$"),
                CallbackQueryHandler(mt_toggle_node, pattern="^MT_toggle_\\d+$"),
                CallbackQueryHandler(mt_del_node, pattern="^MT_del_\\d+$"),
                CallbackQueryHandler(mt_del_ok, pattern="^MT_delok_\\d+$"),
                CallbackQueryHandler(mt_addnums_start, pattern="^MT_addnums_\\d+$"),
                CallbackQueryHandler(mt_clearnums, pattern="^MT_clearnums_\\d+$"),
                CallbackQueryHandler(mt_clearnums_ok, pattern="^MT_clearnums_ok_\\d+$"),
                CallbackQueryHandler(cb_admin_back, pattern="^A_back$"),
            ],
            MT_IN_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, _mt_title_router)],
            MT_IN_EMOJI: [MessageHandler(filters.TEXT & ~filters.COMMAND, _mt_emoji_router)],
            MT_IN_COLOR: [CallbackQueryHandler(mt_newcolor_pick, pattern="^MT_newcolor_(primary|success|danger)$")],
            MT_IN_TYPE: [CallbackQueryHandler(mt_newtype_pick, pattern="^MT_newtype_(folder|category)$")],
            MT_IN_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, _mt_price_router)],
            # ============ تحرير الأزرار ============
            BTN_EDIT_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, btn_text_save)],
            BTN_EDIT_EMOJI: [MessageHandler(filters.TEXT & ~filters.COMMAND, btn_emoji_save)],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"),
            CallbackQueryHandler(cb_admin_back, pattern="^A_back$"),
            CallbackQueryHandler(btn_panel_root, pattern="^BTN_root$"),
        ],
        allow_reentry=True, per_message=False)

    # ============ محادثة تعبئة الكود ============
    redeem_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(redeem_start, pattern="^redeem$")],
        states={
            U_REDEEM_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, redeem_receive)],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            CallbackQueryHandler(redeem_cancel, pattern="^redeem_cancel$"),
        ],
        allow_reentry=True, per_message=False)

    # ============ محادثة الشكاوى ============
    complaint_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_complaint_start, pattern="^complaint$")],
        states={
            U_COMPLAINT_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_receive)],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            CallbackQueryHandler(complaint_cancel, pattern="^complaint_cancel$"),
        ],
        allow_reentry=True, per_message=False)

    # ============ محادثة الرد على الشكاوى ============
    complaint_reply_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(complaint_reply_start, pattern="^creply_\\d+$")],
        states={
            A_COMPLAINT_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_reply_send)],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            CallbackQueryHandler(complaint_reply_cancel, pattern="^creply_cancel$"),
        ],
        allow_reentry=True, per_message=False)

    # ============ محادثة شحن آسيا سيل ============
    asia_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_asia_auto_start, pattern="^asia_auto$")],
        states={
            ASIA_PHONE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, asia_receive_phone)],
            ASIA_OTP:     [MessageHandler(filters.TEXT & ~filters.COMMAND, asia_receive_otp)],
            ASIA_AMOUNT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, asia_receive_amount)],
            ASIA_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, asia_receive_confirm)],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            CallbackQueryHandler(asia_cancel, pattern="^asia_cancel$"),
        ],
        allow_reentry=True, per_message=False)

    # ============ تسجيل المحادثات ============
    app.add_handler(admin_conv)
    app.add_handler(redeem_conv)
    app.add_handler(complaint_conv)
    app.add_handler(complaint_reply_conv)
    app.add_handler(asia_conv)

    # ============ الأوامر ============
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("myid", cmd_myid))

    # ============ أزرار المستخدم ============
    app.add_handler(CallbackQueryHandler(cb_home, pattern="^home$"))
    app.add_handler(CallbackQueryHandler(cb_check_sub, pattern="^check_sub$"))
    app.add_handler(CallbackQueryHandler(redeem_cancel, pattern="^redeem_cancel$"))
    app.add_handler(CallbackQueryHandler(cb_daily_gift, pattern="^daily_gift$"))
    app.add_handler(CallbackQueryHandler(cb_shop, pattern="^shop$"))
    app.add_handler(CallbackQueryHandler(cb_menu_node, pattern="^mnode_\\d+$"))
    app.add_handler(CallbackQueryHandler(cb_buycat, pattern="^buycat_\\d+$"))
    app.add_handler(CallbackQueryHandler(cb_my_purchases, pattern="^my_purchases$"))
    app.add_handler(CallbackQueryHandler(cb_view_purchase, pattern="^view_\\d+$"))
    app.add_handler(CallbackQueryHandler(cb_getcode, pattern="^getcode_\\d+$"))
    app.add_handler(CallbackQueryHandler(cb_otp, pattern="^otp_\\d+$"))
    app.add_handler(CallbackQueryHandler(cb_kick_session, pattern="^kick_\\d+$"))
    app.add_handler(CallbackQueryHandler(cb_balance, pattern="^balance$"))
    app.add_handler(CallbackQueryHandler(cb_recharge, pattern="^recharge$"))
    app.add_handler(CallbackQueryHandler(complaint_reject, pattern="^creject_\\d+$"))
    app.add_handler(CallbackQueryHandler(asia_cancel, pattern="^asia_cancel$"))

    # ============ معالج الأخطاء ============
    app.add_error_handler(error_handler)

    log.info("🚀 البوت اشتغل...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True,
                    poll_interval=3.0, timeout=60)


if __name__ == "__main__":
    main()