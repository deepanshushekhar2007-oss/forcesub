import asyncio
import json
import os
import re
import time
from datetime import datetime
from flask import Flask
from threading import Thread

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from telethon import TelegramClient
from telethon.sessions import StringSession

from pymongo import MongoClient


# ================= CONFIG =================

TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 6860983540
ALLOWED_GROUP_ID = -1003400610239

OTP_GROUP_LINK = "https://t.me/SPIDYWS_OP"
FORCE_CHANNEL = "@SPIDY_W_S"

# ================= TELETHON =================

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

# ================= MONGODB =================

MONGO_URL = os.getenv("MONGO_URL")

# ================= BOT =================

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

# ================= RUNTIME DATA =================

bot_data = {}

# ================= TELETHON CLIENT =================

telethon_client = TelegramClient(
    StringSession(SESSION_STRING),
    API_ID,
    API_HASH
)

# ================= DATABASE =================

mongo = MongoClient(MONGO_URL)

mongo_db = mongo["otp_bot"]

numbers_db = mongo_db["numbers"]
users_db = mongo_db["users"]


# ================= JSON DB =================

DB_FILE = "bot_db.json"


def load_db():

    if not os.path.exists(DB_FILE):

        return {
            "last_menu": {},
            "countries": {},
            "locked": {},
            "active": {},
            "cooldown": {},
            "manual_mode": True,
            "bot_status": True
        }

    with open(DB_FILE, "r") as f:

        data = json.load(f)

    # ensure keys exist
    data.setdefault("last_menu", {})
    data.setdefault("countries", {})
    data.setdefault("locked", {})
    data.setdefault("active", {})
    data.setdefault("cooldown", {})
    data.setdefault("manual_mode", True)
    data.setdefault("bot_status", True)

    return data


def save_db(data):

    with open(DB_FILE, "w") as f:

        json.dump(data, f, indent=2)


# ================= ADMIN SYSTEM =================

ADMINS = set()

def is_admin(user_id):

    return user_id == OWNER_ID or user_id in ADMINS


# ================= SUBSCRIPTION CHECK =================

async def check_subscription(user_id):

    try:

        member = await bot.get_chat_member(
            FORCE_CHANNEL,
            user_id
        )

        return member.status in [
            "member",
            "administrator",
            "creator"
        ]

    except:

        return False


# ================= BOT STATUS =================

async def check_bot_status(event):

    db = load_db()

    if not db.get("bot_status", True):

        if isinstance(event, Message):

            await event.answer(
                "🚫 <b>Bot is currently disabled by admin.</b>"
            )

        elif isinstance(event, CallbackQuery):

            await event.answer(
                "🚫 Bot is currently disabled.",
                show_alert=True
            )

        return False

    return True

# ---------------- START ----------------

@dp.message(Command("start"))
async def start(message: Message):

    if not await check_bot_status(message):
        return

    user = message.from_user
    user_id = str(user.id)

    # -------- Force Subscribe --------

    is_joined = await check_subscription(user.id)

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
            "🚫 <b>You Must Join Our Channel To Use This Bot</b>\n\n"
            "📢 Join channel then click 'I Joined'",
            reply_markup=kb
        )

    db = load_db()

    # -------- delete old menu --------

    old_menu = db.get("last_menu", {}).get(user_id)

    if old_menu:

        try:
            await bot.delete_message(user.id, old_menu)
        except:
            pass

    username = f"@{user.username}" if user.username else "No Username"

    # -------- Owner Notify --------

    if user.id != OWNER_ID and user.id not in ADMINS:

        await bot.send_message(
            OWNER_ID,
            f"🚀 <b>New User Started</b>\n\n"
            f"👤 {user.full_name}\n"
            f"🆔 <code>{user.id}</code>\n"
            f"📎 {username}\n"
            f"🌐 {user.language_code}\n"
            f"⏰ {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
        )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌍 Choose Your Country",
                    callback_data="select_country"
                )
            ]
        ]
    )

    msg = await message.answer(
    "╔══════════════════════╗\n"
    "   🕷️ <b>Welcome to Spidy OTP</b>\n"
    "╚══════════════════════╝\n\n"
    
    "🔐 <b>Fast & Secure OTP Service</b>\n\n"
    
    "⚡ Instant OTP Delivery\n"
    "🌍 Multiple Countries Available\n"
    "📲 Easy Number Access\n\n"
    
    "🌎 <b>Please select a country below</b> to continue.",
    
        parse_mode="HTML",
        reply_markup=kb
    )
    

    db.setdefault("last_menu", {})[user_id] = msg.message_id

    save_db(db)


