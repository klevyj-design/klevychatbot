import logging
import json
import os
import asyncio
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ChatMemberStatus
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

TOKEN = "8973060800:AAHI2CWAQZ5wWr5O0TCexzvH_ap_IqcfEk8"
SUPER_ADMIN_ID = 997372240

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
bot = Bot(token=TOKEN)
dp = Dispatcher()
CONFIG_FILE = "bot_config.json"
USER_STATES = {}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            try: 
                return json.load(f)
            except: 
                pass
    return {"admins": [SUPER_ADMIN_ID], "main_chats": {}, "channels": {}}

def save_config(config):
    with open(CONFIG_FILE, "w") as f: 
        json.dump(config, f, indent=4)

config = load_config()

def is_admin(user_id): 
    return user_id in config["admins"] or user_id == SUPER_ADMIN_ID

def get_admin_keyboard(user_id):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="💬 Мій Головний Чат", callback_data="manage_main_chat"))
    builder.row(types.InlineKeyboardButton(text="📢 Канали підписки (до 5 шт.)", callback_data="manage_channels"))
    if user_id == SUPER_ADMIN_ID:
        builder.row(types.InlineKeyboardButton(text="👑 Додати субадміна", callback_data="add_subadmin"))
    builder.row(types.InlineKeyboardButton(text="📊 Статус налаштувань", callback_data="view_stats"))
    return builder.as_markup()

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    if message.chat.type == "private" and is_admin(message.from_user.id):
        USER_STATES[message.from_user.id] = None
        await message.answer(
            "⚙️ **Панель керування ботом**\n\nТут ви можете налаштувати роботу бота прямо з телефону.", 
            reply_markup=get_admin_keyboard(message.from_user.id)
        )

@dp.callback_query()
async def process_callbacks(callback: types.CallbackQuery):
    u_id = str(callback.from_user.id)
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Немає доступу!", show_alert=True)
        return

    if callback.data == "manage_main_chat":
        USER_STATES[callback.from_user.id] = "wait_main_chat"
        current_chat = config["main_chats"].get(u_id, "Не встановлено")
        await callback.message.edit_text(
            f"💬 **Налаштування Головного чату:**\n\nПоточний чат: `{current_chat}`\n\n👉 Надішліть сюди ID вашої групи (наприклад: `-1004457991271`).", 
            reply_markup=InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🔙 Назад", callback_data="to_main")).as_markup()
        )
    elif callback.data == "manage_channels":
        USER_STATES[callback.from_user.id] = None
        user_chans = config["channels"].get(u_id, [])
        builder = InlineKeyboardBuilder()
        text = "📢 **Ваші канали для підписки (до 5 шт.):**\n\n"
        if not user_chans: 
            text += "ℹ️ Список порожній.\n"
        else:
            for idx, ch in enumerate(user_chans, 1):
                text += f"{idx}. ID: `{ch}`\n"
                builder.row(types.InlineKeyboardButton(text=f"❌ Видалити {ch}", callback_data=f"delchan_{ch}"))
        if len(user_chans) < 5: 
            builder.row(types.InlineKeyboardButton(text="➕ Додати новий канал", callback_data="add_chan_mode"))
        builder.row(types.InlineKeyboardButton(text="🔙 Назад", callback_data="to_main"))
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    elif callback.data == "add_chan_mode":
        USER_STATES[callback.from_user.id] = "wait_channel"
        await callback.message.edit_text(
            "📝 Надішліть сюди цифровий ID каналу підписки (наприклад: `-1004407416238`).", 
            reply_markup=InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🔙 Назад", callback_data="manage_channels")).as_markup()
        )
    elif callback.data == "add_subadmin":
        USER_STATES[callback.from_user.id] = "wait_subadmin"
        await callback.message.edit_text(
            "👑 Надішліть боту цифровий ID користувача, якому хочете дати доступ.", 
            reply_markup=InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🔙 Назад", callback_data="to_main")).as_markup()
        )
    elif callback.data == "view_stats":
        USER_STATES[callback.from_user.id] = None
        my_chat = config["main_chats"].get(u_id, "Не встановлено")
        my_chans = config["channels"].get(u_id, [])
        await callback.message.edit_text(
            f"📊 **Статус налаштувань:**\n\n🔹 Чат модерації: `{my_chat}`\n🔹 Каналів перевірки: {len(my_chans)}/5\n🔹 Адмінів у системі: {len(config['admins'])}", 
            reply_markup=get_admin_keyboard(callback.from_user.id)
        )
    elif callback.data == "to_main":
        USER_STATES[callback.from_user.id] = None
        await callback.message.edit_text("Головне меню панелі керування:", reply_markup=get_admin_keyboard(callback.from_user.id))
    elif callback.data.startswith("delchan_"):
        ch_to_del = int(callback.data.split("_")[1])
        if u_id in config["channels"] and ch_to_del in config["channels"][u_id]:
            config["channels"][u_id].remove(ch_to_del)
            save_config(config)
            await callback.answer("✅ Канал вилучено!", show_alert=True)
        
        user_chans = config["channels"].get(u_id, [])
        builder = InlineKeyboardBuilder()
        text = "📢 **Ваші канали для підписки (до 5 шт.):**\n\n"
        if not user_chans: text += "ℹ️ Список порожній.\n"
        else:
            for idx, ch in enumerate(user_chans, 1):
                text += f"{idx}. ID: `{ch}`\n"
                builder.row(types.InlineKeyboardButton(text=f"❌ Видалити {ch}", callback_data=f"delchan_{ch}"))
        if len(user_chans) < 5: builder.row(types.InlineKeyboardButton(text="➕ Додати новий канал", callback_data="add_chan_mode"))
        builder.row(types.InlineKeyboardButton(text="🔙 Назад", callback_data="to_main"))
        await callback.message.edit_text(text, reply_markup=builder.as_markup())

