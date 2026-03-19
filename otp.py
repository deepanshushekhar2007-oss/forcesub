# ================= CORE =================
import asyncio
import json
import os
import re
import time
import random
import logging
from datetime import datetime
from io import BytesIO
from threading import Thread

# ================= FLASK =================
from flask import Flask

# ================= AIOGRAM =================
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ================= TELETHON =================
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# ================= MONGODB =================
from motor.motor_asyncio import AsyncIOMotorClient


# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# ================= SAFE CONFIG =================

def get_env(name, default=None, required=False):
    val = os.getenv(name, default)
    if required and not val:
        raise ValueError(f"❌ Missing ENV: {name}")
    return val


# ================= ENV =================

TOKEN = get_env("BOT_TOKEN", required=True)

OWNER_ID = 6860983540
ALLOWED_GROUP_ID = -1003400610239

OTP_GROUP_LINK = "https://t.me/SPIDYWS_OP"
FORCE_CHANNEL = "@SPIDY_W_S"

API_ID = int(get_env("API_ID", required=True))
API_HASH = get_env("API_HASH", required=True)
SESSION_STRING = get_env("SESSION_STRING", required=True)

MONGO_URL = get_env("MONGO_URL", required=True)


# ================= BOT =================

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()


# ================= TELETHON =================

telethon_client = TelegramClient(
    StringSession(SESSION_STRING),
    API_ID,
    API_HASH
)


# ================= MONGODB =================

mongo = AsyncIOMotorClient(MONGO_URL)

mongo_db = mongo["otp_bot"]

numbers_db = mongo_db["numbers"]
users_db = mongo_db["users"]
settings_db = mongo_db["settings"]


# ================= STARTUP CHECK =================

async def check_connections():
    try:
        await mongo.server_info()
        logging.info("✅ MongoDB Connected")

        await telethon_client.connect()
        if not await telethon_client.is_user_authorized():
            logging.error("❌ Telethon not authorized (SESSION_STRING issue)")
        else:
            logging.info("✅ Telethon Ready")

    except Exception as e:
        logging.error(f"Startup Error: {e}")

# ================= JSON DB (SAFE) =================

DB_FILE = "bot_db.json"


def load_db():
    try:
        if not os.path.exists(DB_FILE):
            return default_db()

        with open(DB_FILE, "r") as f:
            data = json.load(f)

        return merge_defaults(data)

    except Exception as e:
        print("DB Load Error:", e)
        return default_db()


def save_db(data):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print("DB Save Error:", e)


def default_db():
    return {
        "last_menu": {},
        "countries": {},
        "locked": {},
        "active": {},
        "cooldown": {},
        "manual_mode": True,
        "bot_status": True,
        "used_numbers": [],
        "user_history": {}
    }


def merge_defaults(data):
    defaults = default_db()
    for k, v in defaults.items():
        data.setdefault(k, v)
    return data


# ================= ADMIN =================

ADMINS = set()


def is_admin(user_id: int):
    return user_id == OWNER_ID or user_id in ADMINS


# ================= SUB CHECK =================