# ---------------- ADMIN PANEL ----------------

@dp.message(Command("admin"))
async def admin_panel(message: Message):

    if not is_admin(message.from_user.id):
        return

    db = load_db()

    bot_status = "🟢 ON" if db.get("bot_status", True) else "🔴 OFF"
    otp_mode = "⚡ AUTO" if not db.get("manual_mode", True) else "🔐 MANUAL"

    await message.answer(

        f"<b>👑 ADMIN CONTROL PANEL</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"

        f"📊 <b>Current Status:</b>\n"
        f"• Bot: {bot_status}\n"
        f"• OTP Mode: {otp_mode}\n\n"

        f"⚙ <b>Bot Control:</b>\n"
        f"• /on  → Enable Bot\n"
        f"• /off → Disable Bot\n\n"

        f"🔄 <b>OTP Mode Control:</b>\n"
        f"• /auto     → Enable Auto OTP Mode\n"
        f"• /manually → Enable Manual OTP Mode\n\n"

        f"📌 <b>Number Management:</b>\n"
        f"• /addnumber Country +Number1 +Number2\n"
        f"• /remove Country\n\n"

        f"📊 <b>Monitoring:</b>\n"
        f"• /live → Check Live Stock\n\n"

        f"📢 <b>Messaging:</b>\n"
        f"• /broadcast Your Message\n\n"

        f"💬 <b>OTP System:</b>\n"
        f"• Reply to OTP request to send OTP manually\n\n"

        f"━━━━━━━━━━━━━━━━━━\n"
        f"👑 <i>Admin Access Only</i>"
    )


# ---------------- BOT ON ----------------

@dp.message(Command("on"))
async def bot_on(message: Message):

    if not is_admin(message.from_user.id):
        return

    db = load_db()

    db["bot_status"] = True

    save_db(db)

    await message.answer("✅ Bot Enabled Successfully")


# ---------------- BOT OFF ----------------

@dp.message(Command("off"))
async def bot_off(message: Message):

    if not is_admin(message.from_user.id):
        return

    db = load_db()

    db["bot_status"] = False

    save_db(db)

    await message.answer("⛔ Bot Disabled Successfully")


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

    country = parts[1]

    numbers = re.findall(r"\+?\d{6,15}", message.text)

    added = 0

    # ---------- Numbers from command ----------
    for num in numbers:

        if not numbers_db.find_one({"number": num}):

            numbers_db.insert_one({
                "country": country,
                "number": num
            })

            added += 1

    await message.answer(
        f"✅ {added} Numbers Added in <b>{country}</b>\n\n📄 You can also send TXT file now."
    )

    bot_data["awaiting_file"] = {
        "admin": message.from_user.id,
        "country": country
    }


# ---------------- TXT FILE UPLOAD ----------------

@dp.message(F.document)
async def upload_numbers(message: Message):

    data = bot_data.get("awaiting_file")

    if not data:
        return

    if message.from_user.id not in [data["admin"], OWNER_ID]:
        return

    await message.answer("📂 Processing TXT file...")

    country = data["country"]

    # download file
    file = await bot.get_file(message.document.file_id)
    downloaded = await bot.download_file(file.file_path)

    content = downloaded.read().decode("utf-8", errors="ignore")

    raw_numbers = re.findall(r"\+?\d{6,15}", content)

    if not raw_numbers:
        return await message.answer("❌ No numbers found in file")

    cleaned_numbers = []

    for num in raw_numbers:

        num = num.strip()

        # add + if missing
        if not num.startswith("+"):
            num = "+" + num

        # clean number
        num = "+" + "".join(filter(str.isdigit, num))

        cleaned_numbers.append({
            "country": country,
            "number": num
        })

    added = 0

    try:
        result = numbers_db.insert_many(cleaned_numbers, ordered=False)
        added = len(result.inserted_ids)
    except Exception:
        added = 0

    bot_data["awaiting_file"] = None

    await message.answer(
        f"📄 <b>TXT Upload Completed</b>\n\n"
        f"🌍 Country: <b>{country}</b>\n"
        f"✅ Numbers Uploaded: <b>{added}</b>",
        parse_mode="HTML"
    )

