from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from app.bot.callbacks import FavCallback
# --- Тексты кнопок (Konstanten) ---
BTN_SEARCH = "🔍 Suche einrichten"  # Настроить поиск
BTN_PROFILE = "👤 Mein Profil"       # Мой профиль
BTN_FAVORITES = "⭐ Favoriten"
BTN_HELP = "ℹ️ Hilfe"                # Помощь

def get_main_keyboard():
    kb = [
        # Первый ряд: Поиск и Избранное
        [KeyboardButton(text=BTN_SEARCH), KeyboardButton(text=BTN_FAVORITES)],
        # Второй ряд: Профиль и Помощь
        [KeyboardButton(text=BTN_PROFILE), KeyboardButton(text=BTN_HELP)]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# Клавиатура под сообщением с квартирой
def get_listing_keyboard(link: str, flat_id: int):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌐 Öffnen", url=link),
            # Кнопка с колбеком: action="add", id=flat_id
            InlineKeyboardButton(
                text="❤️ Merken",
                callback_data=FavCallback(action="add", id=flat_id).pack()
            )
        ]
    ])
    return kb

# Клавиатура для списка избранного (Кнопка удалить)
def get_fav_keyboard(flat_id: int, link: str):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌐 Öffnen", url=link),
            InlineKeyboardButton(
                text="🗑 Löschen",
                callback_data=FavCallback(action="del", id=flat_id).pack()
            )
        ]
    ])
    return kb