async def check_subscription(user_id: int):
    try:
        member = await bot.get_chat_member(FORCE_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print("Sub Check Error:", e)
        return False

async def send_safe(uid, text):
    try:
        await bot.send_message(uid, text)
        return True
    except Exception:
        return False
# ================= BOT STATUS =================

async def check_bot_status(event):

    try:
        settings = await settings_db.find_one({"_id": "bot"})
    except Exception as e:
        print("DB Error:", e)
        return True  # fail-safe

    if settings and not settings.get("bot_status", True):

        if isinstance(event, Message):
            await event.answer("🚫 <b>Bot is currently disabled by admin.</b>")

        elif isinstance(event, CallbackQuery):
            await event.answer("🚫 Bot is disabled.", show_alert=True)

        return False

    return True

# ---------------- START ----------------

@dp.message(Command("start"))
async def start(message: Message):

    if not await check_bot_status(message):
        return

    user = message.from_user
    user_id = str(user.id)

    # ================= SAVE USER =================
    try:
        await users_db.update_one(
            {"user_id": user_id},
            {
                "$setOnInsert": {
                    "user_id": user_id,
                    "name": user.full_name,
                    "username": user.username,
                    "joined": datetime.now()
                }
            },
            upsert=True
        )
    except Exception as e:
        print("User Save Error:", e)

    # ================= FORCE SUB =================
    try:
        is_joined = await check_subscription(user.id)
    except:
        is_joined = True  # fail safe

    if not is_joined:

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📢 Join Channel",
                        url=f"https://t.me/{FORCE_CHANNEL.replace('@','')}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="✅ I Joined",
                        callback_data="check_join"
                    )
                ]
            ]
        )

        return await message.answer(
            "🚫 <b>Access Denied</b>\n\n"
            "📢 Please join our channel to continue.\n"
            "Then click <b>I Joined</b> ✅",
            reply_markup=kb
        )

    # ================= DELETE OLD MENU =================
    try:
        user_data = await users_db.find_one({"user_id": user_id})

        if user_data and user_data.get("last_menu"):
            await bot.delete_message(user.id, user_data["last_menu"])
    except:
        pass

    # ================= OWNER NOTIFY (ONLY FIRST TIME) =================
    try:
        exists = await users_db.find_one({"user_id": user_id, "notified": True})

        if not exists and not is_admin(user.id):

            await bot.send_message(
                OWNER_ID,
                f"🚀 <b>New User Started</b>\n\n"
                f"👤 {user.full_name}\n"
                f"🆔 <code>{user.id}</code>\n"
                f"📎 @{user.username if user.username else 'No Username'}\n"
                f"⏰ {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
            )

            await users_db.update_one(
                {"user_id": user_id},
                {"$set": {"notified": True}}
            )

    except Exception as e:
        print("Notify Error:", e)

    # ================= PREMIUM UI =================

    text = (
        "╔═══❖•ೋ° 🕷️ °ೋ•❖═══╗\n"
        "   <b>SPIDY OTP SYSTEM</b>\n"
        "╚═══❖•ೋ° 🕷️ °ೋ•❖═══╝\n\n"

        "🔐 <b>Secure OTP Service</b>\n"
        "⚡ Instant OTP Delivery\n"
        "🌍 Multi Country Support\n"
        "📱 Real-Time Numbers\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "🎯 <b>Select your country below</b>\n"
        "━━━━━━━━━━━━━━━━━━"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌍 Select Country",
                    callback_data="select_country"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Live Stock",
                    callback_data="live_stock"
                ),
                InlineKeyboardButton(
                    text="ℹ️ Help",
                    callback_data="help"
                )
            ]
        ]
    )

    msg = await message.answer(text, reply_markup=kb)

    # ================= SAVE LAST MENU =================
    try:
        await users_db.update_one(
            {"user_id": user_id},
            {"$set": {"last_menu": msg.message_id}},
            upsert=True
        )
    except:
        pass



@dp.callback_query(F.data == "live_stock")
async def live_stock_callback(call: CallbackQuery):

    if not await check_bot_status(call):
        return

    await call.answer()

    db = load_db()

    countries = await numbers_db.distinct("country")

    if not countries:
        return await call.message.edit_text("❌ <b>No Countries Available</b>")

    text = (
        "╔═══❖•ೋ° 📊 °ೋ•❖═══╗\n"
        "   <b>LIVE STOCK DASHBOARD</b>\n"
        "╚═══❖•ೋ° 📊 °ೋ•❖═══╝\n\n"
    )

    total_numbers = 0
    total_locked = 0

    locked_numbers = db.get("locked", {})

    for country in countries:

        total = await numbers_db.count_documents({"country": country})

        locked = 0

        for number in locked_numbers:
            doc = await numbers_db.find_one({"number": number})
            if doc and doc.get("country") == country:
                locked += 1

        available = total - locked

        total_numbers += total
        total_locked += locked

        text += (
            f"🌍 <b>{country}</b>\n"
            f"┣ 📦 Total     : <b>{total}</b>\n"
            f"┣ 🔒 Locked    : <b>{locked}</b>\n"
            f"┗ ✅ Available : <b>{available}</b>\n\n"
        )

    text += "━━━━━━━━━━━━━━━━━━\n"

    text += (
        f"📊 <b>OVERALL STATUS</b>\n\n"
        f"┣ 📦 Total     : <b>{total_numbers}</b>\n"
        f"┣ 🔒 Locked    : <b>{total_locked}</b>\n"
        f"┗ ✅ Available : <b>{total_numbers - total_locked}</b>\n"
    )

    # 🔥 BUTTONS
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Refresh",
                    callback_data="live_stock"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅ Back",
                    callback_data="select_country"
                )
            ]
        ]
    )

    await call.message.edit_text(text, reply_markup=kb)
    
    
