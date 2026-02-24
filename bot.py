import asyncio
import os
import cv2
import numpy as np
import pytesseract
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import CommandStart
from PIL import Image, ImageDraw, ImageFont

API_TOKEN = "8534970960:AAEBslbIwNoDZT8VsZMdcfLxhhIEaOMtmmM"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

user_photos = {}

# ================= OCR DETECTION =================
def detect_member_number(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Improve contrast
    gray = cv2.GaussianBlur(gray, (3,3), 0)

    data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)

    for i, text in enumerate(data["text"]):
        if text.isdigit():
            x = data["left"][i]
            y = data["top"][i]
            w = data["width"][i]
            h = data["height"][i]
            return (x, y, w, h)

    return None


# ================= REPLACE NUMBER =================
def replace_number(image_path, output_path, new_number):
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    bbox = detect_member_number(image_path)

    if not bbox:
        img.save(output_path)
        return False

    x, y, w, h = bbox

    # Sample background
    crop = img.crop((x, y, x+w, y+h))
    avg_color = tuple(int(c) for c in crop.resize((1,1)).getpixel((0,0)))

    # Cover old number
    draw.rectangle((x-2, y-2, x+w+2, y+h+2), fill=avg_color)

    # Load font
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", h)
    except:
        font = ImageFont.load_default()

    # Telegram green color
    draw.text((x, y), str(new_number), font=font, fill=(0, 200, 120))

    img.save(output_path)
    return True


# ================= START =================
@dp.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer("📸 Send Telegram screenshot.\nThen send new member count.")

# ================= HANDLE PHOTO =================
@dp.message(F.photo)
async def handle_photo(message: Message):
    photo = message.photo[-1]
    file_path = f"temp_{message.from_user.id}.jpg"
    await bot.download(photo, destination=file_path)

    user_photos[message.from_user.id] = file_path
    await message.answer("✅ Screenshot received.\nNow send new member count.")

# ================= HANDLE NUMBER =================
@dp.message(F.text.regexp(r'^\d+$'))
async def handle_number(message: Message):
    user_id = message.from_user.id

    if user_id not in user_photos:
        await message.answer("❌ Send screenshot first.")
        return

    new_number = message.text
    input_path = user_photos[user_id]
    output_path = f"edited_{user_id}.jpg"

    processing = await message.answer("⚙ Processing with OCR...")

    success = replace_number(input_path, output_path, new_number)

    if not success:
        await processing.edit_text("❌ Could not detect member number.")
        return

    await message.answer_photo(FSInputFile(output_path))

    await processing.delete()

    os.remove(input_path)
    os.remove(output_path)
    user_photos.pop(user_id)


# ================= RUN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())