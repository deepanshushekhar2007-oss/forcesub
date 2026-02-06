import asyncio
import os
import sqlite3
from aiogram import Bot, Dispatcher, Router
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import Command
from aiogram.enums import ChatMemberStatus
from aiogram.client.default import DefaultBotProperties

# ================= CONFIG =================
# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "6860983540"))
# =========================================

PROMO_TEXT = (
    "DO YOU WANT TO ADD YOUR CHANNEL AND GET PROMOTED\n"
    "THEN CONTACT @SPIDYWS"
)
# =========================================

# ---------- BOT ----------
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ---------- DATABASE ----------
DB_PATH = "data.db"
db = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = db.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS channels (channel TEXT PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS joins (user_id INTEGER, channel TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS access (user_id INTEGER PRIMARY KEY)")
db.commit()

# ---------- KEYBOARDS ----------
def owner_panel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Channel", callback_data="add_channel")],
        [InlineKeyboardButton(text="➖ Remove Channel", callback_data="remove_channel")],
        [InlineKeyboardButton(text="📊 Channel Status", callback_data="status")]
    ])

def channels_kb(join=False):
    buttons = []
    cur.execute("SELECT channel FROM channels")
    for (ch,) in cur.fetchall():
        if join:
            buttons.append([InlineKeyboardButton(
                text=f"✅ Join {ch}",
                url=f"https://t.me/{ch.replace('@','')}"
            )])
        else:
            buttons.append([InlineKeyboardButton(
                text=f"❌ Remove {ch}",
                callback_data=f"del_{ch}"
            )])
    if join:
        buttons.append([InlineKeyboardButton(
            text="🔄 Check Again",
            callback_data="check_join"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ---------- UTILS ----------
async def is_joined(user_id: int, channel: str) -> bool:
    try:
        member = await bot.get_chat_member(channel, user_id)
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR
        )
    except Exception as e:
        print("JOIN CHECK ERROR:", e)
        return False

def has_access(user_id: int) -> bool:
    cur.execute("SELECT 1 FROM access WHERE user_id=?", (user_id,))
    return cur.fetchone() is not None

def get_channels():
    cur.execute("SELECT channel FROM channels")
    return [x[0] for x in cur.fetchall()]

# ---------- START ----------
@router.message(Command("start"))
async def start(message: Message):
    user = message.from_user

    if user.id == OWNER_ID:
        await message.answer("👑 <b>Owner Panel</b>", reply_markup=owner_panel())
        return

    await bot.send_message(
        OWNER_ID,
        f"🔔 <b>User Started Bot</b>\n"
        f"👤 {user.full_name}\n"
        f"🆔 {user.id}\n"
        f"🔗 @{user.username if user.username else 'No username'}"
    )

    if not has_access(user.id):
        await message.answer(PROMO_TEXT)
        return

    await message.answer("✅ <b>Access granted</b>")

# ---------- OWNER ACCESS ----------
@router.message(Command("access"))
async def give_access(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        uid = int(message.text.split()[1])
        cur.execute("INSERT OR IGNORE INTO access VALUES (?)", (uid,))
        db.commit()
        await message.reply(f"✅ Access granted to `{uid}`")
        await bot.send_message(uid, "✅ You are approved to use the bot")
    except:
        await message.reply("❌ Usage: /access user_id")

# ---------- ADD CHANNEL ----------
@router.callback_query(lambda c: c.data == "add_channel")
async def add_channel_prompt(c: CallbackQuery):
    if c.from_user.id != OWNER_ID:
        return
    await c.message.edit_text("Send channel username\nExample: @mychannel")

@router.message(lambda m: m.text and m.text.startswith("@"))
async def add_channel(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    channel = message.text.strip()
    try:
        cur.execute("INSERT INTO channels VALUES (?)", (channel,))
        db.commit()
        await message.reply(f"✅ {channel} added", reply_markup=owner_panel())
    except:
        await message.reply("⚠️ Channel already exists")

# ---------- REMOVE CHANNEL ----------
@router.callback_query(lambda c: c.data == "remove_channel")
async def remove_channel(c: CallbackQuery):
    if c.from_user.id != OWNER_ID:
        return
    await c.message.edit_text("Remove channel:", reply_markup=channels_kb())

@router.callback_query(lambda c: c.data.startswith("del_"))
async def del_channel(c: CallbackQuery):
    if c.from_user.id != OWNER_ID:
        return
    ch = c.data.replace("del_", "")
    cur.execute("DELETE FROM channels WHERE channel=?", (ch,))
    cur.execute("DELETE FROM joins WHERE channel=?", (ch,))
    db.commit()
    await c.message.edit_text(f"❌ {ch} removed", reply_markup=owner_panel())

# ---------- STATUS ----------
@router.callback_query(lambda c: c.data == "status")
async def status(c: CallbackQuery):
    if c.from_user.id != OWNER_ID:
        return
    text = "📊 <b>Channel Status</b>\n\n"
    for ch in get_channels():
        cur.execute(
            "SELECT COUNT(DISTINCT user_id) FROM joins WHERE channel=?",
            (ch,)
        )
        count = cur.fetchone()[0]
        text += f"{ch} → {count} joined\n"
    await c.message.edit_text(text, reply_markup=owner_panel())

# ---------- FORCE JOIN ----------
@router.message()
async def force_join(message: Message):
    if message.from_user.id == OWNER_ID:
        return
    if message.chat.type not in ("group", "supergroup"):
        return

    user = message.from_user
    user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

    channels = get_channels()
    if not channels:
        return

    for ch in channels:
        if not await is_joined(user.id, ch):
            try:
                await message.delete()
            except:
                pass
            await message.answer(
                f"🚫 {user_mention}\n\n"
                "<b>Message karne se pehle niche diye gaye channels join karo 👇</b>",
                reply_markup=channels_kb(join=True)
            )
            return

    for ch in channels:
        cur.execute(
            "INSERT OR IGNORE INTO joins VALUES (?, ?)",
            (user.id, ch)
        )
    db.commit()

# ---------- JOIN CHECK ----------
@router.callback_query(lambda c: c.data == "check_join")
async def check_join(c: CallbackQuery):
    await asyncio.sleep(3)
    for ch in get_channels():
        if not await is_joined(c.from_user.id, ch):
            await c.answer(
                "❌ Abhi join detect nahi hua.\nJoin karke Check Again dabao",
                show_alert=True
            )
            return

    await c.message.edit_text(
        "✅ <b>Access granted.</b>\n"
        "Ab group me message kar sakte ho.\n\n"
        "Promotion ke liye contact: @SPIDYWS"
    )

# ---------- MAIN ----------
async def main():
    print("🤖 Bot running on Render...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