@dp.callback_query(F.data == "help")
async def help_callback(call: CallbackQuery):

    await call.answer()

    text = (
        "╔═══❖•ೋ° ℹ️ °ೋ•❖═══╗\n"
        "     <b>HELP PANEL</b>\n"
        "╚═══❖•ೋ° ℹ️ °ೋ•❖═══╝\n\n"

        "📌 <b>How To Use:</b>\n"
        "1️⃣ Select your country 🌍\n"
        "2️⃣ Copy any number 📱\n"
        "3️⃣ Use it for OTP\n"
        "4️⃣ Receive OTP instantly 🔐\n\n"

        "⚡ <b>Features:</b>\n"
        "• Instant OTP\n"
        "• Auto detection\n"
        "• Multi-country support\n\n"

        "👑 <b>Owner:</b>\n"
        "👉 @SPIDYWS\n\n"

        "⚠️ <i>Note:</i>\n"
        "Use numbers quickly before expiry"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👑 Contact Owner",
                    url="https://t.me/SPIDYWS"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅ Back",
                    callback_data="select_country"
                )
            ]
        ]
    )

    await call.message.edit_text(text, reply_markup=kb)
# ---------------- ADMIN PANEL ----------------

@dp.message(Command("admin"))
async def admin_panel(message: Message):

    if not is_admin(message.from_user.id):
        return

    try:
        settings = await settings_db.find_one({"_id": "bot"}) or {}
    except:
        settings = {}

    bot_status = "🟢 ONLINE" if settings.get("bot_status", True) else "🔴 OFFLINE"
    manual_mode = settings.get("manual_mode", True)
    otp_mode = "⚡ AUTO OTP" if not manual_mode else "🔐 MANUAL OTP"

    text = (
        "╔══════════════════════╗\n"
        "     👑 <b>ADMIN CONTROL PANEL</b>\n"
        "╚══════════════════════╝\n\n"

        f"📊 <b>System Status</b>\n"
        f"• Bot Status : {bot_status}\n"
        f"• OTP Mode   : {otp_mode}\n\n"

        "━━━━━━━━━━━━━━━━━━\n"

        "⚙ <b>Bot Controls</b>\n"
        "• /on  - Enable Bot\n"
        "• /off - Disable Bot\n\n"

        "🔄 <b>OTP Mode</b>\n"
        "• /auto     - Enable Auto OTP\n"
        "• /manually - Enable Manual OTP\n\n"

        "📌 <b>Number Management</b>\n"
        "• /addnumber Country +Number1 +Number2\n"
        "• /remove Country\n\n"

        "📊 <b>Monitoring</b>\n"
        "• /live - Check Live Numbers\n\n"

        "📢 <b>Messaging</b>\n"
        "• /broadcast Your Message\n\n"

        "💬 <b>Manual OTP</b>\n"
        "• Reply to OTP request to send OTP\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "👑 <i>Admin Access Only</i>"
    )

    await message.answer(text)


# ---------------- BOT ON ----------------

@dp.message(Command("on"))
async def bot_on(message: Message):

    if not is_admin(message.from_user.id):
        return

    try:
        await settings_db.update_one(
            {"_id": "bot"},
            {"$set": {"bot_status": True}},
            upsert=True
        )
        await message.answer("✅ Bot Enabled Successfully")
    except:
        await message.answer("❌ DB Error")


# ---------------- BOT OFF ----------------

