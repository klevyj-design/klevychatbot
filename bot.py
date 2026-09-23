import logging
import json
import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ChatMemberStatus
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

# ==================== ЄДИНЕ НАЛАШТУВАННЯ (ВЛАСНИК СИСТЕМИ) ====================
TOKEN = "8973060800:AAHV0T7_yknoNZWo2s7AFxGC108b7fHjPYE"
SUPER_ADMIN_ID = 997372240  # Тільки ваш особистий ID прописаний залізно
# ==============================================================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

CONFIG_FILE = "bot_config.json"

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
        json.dump(config, f)

config = load_config()

# Перевірка: чи користувач є адміном цього бота
def is_admin(user_id):
    return user_id in config["admins"] or user_id == SUPER_ADMIN_ID

# --- КЛАВІАТУРА АДМІН-ПАНЕЛІ ---
def get_admin_keyboard(user_id):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="💬 Мій Головний Чат (де видаляти)", callback_data="manage_main_chat"))
    builder.row(types.InlineKeyboardButton(text="📢 Канали підписки (до 5 шт.)", callback_data="manage_channels"))
    if user_id == SUPER_ADMIN_ID:
        builder.row(types.InlineKeyboardButton(text="👑 Додати субадміна", callback_data="add_subadmin"))
    builder.row(types.InlineKeyboardButton(text="📊 Статус налаштувань", callback_data="view_stats"))
    return builder.as_markup()

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    if message.chat.type == "private" and is_admin(message.from_user.id):
        await message.answer(
            f"⚙️ **Панель керування ботом**\n\n"
            f"Тут ви можете повністю налаштувати логіку роботи бота без зміни коду.",
            reply_markup=get_admin_keyboard(message.from_user.id)
        )

# --- ОБРОБКА КНОПОК ПАНЕЛІ ---
@dp.callback_query()
async def process_callbacks(callback: types.CallbackQuery):
    u_id = str(callback.from_user.id)
    
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Немає доступу!", show_alert=True)
        return

    if callback.data == "manage_main_chat":
        current_chat = config["main_chats"].get(u_id, "Не встановлено")
        await callback.message.edit_text(
            f"💬 **Налаштування Головного чату спілкування:**\n\n"
            f"Поточний чат, де бот видаляє повідомлення: `{current_chat}`\n\n"
            f"👉 **Щоб змінити або встановити його:** просто надішліть у приват боту ID вашої групи (наприклад: `-1004457991271`).\n"
            f"*(Бот має бути адміном у цій групі з правом видалення повідомлень)*",
            reply_markup=InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🔙 Назад", callback_data="to_main")).as_markup()
        )
        
    elif callback.data == "manage_channels":
        user_chans = config["channels"].get(u_id, [])
        builder = InlineKeyboardBuilder()
        text = "📢 **Ваші канали для обов'язкової підписки (до 5 шт.):**\n\n"
        
        if not user_chans:
            text += "ℹ️ Список порожній. Користувачі можуть писати без обмежень.\n"
        else:
            for idx, ch in enumerate(user_chans, 1):
                text += f"{idx}. ID: `{ch}`\n"
                builder.row(types.InlineKeyboardButton(text=f"❌ Видалити {ch}", callback_data=f"delchan_{ch}"))
                
        if len(user_chans) < 5:
            builder.row(types.InlineKeyboardButton(text="➕ Додати новий канал", callback_data="add_chan_mode"))
        builder.row(types.InlineKeyboardButton(text="🔙 Назад", callback_data="to_main"))
        
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        
    elif callback.data == "add_chan_mode":
        await callback.message.edit_text(
            "📝 **Додавання каналу підписки:**\n\n"
            "Надішліть у приват боту цифровий ID каналу (наприклад: `-1004407416238`).\n"
            "*(Бот має бути адміном на цьому каналі)*",
            reply_markup=InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🔙 Назад", callback_data="manage_channels")).as_markup()
        )
        
    elif callback.data == "add_subadmin":
        await callback.message.edit_text(
            "👑 **Додавання нового адміністратора системи:**\n\n"
            "Надішліть боту цифровий Telegram ID користувача, якому хочете довірити бота.\n"
            "Він зможе налаштувати його під свої групи.",
            reply_markup=InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🔙 Назад", callback_data="to_main")).as_markup()
        )
        
    elif callback.data == "view_stats":
        my_chat = config["main_chats"].get(u_id, "Не встановлено")
        my_chans = config["channels"].get(u_id, [])
        await callback.message.edit_text(
            f"📊 **Поточний статус вашої конфігурації:**\n\n"
            f"🔹 Модерація в чаті: `{my_chat}`\n"
            f"🔹 Кількість каналів перевірки: {len(my_chans)}/5\n"
            f"🔹 Всього адмінів у системі: {len(config['admins'])}",
            reply_markup=get_admin_keyboard(callback.from_user.id)
        )
        
    elif callback.data == "to_main":
        await callback.message.edit_text("Головне меню панелі керування:", reply_markup=get_admin_keyboard(callback.from_user.id))
        
    elif callback.data.startswith("delchan_"):
        ch_to_del = int(callback.data.split("_")[1])
        if u_id in config["channels"] and ch_to_del in config["channels"][u_id]:
            config["channels"][u_id].remove(ch_to_del)
            save_config(config)
            await callback.answer("✅ Канал вилучено!", show_alert=True)
        await callback.message.edit_text("Головне меню:", reply_markup=get_admin_keyboard(callback.from_user.id))