async def auto_delete_msg(chat_id: int, message_id: int, delay: int = 10):
    await asyncio.sleep(delay)
    try: 
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramBadRequest: 
        pass

@dp.message()
async def handle_inputs(message: types.Message):
    u_id = str(message.from_user.id)
    chat_id = message.chat.id

    for owner_id, main_chat_id in config["main_chats"].items():
        if chat_id == main_chat_id:
            try:
                group_member = await message.chat.get_member(message.from_user.id)
                if group_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]: 
                    return
            except: 
                pass

            target_channels = config["channels"].get(owner_id, [])
            if not target_channels: 
                return

            not_subscribed = []
            for channel_id in target_channels:
                try:
                    member = await bot.get_chat_member(chat_id=channel_id, user_id=message.from_user.id)
                    if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
                        not_subscribed.append(channel_id)
                except: 
                    continue

            if not_subscribed:
                try:
                    await message.delete()
                    warn_msg = await message.answer(
                        f"⚠️ Чат заблоковано! @{message.from_user.username or message.from_user.first_name}, "
                        f"підпишіться на наші канали, щоб писати сюди! (Зникне через 10 сек)."
                    )
                    asyncio.create_task(auto_delete_msg(chat_id, warn_msg.message_id, 10))
                except TelegramBadRequest: 
                    pass
            return

    if message.chat.type == "private" and is_admin(message.from_user.id):
        state = USER_STATES.get(message.from_user.id)
        if state == "wait_main_chat":
            try:
                config["main_chats"][u_id] = int(message.text.strip())
                save_config(config)
                USER_STATES[message.from_user.id] = None
                await message.answer("✅ Головний чат збережено!", reply_markup=get_admin_keyboard(message.from_user.id))
            except ValueError:
                await message.answer("❌ Надішліть правильний числовий ID чату.")
        elif state == "wait_channel":
            try:
                chan_target = int(message.text.strip())
                if u_id not in config["channels"]: 
                    config["channels"][u_id] = []
                if len(config["channels"][u_id]) >= 5:
                    await message.answer("❌ Максимум 5 каналів!", reply_markup=get_admin_keyboard(message.from_user.id))
                    USER_STATES[message.from_user.id] = None
                    return
                if chan_target not in config["channels"][u_id]:
                    config["channels"][u_id].append(chan_target)
                    save_config(config)
                    await message.answer("✅ Канал додано!", reply_markup=get_admin_keyboard(message.from_user.id))
                else:
                    await message.answer("⚠️ Вже є у списку.", reply_markup=get_admin_keyboard(message.from_user.id))
                USER_STATES[message.from_user.id] = None
            except ValueError:
                await message.answer("❌ Надішліть правильний числовий ID каналу.")
        elif state == "wait_subadmin" and message.from_user.id == SUPER_ADMIN_ID:
            try:
                new_admin = int(message.text.strip())
                if new_admin not in config["admins"]:
                    config["admins"].append(new_admin)