@dp.message(Command("off"))
async def bot_off(message: Message):

    if not is_admin(message.from_user.id):
        return

    try:
        await settings_db.update_one(
            {"_id": "bot"},
            {"$set": {"bot_status": False}},
            upsert=True
        )
        await message.answer("⛔ Bot Disabled Successfully")
    except:
        await message.answer("❌ DB Error")


# ---------------- ADD NUMBER ----------------

@dp.message(Command("addnumber"))
async def add_number(message: Message):

    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()

    if len(parts) < 2:
        return await message.answer(
            "Use:\n/addnumber Country +Number1 +Number2\nOR\n/addnumber Country then send TXT file"
        )

    country = parts[1].lower().strip()

    raw_numbers = re.findall(r"\+?\d{6,15}", message.text)

    docs = []
    seen = set()

    for num in raw_numbers:

        num = "+" + "".join(filter(str.isdigit, num))

        if num in seen:
            continue

        seen.add(num)

        docs.append({
            "country": country,
            "number": num
        })

    added = 0

    if docs:
        try:
            result = await numbers_db.insert_many(docs, ordered=False)
            added = len(result.inserted_ids)
        except Exception as e:
            print("Insert Error:", e)

    await message.answer(
        f"✅ {added} Numbers Added in <b>{country.upper()}</b>\n\n📄 Send TXT file now."
    )

    # safer than global overwrite
    bot_data["awaiting_file"] = {
        str(message.from_user.id): country
    }


# ---------------- TXT FILE UPLOAD ----------------

@dp.message(F.document)
async def upload_numbers(message: Message):

    user_id = str(message.from_user.id)

    data = bot_data.get("awaiting_file", {}).get(user_id)

    if not data:
        return

    processing = await message.answer("📂 Processing TXT file...")

    country = data

    try:

        file = await bot.get_file(message.document.file_id)

        file_bytes = BytesIO()
        await bot.download_file(file.file_path, file_bytes)

        content = file_bytes.getvalue().decode("utf-8", errors="ignore")

        raw_numbers = re.findall(r"\+?\d{6,15}", content)

        if not raw_numbers:
            await processing.delete()
            return await message.answer("❌ No numbers found")

        docs = []
        seen = set()

        for num in raw_numbers:

            num = "+" + "".join(filter(str.isdigit, num))

            if num in seen:
                continue

            seen.add(num)

            docs.append({
                "country": country,
                "number": num
            })

        added = 0

        if docs:
            try:
                result = await numbers_db.insert_many(docs, ordered=False)
                added = len(result.inserted_ids)
            except Exception as e:
                print("Insert Error:", e)

        # clear user state
        bot_data["awaiting_file"].pop(user_id, None)

        await processing.delete()

        await message.answer(
            f"📄 <b>Upload Done</b>\n\n"
            f"🌍 Country: <b>{country.upper()}</b>\n"
            f"📥 Found: <b>{len(raw_numbers)}</b>\n"
            f"✅ Added: <b>{added}</b>"
        )

    except Exception as e:

        await processing.delete()
        print("TXT Error:", e)

        await message.answer("❌ File processing failed")


# ---------------- REMOVE COUNTRY ----------------

