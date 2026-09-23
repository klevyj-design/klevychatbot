import logging
import json
import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ChatMemberStatus
from aiogram.filters import Command
from aiohttp import web  # Додано для обходу обмежень Render

# ==================== АВТОМАТИЧНІ НАЛАШТУВАННЯ СИСТЕМИ ====================
TOKEN = "8973060800:AAHV0T7_yknoNZWo2s7AFxGC108b7fHjPYE"
SUPER_ADMIN_ID = 997372240
MAIN_CHAT_ID = -1004457991271
# ==========================================================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

CHANNELS_FILE = "channels.json"
ADMINS_FILE = "admins.json"

def load_data(filename, default_value):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return default_value

def save_data(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f)

admins_list = load_data(ADMINS_FILE, [SUPER_ADMIN_ID])
channels_list = load_data(CHANNELS_FILE, [-1004407416238])

@dp.message(Command("add_admin"))
async def add_admin_cmd(message: types.Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return
    try:
        new_admin = int(message.text.split()[1])
        if new_admin not in admins_list:
            admins_list.append(new_admin)
            save_data(ADMINS_FILE, admins_list)
            await message.answer(f"✅ Користувача `{new_admin}` успішно призначено адміном!")
        else:
            await message.answer("ℹ️ Цей користувач вже є адміністратором.")
    except (IndexError, ValueError):
        await message.answer("❌ Формат команди:\n`/add_admin ID_КОРИСТУВАЧА`")

@dp.message(Command("add_channel"))
async def add_channel_cmd(message: types.Message):
    if message.from_user.id not in admins_list:
        return
    try:
        channel_id = int(message.text.split()[1])
        if channel_id not in channels_list:
            channels_list.append(channel_id)
            save_data(CHANNELS_FILE, channels_list)
            await message.answer(f"✅ Новий чат/канал `{channel_id}` успішно додано!")
        else:
            await message.answer("ℹ️ Цей канал вже перевіряється ботом.")
    except (IndexError, ValueError):
        await message.answer("❌ Формат команди:\n`/add_channel -100XXXXXXXXXX`")

async def is_subscribed_to_all(user_id: int) -> bool:
    if not channels_list:
        return True
    for channel_id in channels_list:
        try:
            member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
                return False
        except Exception as e:
            logging.error(f"Помилка доступу до каналу {channel_id}: {e}")
            continue
    return True

@dp.message()
async def check_chat_messages(message: types.Message):
    if message.chat.id == MAIN_CHAT_ID:
        member = await message.chat.get_member(message.from_user.id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
            return

        if not await is_subscribed_to_all(message.from_user.id):
            try:
                await message.delete()
                warn_msg = await message.answer(
                    f"👋 **Hi / Привіт, {message.from_user.first_name}!**\n\n"
                    f"🚫 **EN:** To write here, you must subscribe to our resources first!\n"
                    f"🚫 **UA:** Щоб писати тут, спочатку підпишіться на наші ресурси!"
                )
                await asyncio.sleep(10)
                await warn_msg.delete()
            except Exception as e:
                logging.error(f"Помилка модерації: {e}")

# --- ФЕЙКОВИЙ ВЕБ-СЕРВЕР ДЛЯ ОБХОДУ ОБМЕЖЕНЬ RENDER ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    # Запускаємо веб-сервер для хостингу та бота одночасно
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        
