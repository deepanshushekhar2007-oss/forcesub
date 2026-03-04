import asyncio
import json
import os
import re
import time
from datetime import datetime
from flask import Flask
from threading import Thread
import os

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

TOKEN = "8602466322:AAEIiEnCneUaYPj-QxXmyFEH31A4T9PfQuQ"
ADMIN_ID = 6860983540
ALLOWED_GROUP_ID = -1003400610239   # Yaha apna real group ID daalo

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

DB_FILE = "numbers.json"

# ---------------- DATABASE ----------------
def load_db():
    if not os.path.exists(DB_FILE):
        data = {
            "countries": {},
            "active": {},
            "locked": {},
            "cooldown": {},
            "last_menu": {},
            "bot_status": True,
            "manual_mode": True
        }
        save_db(data)
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)
        
      
        
          
            
                
async def check_bot_status(event):
    db = load_db()
    if not db.get("bot_status", True):
        if isinstance(event, Message):
            await event.answer("🚫 <b>Bot is currently disabled by admin.</b>")
        elif isinstance(event, CallbackQuery):
            await event.answer("🚫 Bot is currently disabled.", show_alert=True)
        return False
    return True

# ---------------- START ----------------
@dp.message(Command("start"))
async def start(message: Message):
    if not await check_bot_status(message):
        return
    user = message.from_user
    user_id = str(user.id)

    db = load_db()

    # delete old menu
    old_menu = db["last_menu"].get(user_id)
    if old_menu:
        try:
            await bot.delete_message(user.id, old_menu)
        except:
            pass

    # admin notify
    await bot.send_message(
        ADMIN_ID,
        f"🚀 <b>New User Started</b>\n\n"
        f"👤 {user.full_name}\n"
        f"🆔 <code>{user.id}</code>\n"
        f"📎 @{user.username}\n"
        f"🌐 {user.language_code}\n"
        f"⏰ {datetime.now()}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌍 Select Country", callback_data="select_country")]
    ])

    msg = await message.answer("👋 Welcome\nSelect Country", reply_markup=kb)

    db["last_menu"][user_id] = msg.message_id
    save_db(db)
    
    
    

 
 


# ---------------- ADMIN PANEL ----------------
# ---------------- ADMIN PANEL ----------------
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
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
        f"• /live  → Check Live Stock\n\n"

        f"📢 <b>Messaging:</b>\n"
        f"• /broadcast Your Message\n\n"

        f"💬 <b>OTP System:</b>\n"
        f"• Reply to OTP request to send OTP manually\n\n"

        f"━━━━━━━━━━━━━━━━━━\n"
        f"👑 <i>Admin Access Only</i>"
    )


