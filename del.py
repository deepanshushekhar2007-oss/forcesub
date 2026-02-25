import asyncio
import time
from collections import defaultdict

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import CommandStart, Command
from aiogram.enums import ChatType, ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest

# ==============================
# 🔥 CONFIG (EDIT HERE ONLY)
# ==============================
BOT_TOKEN = "8628474569:AAHS18inBbJsjptsm0_KV2lW4kYo6HQfWRA"
OWNER_ID = 6860983540  # 👈 Apna Telegram numeric ID daalo

SPAM_LIMIT = 5
TIME_WINDOW = 5
# ==============================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

user_sticker_data = defaultdict(list)
group_delete_count = defaultdict(int)


# ========= ADMIN CHECK =========
async def is_admin(chat_id, user_id):
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in ("administrator", "creator")


# ========= PRIVATE START =========
@dp.message(CommandStart())
async def start_private(message: Message):
    if message.chat.type == ChatType.PRIVATE:
        await message.answer(
            "👋 Fast Moderation Bot Activated!\n\n"
            "📌 HOW TO USE:\n"
            "1️⃣ Add me to your group\n"
            "2️⃣ Make me ADMIN\n"
            "3️⃣ Give Delete Messages permission\n\n"
            "⚡ COMMAND:\n"
            "Reply to message + /del\n\n"
            "🚫 Sticker spam auto delete enabled."
        )


# ========= BOT ADDED TO GROUP =========
@dp.my_chat_member()
async def bot_added(event: ChatMemberUpdated):
    if event.new_chat_member.status in (
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR
    ):
        chat = event.chat
        try:
            await bot.send_message(
                OWNER_ID,
                f"📢 Bot Added To Group\n\n"
                f"Group Name: {chat.title}\n"
                f"Group ID: {chat.id}"
            )
        except:
            pass


# ========= FAST BULK DELETE =========
@dp.message(Command("del"))
async def fast_delete(message: Message):

    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    if not await is_admin(message.chat.id, message.from_user.id):
        return

    if not message.reply_to_message:
        await message.reply("⚠️ Reply to a message first.")
        return

    start = message.reply_to_message.message_id
    end = message.message_id

    ids = list(range(start, end + 1))
    deleted = 0

    for i in range(0, len(ids), 100):
        chunk = ids[i:i+100]
        try:
            await bot.delete_messages(message.chat.id, chunk)
            deleted += len(chunk)
        except TelegramBadRequest:
            pass

    group_delete_count[message.chat.id] += deleted

    # Send log to Owner
    try:
        await bot.send_message(
            OWNER_ID,
            f"🧹 Delete Log\n\n"
            f"Group: {message.chat.title}\n"
            f"Deleted Now: {deleted}\n"
            f"Total Deleted In Group: {group_delete_count[message.chat.id]}"
        )
    except:
        pass


# ========= STICKER SPAM CONTROL =========
@dp.message(F.sticker)
async def sticker_spam_control(message: Message):

    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    if await is_admin(message.chat.id, message.from_user.id):
        return

    user_id = message.from_user.id
    now = time.time()

    recent = [t for t in user_sticker_data[user_id] if now - t < TIME_WINDOW]
    recent.append(now)
    user_sticker_data[user_id] = recent

    if len(recent) >= SPAM_LIMIT:
        try:
            await message.delete()
            group_delete_count[message.chat.id] += 1
        except:
            pass


# ========= START BOT =========
async def main():
    print("🚀 Fast Moderation Bot Running On Render...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())