import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

db = sqlite3.connect("database.db")
cursor = db.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS products (name TEXT, price INTEGER, file TEXT)")
db.commit()

# sample product
cursor.execute("INSERT OR IGNORE INTO products VALUES ('Sample Script', 100, 'sample.zip')")
db.commit()


@dp.message(Command("start"))
async def start(msg: types.Message):
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?)", (msg.from_user.id, 0))
    db.commit()
    await msg.answer("Welcome!\nUse /products to see items.")


@dp.message(Command("products"))
async def products(msg: types.Message):
    cursor.execute("SELECT rowid, name, price FROM products")
    items = cursor.fetchall()
    text = "🛒 Products:\n"
    for i in items:
        text += f"{i[0]}. {i[1]} - ₹{i[2]}\n"
    text += "\nBuy using /buy <id>"
    await msg.answer(text)


@dp.message(Command("buy"))
async def buy(msg: types.Message):
    try:
        pid = int(msg.text.split()[1])
        cursor.execute("SELECT name, price, file FROM products WHERE rowid=?", (pid,))
        product = cursor.fetchone()
        cursor.execute("SELECT balance FROM users WHERE id=?", (msg.from_user.id,))
        balance = cursor.fetchone()[0]

        if balance >= product[1]:
            cursor.execute("UPDATE users SET balance=? WHERE id=?", (balance-product[1], msg.from_user.id))
            db.commit()
            await msg.answer_document(FSInputFile(product[2]))
        else:
            await msg.answer("Insufficient balance. Use /addbalance")
    except:
        await msg.answer("Usage: /buy <product_id>")


@dp.message(Command("addbalance"))
async def add_balance(msg: types.Message):
    await msg.answer("Send UPI screenshot after paying to: yourupi@bank")

@dp.message(lambda m: m.photo)
async def payment_proof(msg: types.Message):
    await bot.forward_message(ADMIN_ID, msg.chat.id, msg.message_id)
    await msg.answer("Payment proof sent to admin for approval.")


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
