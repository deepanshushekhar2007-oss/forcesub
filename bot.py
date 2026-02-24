import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, ContentTypeFilter
from aiogram.utils.keyboard import ReplyKeyboardMarkup, KeyboardButton
from PIL import Image, ImageDraw, ImageFont
import pytesseract
import asyncio

API_TOKEN = os.getenv("API_TOKEN")  # Must be set in Render or local env
if not API_TOKEN:
    raise ValueError("API_TOKEN environment variable is missing!")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ---------- Function to replace members number ----------
def replace_members_number_exact(image_path, new_number, output_path):
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

    for i, text in enumerate(data['text']):
        if "members" in text.lower():
            number_index = i - 1
            if number_index < 0:
                continue

            x, y, w, h = (data['left'][number_index], data['top'][number_index],
                          data['width'][number_index], data['height'][number_index])

            # Crop old number area to get pixel colors
            old_area = img.crop((x, y, x+w, y+h))
            bg_color = old_area.getpixel((0, 0))

            # Cover old number
            draw.rectangle([x, y, x+w, y+h], fill=bg_color)

            # Font same height
            try:
                font = ImageFont.truetype("DejaVuSans-Bold.ttf", h)
            except:
                font = ImageFont.load_default()

            # Average color of old number
            pixels = list(old_area.getdata())
            if pixels:
                avg_color = tuple(sum(p[i] for p in pixels)//len(pixels) for i in range(3))
            else:
                avg_color = (0, 128, 0)

            draw.text((x, y), str(new_number), fill=avg_color, font=font)
            break

    img.save(output_path)
    return output_path

# ---------- /start command ----------
@dp.message(Command(commands=["start"]))
async def cmd_start(message: types.Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Send Screenshot")]],
        resize_keyboard=True
    )
    await message.answer(
        "Send me your screenshot first, then send the number you want to replace 'members' with.",
        reply_markup=kb
    )

# ---------- Handle photo ----------
@dp.message(ContentTypeFilter(types=['photo']))
async def handle_photo(message: types.Message):
    uid = message.from_user.id

    # Save photo locally
    file_info = await bot.get_file(message.photo[-1].file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    img_path = f"{uid}_ss.png"
    with open(img_path, "wb") as f:
        f.write(downloaded_file.read())

    # Save path in memory (simple dictionary)
    if not hasattr(dp, "user_data"):
        dp.user_data = {}
    dp.user_data[uid] = {"img_path": img_path}

    await message.answer("✅ Screenshot received! Now send the number you want to replace 'members' with.")

# ---------- Handle number ----------
@dp.message()
async def handle_number(message: types.Message):
    uid = message.from_user.id

    try:
        number = int(message.text)
    except ValueError:
        await message.reply("Please send a valid number (e.g., 50).")
        return

    user_info = getattr(dp, "user_data", {}).get(uid)
    if not user_info or not os.path.exists(user_info.get("img_path", "")):
        await message.reply("❌ Please send a screenshot first.")
        return

    img_path = user_info["img_path"]
    output_path = f"{uid}_ss_updated.png"
    replace_members_number_exact(img_path, number, output_path)

    with open(output_path, "rb") as f:
        await message.answer_photo(f, caption=f"✅ Number replaced with {number}")

# ---------- Run bot ----------
if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp)