@dp.message(Command("remove"))
async def remove_country(message: Message):

    if not is_admin(message.from_user.id):
        return

    try:
        countries = await numbers_db.distinct("country")
    except:
        return await message.answer("❌ DB Error")

    if not countries:
        return await message.answer("❌ No Countries Available")

    buttons = [
        [InlineKeyboardButton(
            text=f"🗑 {c.upper()}",
            callback_data=f"remove_country_{c}"
        )]
        for c in countries
    ]

    buttons.append([
        InlineKeyboardButton(
            text="❌ Cancel",
            callback_data="cancel_remove_country"
        )
    ])

    await message.answer(
        "🌍 <b>Select Country To Remove</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@dp.callback_query(F.data.startswith("remove_country_"))
async def confirm_remove_country(call: CallbackQuery):

    if not is_admin(call.from_user.id):
        return

    country = call.data.replace("remove_country_", "")

    try:
        result = await numbers_db.delete_many({"country": country})
    except:
        return await call.message.edit_text("❌ DB Error")

    if result.deleted_count > 0:

        await call.message.edit_text(
            f"🗑 <b>{country.upper()}</b> Removed\n\n"
            f"❌ {result.deleted_count} numbers deleted"
        )

    else:

        await call.message.edit_text("❌ Country Not Found")


@dp.callback_query(F.data == "cancel_remove_country")
async def cancel_remove_country(call: CallbackQuery):

    if not is_admin(call.from_user.id):
        return

    await call.message.edit_text("❌ Cancelled")


@dp.callback_query(F.data == "go_home")
async def go_home(call: CallbackQuery):

    await call.answer()

    try:
        await start(call.message)
    except:
        pass
# ---------------- SELECT COUNTRY ----------------
@dp.callback_query(F.data == "select_country")
async def select_country(call: CallbackQuery):

    await call.answer()

    if not await check_bot_status(call):
        return

    try:
        countries = await numbers_db.distinct("country")
    except Exception as e:
        print("Country Fetch Error:", e)
        return await call.message.edit_text("❌ DB Error")

    if not countries:
        return await call.message.edit_text("❌ <b>No Countries Available</b>")

    buttons = [
        [
            InlineKeyboardButton(
                text=c.upper(),
                callback_data=f"country_{c}"
            )
        ]
        for c in sorted(countries)
    ]

    # 🔥 ONLY BACK BUTTON ADD
    buttons.append([
        InlineKeyboardButton(
            text="⬅ Back",
            callback_data="go_home"
        )
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await call.message.edit_text(
        "🌍 <b>Select Your Country</b>",
        reply_markup=kb
    )


# ---------------- GIVE NUMBER ----------------
@dp.callback_query(F.data.startswith("country_"))
async def give_number(call: CallbackQuery):

    if not await check_bot_status(call):
        return

    await call.answer()

    country = call.data.replace("country_", "")
    user_id = str(call.from_user.id)

    db = load_db()

    db.setdefault("cooldown", {})
    db.setdefault("active", {})
    db.setdefault("locked", {})
    db.setdefault("used_numbers", [])
    db.setdefault("user_history", {})

    # ---------- Cooldown ----------
    last = db["cooldown"].get(user_id, 0)

    if time.time() - last < 5:
        wait = int(5 - (time.time() - last))
        return await call.answer(f"⏳ Wait {wait}s", show_alert=True)

    db["cooldown"][user_id] = time.time()

    # ---------- Remove old ----------
    if user_id in db["active"]:

        old_numbers = db["active"][user_id]["numbers"]

        for num in old_numbers:
            db["locked"].pop(num, None)

            db["user_history"].setdefault(user_id, [])
            if num not in db["user_history"][user_id]:
                db["user_history"][user_id].append(num)

        db["active"].pop(user_id, None)

    # ---------- FETCH ----------
    try:
        cursor = numbers_db.find({"country": country}).limit(100)
        numbers = [doc["number"] async for doc in cursor if doc.get("number")]
    except Exception as e:
        print("DB Fetch Error:", e)
        return await call.answer("❌ DB Error", show_alert=True)

    if not numbers:
        return await call.answer("❌ Out of Stock", show_alert=True)

    # ---------- FILTER ----------
    locked = db["locked"]
    used = db["used_numbers"]
    history = db["user_history"].get(user_id, [])

    available = [
        n for n in numbers
        if n not in locked
        and n not in used
        and n not in history
    ]

    if not available:
        save_db(db)
        return await call.answer("❌ All Numbers Used", show_alert=True)

    # ---------- SELECT ----------
    selected_numbers = available[:min(4, len(available))]

    db["active"][user_id] = {
        "numbers": selected_numbers,
        "country": country,
        "time": time.time()
    }

    for num in selected_numbers:
        db["locked"][num] = user_id

    save_db(db)

    # ================= BUTTONS =================

    buttons = [
        [
            InlineKeyboardButton("🔄 Change", callback_data=f"country_{country}"),
            InlineKeyboardButton("📢 Group", url=OTP_GROUP_LINK)
        ],
        [
            InlineKeyboardButton("⬅ Back", callback_data="select_country")
        ]
    ]

    if db.get("manual_mode", True):
        buttons.insert(
            1,
            [InlineKeyboardButton("🔐 Get OTP", callback_data="send_otp")]
        )

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # ================= MESSAGE =================

    numbers_text = "\n".join(
        [f"{i+1}. <code>{n}</code>" for i, n in enumerate(selected_numbers)]
    )

    message_text = (
        f"╔═══❖•ೋ° 📲 °ೋ•❖═══╗\n"
        f"   <b>{country.upper()} PANEL</b>\n"
        f"╚═══❖•ೋ° 📲 °ೋ•❖═══╝\n\n"

        f"📱 <b>Your Numbers:</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{numbers_text}\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"

        f"⏱ <b>Expiry:</b> 2-5 min\n"
        f"📌 <i>Copy & use fast</i>\n\n"
    )

    if db.get("manual_mode", True):
        message_text += "🔐 Tap <b>Get OTP</b> after sending code"
    else:
        message_text += "📢 Check OTP in group"

    try:
        await call.message.edit_text(message_text, reply_markup=kb)
    except:
        await call.message.answer(message_text, reply_markup=kb)
        
# ---------------- CHECK JOIN ----------------
@dp.callback_query(F.data == "check_join")
async def check_join_callback(call: CallbackQuery):

    is_joined = await check_subscription(call.from_user.id)

    if not is_joined:
        return await call.answer(
            "❌ You Still Haven't Joined The Channel",
            show_alert=True
        )

    await call.message.delete()
    await start(call.message)


# ---------------- SEND OTP REQUEST ----------------
@dp.callback_query(F.data == "send_otp")
async def send_otp(call: CallbackQuery):

    if not await check_bot_status(call):
        return

    user_id = str(call.from_user.id)
    db = load_db()

    data = db.get("active", {}).get(user_id)

    if not data:
        return await call.answer("❌ No active number", show_alert=True)

    number = data["numbers"][0]
    country = data["country"]

    try:
        msg = await bot.send_message(
            OWNER_ID,
            f"📥 <b>OTP REQUEST</b>\n\n"
            f"👤 UserID: <code>{user_id}</code>\n"
            f"🌍 {country}\n"
            f"📱 <code>{number}</code>\n\n"
            f"Reply with OTP."
        )
    except:
        return await call.answer(
            "❌ Failed to send request",
            show_alert=True
        )

    await call.answer(
        "✅ Request sent to admin.\nOTP will come here.",
        show_alert=True
    )


# ---------------- CHANGE NUMBER ----------------
@dp.callback_query(F.data == "change_number")
async def change_number(call: CallbackQuery):

    user_id = str(call.from_user.id)
    db = load_db()

    data = db.get("active", {}).get(user_id)

    if not data:
        return await call.answer("❌ No active number", show_alert=True)

    numbers = data.get("numbers", [])

    for number in numbers:
        db.get("locked", {}).pop(number, None)

        db.setdefault("used_numbers", [])

        if number not in db["used_numbers"]:
            db["used_numbers"].append(number)

    db["active"].pop(user_id, None)

    save_db(db)

    await call.answer("♻ Number Changed")

    try:
        await start(call.message)
    except:
        pass


# ---------------- ADMIN OTP REPLY ----------------
@dp.message(F.reply_to_message)
async def admin_reply(message: Message):

    if message.from_user.id != OWNER_ID:
        return

    text = message.reply_to_message.text or ""

    if "OTP REQUEST" not in text:
        return

    try:
        user_id = text.split("UserID:")[1].split("\n")[0]
        user_id = user_id.replace("<code>", "").replace("</code>", "").strip()
    except:
        return await message.answer("❌ Invalid request")

    otp = message.text.strip()

    db = load_db()

    data = db.get("active", {}).get(user_id)

    if not data:
        return await message.answer("❌ User not active")

    number = data["numbers"][0]
    country = data["country"]

    try:
        await bot.send_message(
            int(user_id),
            f"🔐 <b>WHATSAPP OTP</b>\n\n"
            f"🔑 <code>{otp}</code>\n\n"
            f"📱 {number}\n"
            f"🌍 {country}"
        )
    except:
        return await message.answer("❌ Failed to send OTP")

    db["locked"].pop(number, None)
    db["active"].pop(user_id, None)

    save_db(db)

    await message.answer("✅ OTP Sent")


# ---------------- AUTO MODE ----------------
@dp.message(Command("auto"))
async def auto_mode(message: Message):

    if message.from_user.id != OWNER_ID:
        return

    db = load_db()
    db["manual_mode"] = False
    save_db(db)

    await message.answer("✅ Auto Mode Enabled")


# ---------------- MANUAL MODE ----------------
@dp.message(Command("manually"))
async def manual_mode(message: Message):

    if message.from_user.id != OWNER_ID:
        return

    db = load_db()
    db["manual_mode"] = True
    save_db(db)

    await message.answer(
        "✅ Manual OTP Mode Enabled\n\n"
        "🔐 Button Restored"
    )


# ---------------- LIVE STOCK ----------------
@dp.message(Command("live"))
async def live_stock(message: Message):

    if message.from_user.id != OWNER_ID:
        return

    db = load_db()

    try:
        countries = await numbers_db.distinct("country")
    except:
        return await message.answer("❌ DB Error")

    if not countries:
        return await message.answer("❌ No Countries Added")

    locked_numbers = set(db.get("locked", {}).keys())

    text = "📊 <b>LIVE STOCK DASHBOARD</b>\n"
    text += "━━━━━━━━━━━━━━━━━━\n\n"

    total_numbers = 0
    total_locked = 0

    for country in countries:

        # 🔥 fast count
        total = await numbers_db.count_documents({"country": country})

        # 🔥 get all numbers of country once
        cursor = numbers_db.find({"country": country}, {"number": 1})

        country_numbers = set()
        async for doc in cursor:
            if doc.get("number"):
                country_numbers.add(doc["number"])

        # 🔥 intersection (FAST)
        locked = len(country_numbers & locked_numbers)

        available = total - locked

        total_numbers += total
        total_locked += locked

        text += (
            f"🌍 <b>{country.upper()}</b>\n"
            f"   📦 Total: <b>{total}</b>\n"
            f"   🔒 Locked: <b>{locked}</b>\n"
            f"   ✅ Available: <b>{available}</b>\n\n"
        )

    text += "━━━━━━━━━━━━━━━━━━\n"
    text += (
        f"📦 <b>Total Numbers:</b> {total_numbers}\n"
        f"🔒 <b>Total Locked:</b> {total_locked}\n"
        f"✅ <b>Total Available:</b> {total_numbers - total_locked}"
    )

    await message.answer(text)

# ---------------- GROUP OTP DETECTOR (TELETHON) ----------------
@telethon_client.on(events.NewMessage(chats=ALLOWED_GROUP_ID))
async def stylish_otp_forward(event):

    text = event.raw_text

    if not text:
        return

    db = load_db()

    if not db.get("active"):
        return

    delivered = 0
    updated = False

    # 🔥 SPLIT MESSAGE INTO BLOCKS
    blocks = text.split("\n\n")

    for block in blocks:

        # ---------------- FIND OTP ----------------
        otp = None

        patterns = [
            r"(?:otp|code|pin)[^\d]{0,10}(\d{3})[-\s]?(\d{3})",
            r"(?:otp|code|pin)[^\d]{0,10}(\d{4,6})",
            r"\b(\d{3})[-\s](\d{3})\b",
            r"\b(\d{6})\b"
        ]

        for pattern in patterns:
            match = re.search(pattern, block, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    otp = match.group(1) + match.group(2)
                else:
                    otp = match.group(1)
                break

        if not otp:
            continue

        # ---------------- FIND NUMBER CANDIDATES ----------------
        number_candidates = []

        for line in block.splitlines():

            l = line.lower()

            if any(x in l for x in ["••", "**", "★★", "xxx", "num", "📱"]):

                digits = "".join(re.findall(r"\d", line))

                if len(digits) >= 6:
                    number_candidates.append(digits)

        if not number_candidates:
            continue

        # ---------------- MATCH USERS ----------------
        for user_id, data in list(db["active"].items()):

            numbers = data.get("numbers", [])
            country = data.get("country")

            matched = False

            for number in numbers:

                number_digits = "".join(re.findall(r"\d", number))

                start = number_digits[:3]
                end3 = number_digits[-3:]
                end2 = number_digits[-2:]

                best_score = 0

                for candidate in number_candidates:

                    score = 0

                    # 🔥 START MATCH
                    if candidate.startswith(start):
                        score += 40

                    # 🔥 END MATCH
                    if candidate.endswith(end3):
                        score += 50
                    elif candidate.endswith(end2):
                        score += 30

                    # 🔥 EXTRA
                    if start in candidate:
                        score += 10

                    best_score = max(best_score, score)

                # 🔥 FINAL MATCH
                if best_score >= 60:

                    try:
                        await bot.send_message(
                            int(user_id),
                            f"╔═══❖•ೋ° 🔐 °ೋ•❖═══╗\n"
                            f"     <b>OTP RECEIVED</b>\n"
                            f"╚═══❖•ೋ° 🔐 °ೋ•❖═══╝\n\n"

                            f"🔑 <b>Verification Code</b>\n"
                            f"┌──────────────────┐\n"
                            f"   <code>{otp}</code>\n"
                            f"└──────────────────┘\n\n"

                            f"📱 <b>Number:</b> <code>{number}</code>\n"
                            f"🌍 <b>Country:</b> <b>{country}</b>\n\n"

                            f"⚡ <i>Use quickly before expiry</i>",
                            parse_mode="HTML"
                        )

                        # -------- CLEANUP --------
                        db.setdefault("used_numbers", [])

                        if number not in db["used_numbers"]:
                            db["used_numbers"].append(number)

                        db["locked"].pop(number, None)

                        delivered += 1
                        updated = True
                        matched = True

                    except Exception as e:
                        print("OTP send error:", e)

                    break  # stop checking more numbers

            # 🔥 remove user only if matched
            if matched:
                db["active"].pop(user_id, None)



    # ---------------- SAVE DB ----------------

    if updated:
        save_db(db)

    if delivered == 0:
        print("⚠ No OTP matched")

# ---------------- BROADCAST ----------------
@dp.message(Command("broadcast"))
async def broadcast(message: Message):

    if message.from_user.id != OWNER_ID:
        return

    text = message.text.replace("/broadcast", "").strip()

    if not text:
        return await message.answer(
            "⚠️ Usage:\n/broadcast your message"
        )

    users = []

    async for user in users_db.find({}, {"user_id": 1}):
        if "user_id" in user:
            users.append(user["user_id"])

    if not users:
        return await message.answer("❌ No users found")

    sent = 0
    failed = 0

    start_msg = await message.answer(
        f"📢 Broadcast Started\n👥 Users: {len(users)}"
    )

    # 🔥 batch system (anti flood)
    batch_size = 25

    for i in range(0, len(users), batch_size):

        batch = users[i:i + batch_size]

        tasks = []

        for uid in batch:
            tasks.append(send_safe(uid, text))

        results = await asyncio.gather(*tasks)

        for r in results:
            if r:
                sent += 1
            else:
                failed += 1

        await asyncio.sleep(1)  # 🔥 anti-ban delay

    await start_msg.edit_text(
        f"📢 <b>BROADCAST REPORT</b>\n\n"
        f"👥 Total: {len(users)}\n"
        f"✅ Sent: {sent}\n"
        f"❌ Failed: {failed}"
    )

# ---------------- WEB SERVER ----------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running successfully!"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)


# ---------------- TELETHON AUTO CONNECT ----------------

async def start_telethon():

    while True:

        try:

            await telethon_client.start()

            print("Telethon Connected ✅")

            await telethon_client.run_until_disconnected()

        except Exception as e:

            print("Telethon Error:", e)

            await asyncio.sleep(5)


async def main():

    # ✅ CONNECTION CHECK (YAHI LAGANA HAI)
    await check_connections()

    # create index
    await numbers_db.create_index("number", unique=True)

    await bot.delete_webhook(drop_pending_updates=True)

    asyncio.create_task(start_telethon())

    print("Bot Started ✅")

    await dp.start_polling(bot)
    

if __name__ == "__main__":

    Thread(target=run_web).start()

    asyncio.run(main())