@dp.message(Command("on"))
async def bot_on(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    db = load_db()
    db["bot_status"] = True
    save_db(db)
    await message.answer("✅ Bot Enabled Successfully")



@dp.message(Command("off"))
async def bot_off(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    db = load_db()
    db["bot_status"] = False
    save_db(db)
    await message.answer("⛔ Bot Disabled Successfully")

# ---------------- ADD NUMBER ----------------
@dp.message(Command("addnumber"))
async def add_number(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()
    if len(parts) < 2:
        return await message.answer("Use:\n/addnumber Country +Number")

    country = parts[1]
    numbers = re.findall(r"\+?\d{6,15}", message.text)

    if not numbers:
        return await message.answer("❌ No valid numbers")

    db = load_db()
    db["countries"].setdefault(country, [])

    added = 0
    for num in numbers:
        if num not in db["countries"][country]:
            db["countries"][country].append(num)
            added += 1

    save_db(db)
    await message.answer(f"✅ {added} Numbers Added in {country}")

# ---------------- REMOVE COUNTRY ----------------
@dp.message(Command("remove"))
async def remove_country(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        return await message.answer("Use:\n/remove Country")

    country = parts[1]
    db = load_db()

    if country in db["countries"]:
        del db["countries"][country]
        save_db(db)
        await message.answer(f"🗑 {country} Removed")
    else:
        await message.answer("❌ Country Not Found")

# ---------------- SELECT COUNTRY ----------------
@dp.callback_query(F.data == "select_country")
async def select_country(call: CallbackQuery):
    if not await check_bot_status(call):
        return
    db = load_db()

    buttons = [
        [InlineKeyboardButton(text=c, callback_data=f"country_{c}")]
        for c in db["countries"]
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
    numbers = db["countries"].get(country, [])

    # ❌ No stock
    if not numbers:
        return await call.answer("❌ Out of Stock", show_alert=True)

    # ⏳ Cooldown 5 seconds
    last = db["cooldown"].get(user_id, 0)
    if time.time() - last < 5:
        return await call.answer("⏳ Please wait 5 seconds", show_alert=True)

    db["cooldown"][user_id] = time.time()

    # ❌ Remove old number permanently if exists
    old = db["active"].get(user_id)
    if old:
        old_number = old["number"]
        old_country = old["country"]

        # Remove from country stock permanently
        if old_number in db["countries"].get(old_country, []):
            db["countries"][old_country].remove(old_number)

        # Remove from locked list
        db["locked"].pop(old_number, None)

        # Remove from active
        db["active"].pop(user_id, None)

        # Reload updated numbers list
        numbers = db["countries"].get(country, [])

        if not numbers:
            save_db(db)
            return await call.answer("❌ Out of Stock", show_alert=True)

    locked = db["locked"]

    # ✅ Available numbers
    available = [n for n in numbers if n not in locked]

    if not available:
        save_db(db)
        return await call.answer("❌ All Numbers Locked", show_alert=True)

    # 🔁 Smart rotation
    selected = available[0]

    # 🔐 Lock new number
    db["active"][user_id] = {
        "number": selected,
        "country": country
    }
    db["locked"][selected] = int(user_id)

    save_db(db)

    # ================= BUTTON CONTROL =================

    buttons = [
        [InlineKeyboardButton(text="🔄 Change Numbers", callback_data=f"country_{country}")]
    ]

    if db.get("manual_mode", True):
        buttons.append(
            [InlineKeyboardButton(text="🔐 RECEIVE OTP OF THIS NUMBER", callback_data="send_otp")]
        )

    buttons.append(
        [InlineKeyboardButton(text="⬅ Back", callback_data="select_country")]
    )

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # ================= MESSAGE =================

    message_text = (
        f"╔══════════════════╗\n"
        f"   ✨ <b>{country} | WhatsApp Secure Portal</b>\n"
        f"╚══════════════════╝\n\n"
        f"📱 <b>Activated Number</b>\n"
        f"┌──────────────────┐\n"
        f"│  <code>{selected}</code>  │\n"
        f"└──────────────────┘\n\n"
        f"📌 <i>Touch & hold the number above to copy it.</i>\n\n"
        f"⏳ Once the verification code is sent,"
    )

    if db.get("manual_mode", True):
        message_text += (
            f"\npress the button below to access your OTP.\n\n"
            f"🔽 <b>RECEIVE OTP OF THIS NUMBER</b>"
        )
    else:
        message_text += (
            f"\nOTP will be detected automatically.\n\n"
            f"⚡ <b>AUTO OTP MODE ACTIVE</b>"
        )

    await call.message.edit_text(
        message_text,
        reply_markup=kb,
        parse_mode="HTML"
    )

# ---------------- SEND OTP REQUEST ----------------
@dp.callback_query(F.data == "send_otp")
async def send_otp(call: CallbackQuery):
    if not await check_bot_status(call):
        return
    user_id = call.from_user.id
    db = load_db()

    data = db["active"].get(str(user_id))
    if not data:
        return await call.answer("❌ No active number", show_alert=True)

    await bot.send_message(
        ADMIN_ID,
        f"📥 <b>OTP REQUEST</b>\n\n"
        f"👤 UserID: <code>{user_id}</code>\n"
        f"🌍 {data['country']}\n"
        f"📱 <code>{data['number']}</code>\n\n"
        f"Reply to this message with OTP."
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
    if message.from_user.id != ADMIN_ID:
        return

    text = message.reply_to_message.text
    if "UserID:" not in text:
        return

    try:
        user_id = int(text.split("UserID:")[1].split("\n")[0].replace("<code>", "").replace("</code>", "").strip())
    except:
        return

    otp = message.text.strip()
    db = load_db()

    data = db["active"].get(str(user_id))
    if not data:
        return await message.answer("❌ User not active")

    number = data["number"]
    country = data["country"]

    await bot.send_message(
        user_id,
        f"╔══════════════════╗\n"
        f"   🔐 <b>WHATSAPP SECURITY VERIFICATION</b>\n"
        f"╚══════════════════╝\n\n"
        f"✨ <b>Your One-Time Password (OTP)</b>\n"
        f"┌──────────────────┐\n"
        f"│   <code>{otp}</code>   │\n"
        f"└──────────────────┘\n\n"
        f"📱 <b>Number:</b> {number}\n"
        f"🌍 <b>Country:</b> {country}\n\n"
        f"🚫 <b>Important:</b>\n"
        f"Do NOT share this code with anyone.\n"
        f"This code is confidential and valid for a short time only.\n\n"
        f"════════════════════",
        parse_mode="HTML"
    )

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
    if message.from_user.id != ADMIN_ID:
        return

    db = load_db()
    db["manual_mode"] = False
    save_db(db)

    await message.answer("✅ Auto OTP Mode Enabled\n\n🔐 Manual Button Removed")


# ---------------- MANUAL MODE ----------------
@dp.message(Command("manually"))
async def manual_mode(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    db = load_db()
    db["manual_mode"] = True
    save_db(db)

    await message.answer("✅ Manual OTP Mode Enabled\n\n🔐 Button Restored")
    
# ---------------- LIVE STOCK ----------------
@dp.message(Command("live"))
async def live_stock(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    db = load_db()

    if not db["countries"]:
        return await message.answer("❌ No Countries Added")

    text = "📊 <b>Live Stock Status</b>\n\n"

    for country, numbers in db["countries"].items():
        total = len(numbers)
        locked = sum(1 for n in numbers if n in db["locked"])
        available = total - locked

        text += (
            f"🌍 <b>{country}</b>\n"
            f"   📦 Total: {total}\n"
            f"   🔒 Locked: {locked}\n"
            f"   ✅ Available: {available}\n\n"
        )

    await message.answer(text)
    
    
# ---------------- SMART GROUP OTP DETECT ----------------
@dp.message(F.chat.id == ALLOWED_GROUP_ID)
async def smart_group_otp_detect(message: Message):
    if not message.text:
        return

    text = message.text
    db = load_db()

    # Extract OTP (4-8 digits)
    otp_match = re.search(r"\b\d{4,8}\b", text)
    if not otp_match:
        print("OTP not found")
        return
    otp = otp_match.group()

    # Find line with WS (masked number)
    number_line = None
    for line in text.split("\n"):
        if "WS" in line:
            number_line = line
            break
    if not number_line:
        print("Number line not found")
        return

    # Extract last 3 digits
    digits = re.findall(r"\d", number_line)
    if len(digits) < 3:
        print("Not enough digits in number line")
        return
    last3 = "".join(digits[-3:])

    # Normalize number helper
    def normalize_number(num):
        return "".join(re.findall(r"\d", num))

    # Match with active users
    for user_id, data in list(db.get("active", {}).items()):
        real_number = normalize_number(data["number"])
        if real_number.endswith(last3):
            try:
                await bot.send_message(
                    int(user_id),
                    f"🔐 <b>AUTO OTP RECEIVED</b>\n\n"
                    f"🔑 OTP: <code>{otp}</code>\n"
                    f"📱 Number: {data['number']}\n"
                    f"🌍 Country: {data['country']}",
                    parse_mode="HTML"
                )

                # Remove number after OTP
                country = data["country"]
                if data["number"] in db["countries"].get(country, []):
                    db["countries"][country].remove(data["number"])
                db["locked"].pop(data["number"], None)
                db["active"].pop(user_id, None)

                save_db(db)
                await message.reply("✅ OTP Delivered")
                print(f"OTP SENT SUCCESS for {data['number']} -> {otp}")
                break
            except Exception as e:
                print("OTP Error:", e)
                
# ---------------- BROADCAST ----------------
@dp.message(Command("broadcast"))
async def broadcast(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    text = message.text.replace("/broadcast", "").strip()
    if not text:
        return await message.answer("Use:\n/broadcast Your message here")

    db = load_db()

    # collect all users from active + cooldown history
    users = set()

    users.update(db["active"].keys())
    users.update(db["cooldown"].keys())

    sent = 0
    failed = 0

    for uid in users:
        try:
            await bot.send_message(int(uid), text)
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1

    await message.answer(
        f"📢 <b>Broadcast Completed</b>\n\n"
        f"✅ Sent: {sent}\n"
        f"❌ Failed: {failed}"
    )
    



app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running successfully!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
# ---------------- RUN ----------------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    Thread(target=run_web).start()
    asyncio.run(main())