# ---------------- REMOVE COUNTRY ----------------
@dp.message(Command("remove"))
async def remove_country(message: Message):

    if not is_admin(message.from_user.id):
        return

    parts = message.text.split(maxsplit=1)

    if len(parts) != 2:
        return await message.answer(
            "Use:\n/remove Country"
        )

    country = parts[1]

    # MongoDB se delete
    result = numbers_db.delete_many({"country": country})

    if result.deleted_count > 0:

        await message.answer(
            f"🗑 <b>{country}</b> Removed\n\n"
            f"❌ {result.deleted_count} numbers deleted from database"
        )

    else:

        await message.answer("❌ Country Not Found")

# ---------------- SELECT COUNTRY ----------------
@dp.callback_query(F.data == "select_country")
async def select_country(call: CallbackQuery):

    if not await check_bot_status(call):
        return

    countries = numbers_db.distinct("country")

    buttons = [
        [InlineKeyboardButton(
            text=c,
            callback_data=f"country_{c}"
        )]
        for c in countries
    ]

    if not buttons:
        return await call.message.edit_text("❌ No country available")

    await call.message.edit_text(
        "🌍 Select Country",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


# ---------------- GIVE NUMBER ----------------
@dp.callback_query(F.data.startswith("country_"))
async def give_number(call: CallbackQuery):

    if not await check_bot_status(call):
        return

    country = call.data.replace("country_", "")
    user_id = str(call.from_user.id)

    db = load_db()

    # -------- Ensure keys exist --------
    db.setdefault("countries", {})
    db.setdefault("cooldown", {})
    db.setdefault("active", {})
    db.setdefault("locked", {})
    db.setdefault("used_numbers", [])
    db.setdefault("user_history", {})

    numbers = [
        x["number"]
        for x in numbers_db.find({"country": country})
]

    # ❌ No stock
    if not numbers:
        return await call.answer(
            "❌ Out of Stock",
            show_alert=True
        )

    # ⏳ Cooldown
    last = db["cooldown"].get(user_id, 0)

    if time.time() - last < 5:
        return await call.answer(
            "⏳ Please wait 5 seconds",
            show_alert=True
        )

    db["cooldown"][user_id] = time.time()

    # ---------------- REMOVE OLD ACTIVE ----------------

    old = db["active"].get(user_id)

    old_number = None

    if old:

        old_number = old["number"]

        db["locked"].pop(old_number, None)
        db["active"].pop(user_id, None)

    # save user history
        db["user_history"].setdefault(user_id, [])

        if old_number not in db["user_history"][user_id]:
            db["user_history"][user_id].append(old_number)

    # ---------------- AVAILABLE NUMBERS ----------------

    locked = db.get("locked", {})

    user_used = db["user_history"].get(user_id, [])
    used_numbers = db.get("used_numbers", [])

    available = [
        n for n in numbers
        if n not in locked
        and n not in user_used
        and n not in used_numbers
    ]

    if not available:

        save_db(db)

        return await call.answer(
            "❌ All Numbers Locked",
            show_alert=True
        )

    # 🔄 rotation number
    import random

    selected_numbers = random.sample(available,     min(4, len(available)))

    # ---------------- LOCK NUMBER ----------------

    db["active"][user_id] = {
        "numbers": selected_numbers,
        "country": country
    }

    for num in selected_numbers:
        db["locked"][num] = int(user_id)

    save_db(db)

    # ================= BUTTONS =================

    buttons = [

        [
            InlineKeyboardButton(
                text="🔄 Change Numbers",
                callback_data=f"country_{country}"
            )
        ],

        [
            InlineKeyboardButton(
                text="📢 OTP GROUP",
                url=OTP_GROUP_LINK
            )
        ],

        [
            InlineKeyboardButton(
                text="⬅ Back",
                callback_data="select_country"
            )
        ]

    ]

    if db.get("manual_mode", True):

        buttons.insert(
            2,
            [
                InlineKeyboardButton(
                    text="🔐 RECEIVE OTP OF THIS NUMBER",
                    callback_data="send_otp"
                )
            ]
        )

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

# ================= MESSAGE =================

    numbers_text = "\n".join(
        [f"│  <code>{n}</code>  │" for n in     selected_numbers]
    )

    message_text = (

            f"╔══════════════════╗\n"
            f"   ✨ <b>{country} | WhatsApp Secure Portal</b>\n"
            f"╚══════════════════╝\n\n"

            f"📱 <b>Activated Numbers</b>\n"
 
            f"┌──────────────────┐\n"
            f"{numbers_text}\n"
            f"└──────────────────┘\n\n"

            f"📌 <i>Touch & hold any number above to copy it.</i>\n\n"
    )

    if db.get("manual_mode", True):

        message_text += (
            "⏳ Once the verification code is sent,\n"
            "press the button below to access your OTP."
        )    
 
    else:
 
        message_text += (
            "📢 <b>Join OTP Group and check your OTP there.</b>"
        )
 
    try:

        await call.message.edit_text(
            message_text,
            reply_markup=kb
        )

    except:

        await call.message.answer(
            message_text,
            reply_markup=kb
        )
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

    fake_message = Message(
        message_id=call.message.message_id,
        date=call.message.date,
        chat=call.message.chat,
        from_user=call.from_user
    )

    await start(fake_message)

# ---------------- SEND OTP REQUEST ----------------
@dp.callback_query(F.data == "send_otp")
async def send_otp(call: CallbackQuery):

    if not await check_bot_status(call):
        return

    user_id = call.from_user.id
    db = load_db()

    data = db["active"].get(str(user_id))

    if not data:
        return await call.answer(
            "❌ No active number",
            show_alert=True
        )

    try:
        await bot.send_message(
        OWNER_ID,
            f"📥 <b>OTP REQUEST</b>\n\n"
            f"👤 UserID: <code>{user_id}</code>\n"
            f"🌍 {data['country']}\n"
            f"📱 <code>{data['number']}</code>\n\n"
            f"Reply to this message with OTP.",
            parse_mode="HTML"
        )
    except:
        return await call.answer(
            "❌ Failed to send request to admin",
            show_alert=True
        )

    await call.answer(
        "✅ NUMBER ACTIVATED SUCCESSFULLY\n\n"
        "OTP will be forwarded here automatically.\n\n"
        "If you do not receive the OTP within 5 minutes,\n"
        "please try another number.",
        show_alert=True
    )


# ---------------- ADMIN OTP REPLY ----------------
@dp.message(F.reply_to_message)
async def admin_reply(message: Message):

    if message.from_user.id != OWNER_ID:
        return

    text = message.reply_to_message.text or ""

    # Security check
    if "OTP REQUEST" not in text:
        return

    try:
        user_id = int(
            text.split("UserID:")[1]
            .split("\n")[0]
            .replace("<code>", "")
            .replace("</code>", "")
            .strip()
        )
    except:
        return await message.answer("❌ Invalid user id")

    otp = message.text.strip()

    db = load_db()

    data = db["active"].get(str(user_id))

    if not data:
        return await message.answer("❌ User not active")

    number = data["number"]
    country = data["country"]

    try:
        await bot.send_message(
            user_id,
            f"🔐 <b>WHATSAPP OTP</b>\n\n"
            f"🔑 <code>{otp}</code>\n\n"
            f"📱 Number: {number}\n"
            f"🌍 Country: {country}",
            parse_mode="HTML"
        )
    except:
        return await message.answer("❌ Failed to send OTP")

    # remove number after OTP
    if number in db["countries"].get(country, []):
        db["countries"][country].remove(number)

    db["locked"].pop(number, None)
    db["active"].pop(str(user_id), None)

    save_db(db)

    await message.answer("✅ OTP Sent & Number Removed")


# ---------------- AUTO MODE ----------------
@dp.message(Command("auto"))
async def auto_mode(message: Message):

    if message.from_user.id != OWNER_ID:
        return

    db = load_db()
    db["manual_mode"] = False
    save_db(db)

    await message.answer(
        "✅ Auto OTP Mode Enabled\n\n"
        "🔐 Manual Button Removed"
    )


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

    if not db["countries"]:
        return await message.answer("❌ No Countries Added")

    text = "📊 <b>Live Stock Status</b>\n\n"

    for country, numbers in db["countries"].items():

        total = len(numbers)

        locked = sum(
            1 for n in numbers
            if n in db["locked"]
        )

        available = total - locked

        text += (
            f"🌍 <b>{country}</b>\n"
            f"📦 Total: {total}\n"
            f"🔒 Locked: {locked}\n"
            f"✅ Available: {available}\n\n"
        )

    await message.answer(text, parse_mode="HTML")


from telethon import events
import re

# ---------------- GROUP OTP DETECTOR (TELETHON) ----------------
@telethon_client.on(events.NewMessage(chats=ALLOWED_GROUP_ID))
async def stylish_otp_forward(event):

    text = event.raw_text

    if not text:
        return

    db = load_db()

    if not db.get("active"):
        return


    # ---------------- FIND OTP ----------------

    otp = None

    patterns = [
        r"🔑\s*(\d{4,6})",                 # 🔑 123456
        r"OTP[:\s]*([0-9]{4,6})",          # OTP: 123456
        r"code\s*([0-9]{3})[-\s]?([0-9]{3})"   # code 123-456
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            if len(match.groups()) == 2:
                otp = match.group(1) + match.group(2)
            else:
                otp = match.group(1)
            break

    if not otp:
        return


    # ---------------- GET NUMBER LINE ----------------

    number_line = None

    for line in text.splitlines():

        if any(mask in line for mask in ["••", "**", "★★"]):
            number_line = line
            break

    if not number_line:
        return


    digits = "".join(re.findall(r"\d", number_line))

    delivered = 0
    updated = False


    # ---------------- MATCH USERS ----------------

    for user_id, data in list(db["active"].items()):

        number_digits = "".join(re.findall(r"\d", data["number"]))

        first3 = number_digits[:3]
        last3 = number_digits[-3:]

        if digits.startswith(first3) and digits.endswith(last3):

            try:

                await bot.send_message(
                    int(user_id),
                    f"🔐 <b>AUTO OTP RECEIVED</b>\n\n"
                    f"🔑 OTP: <code>{otp}</code>\n"
                    f"📱 Number: {data['number']}\n"
                    f"🌍 Country: {data['country']}",
                    parse_mode="HTML"
                )

                country = data["country"]
                number = data["number"]

                # add to used numbers
                db.setdefault("used_numbers", [])

                if number not in db["used_numbers"]:
                    db["used_numbers"].append(number)

                # remove from stock
                if number in db["countries"].get(country, []):
                    db["countries"][country].remove(number)

                # cleanup
                db["locked"].pop(number, None)
                db["active"].pop(user_id, None)

                delivered += 1
                updated = True

            except Exception as e:
                print("OTP send error:", e)


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
            "Use:\n/broadcast Your message here"
        )

    db = load_db()

    users = set()

    users.update(db.get("active", {}).keys())
    users.update(db.get("cooldown", {}).keys())

    sent = 0
    failed = 0

    for uid in users:

        try:
            await bot.send_message(
                int(uid),
                text,
                parse_mode="HTML"
            )

            sent += 1

            await asyncio.sleep(0.05)

        except Exception:
            failed += 1

    await message.answer(
        f"📢 <b>Broadcast Completed</b>\n\n"
        f"👥 Total Users: {len(users)}\n"
        f"✅ Sent: {sent}\n"
        f"❌ Failed: {failed}",
        parse_mode="HTML"
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
import asyncio
from threading import Thread

async def start_telethon():
    while True:
        try:
            await telethon_client.start()
            print("Telethon Connected ✅")

            await client.run_until_disconnected()

        except Exception as e:
            print("Telethon Error:", e)
            await asyncio.sleep(5)


async def main():

    # webhook remove (conflict fix)
    await bot.delete_webhook(drop_pending_updates=True)

    # telethon background me start
    asyncio.create_task(start_telethon())

    print("Bot Started ✅")

    # bot polling
    await dp.start_polling(bot)


if __name__ == "__main__":

    # render web server
    Thread(target=run_web).start()

    asyncio.run(main())