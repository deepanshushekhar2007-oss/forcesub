import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ContentType
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardMarkup, KeyboardButton
from PIL import Image, ImageDraw, ImageFont
import pytesseract

API_TOKEN = os.getenv("API_TOKEN")  # Set this in Render environment

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- Function to replace members number ---
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

            # Sample background from old number
            old_area = img.crop((x, y, x+w, y+h))
            bg_color = old_area.getpixel((0, 0))

            draw.rectangle([x, y, x+w, y+h], fill=bg_color)

            # Try exact font size
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

# --- Start command ---
@dp.message(Command(commands=["start"]))
async def start_cmd(message: types.Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Send Screenshot")]
        ], resize_keyboard=True
    )
    await message.answer("Send me your screenshot and the number you want to replace the members with.", reply_markup=kb)

# --- Handle photo ---
@dp.message(content_types=ContentType.PHOTO)
async def handle_photo(message: types.Message):
    uid = message.from_user.id
    await message.answer("✅ Screenshot received! Now send the number you want to replace the members with.")
    
    # Save photo
    file_info = await bot.get_file(message.photo[-1].file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    img_path = f"{uid}_ss.png"
    with open(img_path, "wb") as f:
        f.write(downloaded_file.read())

    # Store file path in user context
    dp.current_state(chat=uid, user=uid).update_data(img_path=img_path)

# --- Handle number ---
@dp.message()
async def handle_number(message: types.Message):
    uid = message.from_user.id
    try:
        number = int(message.text)
    except ValueError:
        await message.reply("Please send a valid number.")
        return

    # Get last uploaded screenshot
    state = dp.current_state(chat=uid, user=uid)
    data = await state.get_data()
    img_path = data.get("img_path")
    if not img_path or not os.path.exists(img_path):
        await message.reply("Please send a screenshot first.")
        return

    output_path = f"{uid}_ss_updated.png"
    replace_members_number_exact(img_path, number, output_path)

    # Send back updated screenshot
    with open(output_path, "rb") as f:
        await message.answer_photo(f, caption=f"✅ Number replaced with {number}")

# --- Run bot ---
if __name__ == "__main__":
    import asyncio
    from aiogram import executor
    executor.start_polling(dp)
