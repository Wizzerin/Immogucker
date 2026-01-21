from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from app.models.settings import Settings


def get_listing_keyboard(link: str, flat_id: int) -> InlineKeyboardMarkup:
    """Кнопки под объявлением"""
    fid = str(flat_id)
    buttons = [
        [
            InlineKeyboardButton(text="⭐ Merken", callback_data=f"like_{fid}"),
            InlineKeyboardButton(text="🗑 Löschen", callback_data=f"dislike_{fid}")
        ],
        [
            InlineKeyboardButton(text="🔗 Angebot öffnen", url=link)
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню"""
    buttons = [
        [
            KeyboardButton(text="🔍 Suche einrichten"),
            KeyboardButton(text="⭐ Favoriten")
        ],
        [
            KeyboardButton(text="👤 Mein Profil"),
            KeyboardButton(text="ℹ️ Hilfe")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_profile_keyboard(settings: Settings) -> InlineKeyboardMarkup:
    """Кнопки управления в профиле"""
    buttons = []

    # WG-Gesucht
    if settings.wg_url:
        buttons.append([InlineKeyboardButton(text="🗑 WG-Gesucht löschen", callback_data="del_wg")])

    # ImmoScout24
    if settings.immo_url:
        buttons.append([InlineKeyboardButton(text="🗑 ImmoScout24 löschen", callback_data="del_immo")])

    # Immowelt
    if settings.immowelt_url:
        buttons.append([InlineKeyboardButton(text="🗑 Immowelt löschen", callback_data="del_iw")])

    # Kleinanzeigen
    if settings.kleinanzeigen_url:
        buttons.append([InlineKeyboardButton(text="🗑 Kleinanzeigen löschen", callback_data="del_ka")])

    # Кнопка закрыть
    buttons.append([InlineKeyboardButton(text="❌ Schließen", callback_data="close_profile")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)