# --- ОБРОБКА ТЕКСТУ (ПРИЙОМ НАЛАШТУВАНЬ ВІД АДМІНІВ) ---
@dp.message()
async def handle_inputs(message: types.Message):
    u_id = str(message.from_user.id)

    # 1. ЛОГІКА МОДЕРАЦІЇ В ЧАТАХ
    # Шукаємо, чи є цей чат чиєюсь підключеною групою для видалення повідомлень
    for owner_id, main_chat_id in config["main_chats"].items():
        if message.chat.id == main_chat_id:
            # Пропускаємо адмінів самої групи Telegram
            group_member = await message.chat.get_member(message.from_user.id)
            if group_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
                return

            # Перевіряємо підписку на канали саме цього адміна
            check_channels = config["channels"].get(owner_id, [])
            for ch_id in check_channels:
                try:
                    ch_member = await bot.get_chat_member(chat_id=ch_id, user_id=message.from_user.id)
                    if ch_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
                        try:
                            await message.delete()
                            warn = await message.answer(
                                f"👋 **Hi / Привіт, {message.from_user.first_name}!**\n\n"
                                f"🚫 **EN:** Subscribe to our channels to write here!\n"
                                f"🚫 **UA:** Підпишіться на наші канали, щоб писати тут!"
                            )
                            await asyncio.sleep(10)
                            await warn.delete()
                        except:
                            pass
                        return
                except:
                    continue
            return

    # 2. ПРИЙОМ ДАНИХ В ПРИВАТІ АДМІНА
    if message.chat.type == "private" and is_admin(message.from_user.id):
        text = message.text.strip()
        
        # Якщо ввели ID групи або каналу (число починається з мінуса і містить цифри)
        if text.startswith("-") and text.replace("-", "").isdigit():
            target_id = int(text)
            
            # Якщо це чат супергрупи (зазвичай починається на -100)
            if text.startswith("-100"):
                # Запитуємо користувача, що це за ID, щоб не переплутати
                builder = InlineKeyboardBuilder()
                builder.row(types.InlineKeyboardButton(text="💬 Зробити Головним чатом", callback_data=f"setmain_{target_id}"))
                builder.row(types.InlineKeyboardButton(text="📢 Додати як Канал підписки", callback_data=f"setchan_{target_id}"))
                await message.answer(f"❓ Яку роль призначити для ID `{target_id}`?", reply_markup=builder.as_markup())
            else:
                await message.answer("❌ Некоректний формат ID. ID чатів та каналів у Telegram мають починатися з `-100`.")
                
        # Якщо Супер-адмін ввів просто цифри (ID субадміна)
        elif text.isdigit() and message.from_user.id == SUPER_ADMIN_ID:
            new_adm = int(text)
            if new_adm not in config["admins"]:
                config["admins"].append(new_adm)
                save_config(config)
                await message.answer(f"✅ Користувача `{new_adm}` додано в адміни бота!", reply_markup=get_admin_keyboard(message.from_user.id))
            else:
                await message.answer("ℹ️ Він вже є у списку адмінів.", reply_markup=get_admin_keyboard(message.from_user.id))

# --- ДОДАТКОВІ КНОПКИ ДЛЯ ВИЗНАЧЕННЯ РОЛІ ID ---
@dp.callback_query(lambda c: c.data.startswith("setmain_") or c.data.startswith("setchan_"))
async def save_role(callback: types.CallbackQuery):
    u_id = str(callback.from_user.id)
    action, target_id = callback.data.split("_")
    target_id = int(target_id)
    
    if action == "setmain":
        config["main_chats"][u_id] = target_id
                
