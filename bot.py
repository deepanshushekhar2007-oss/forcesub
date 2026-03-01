import asyncio
import sqlite3
import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Database
db = sqlite3.connect("database.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0
)
""")
db.commit()

# Load products
def load_products():
    with open("products.json", "r") as f:
        return json.load(f)

# Start
@dp.message(Command("start"))
async def start(message: types.Message):
    cursor.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (message.from_user.id,))
    db.commit()
    await message.answer("👋 Welcome!\nUse /products to see products.")

# Show products
@dp.message(Command("products"))
async def show_products(message: types.Message):
    products = load_products()
    text = "🛒 Available Products:\n\n"
    for i, p in enumerate(products):
        text += f"{i+1}. {p['name']} - ₹{p['price']}\n"
    text += "\nBuy using: /buy <number>"
    await message.answer(text)

# Buy
@dp.message(Command("buy"))
async def buy_product(message: types.Message):
    try:
        index = int(message.text.split()[1]) - 1
        products = load_products()
        product = products[index]

        cursor.execute("SELECT balance FROM users WHERE id=?", (message.from_user.id,))
        balance = cursor.fetchone()[0]

        if balance >= product["price"]:
            cursor.execute("UPDATE users SET balance=? WHERE id=?",
                           (balance - product["price"], message.from_user.id))
            db.commit()

            await message.answer_document(FSInputFile(product["file"]))
        else:
            await message.answer("❌ Insufficient balance.\nUse /addbalance")

    except:
        await message.answer("Usage: /buy <product_number>")

# Add balance
@dp.message(Command("addbalance"))
async def add_balance(message: types.Message):
    await message.answer(
        "💳 Send payment to UPI: yourupi@bank\n\n"
        "After payment, send screenshot here."
    )

# Payment proof
@dp.message(lambda m: m.photo)
async def payment_proof(message: types.Message):
    await bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
    await message.answer("✅ Screenshot sent to admin for approval.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
