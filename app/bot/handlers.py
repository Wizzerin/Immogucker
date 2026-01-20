from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import asyncio
from app.bot.callbacks import FavCallback
from app.bot.keyboards import get_listing_keyboard, get_fav_keyboard, BTN_FAVORITES, get_main_keyboard, BTN_SEARCH, \
    BTN_PROFILE, BTN_HELP
from app.bot.states import UserState
from app.core.database import SessionLocal
from app.models.settings import Settings
from app.models.favorites import Favorite
from app.models.immobilien import Immobilie
from app.providers.wg_gesucht import WGGesuchtProvider
from app.providers.immoscout import ImmoscoutProvider
from sqlalchemy import func

router = Router()


# --- 1. START ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        f"🇩🇪 <b>Willkommen bei ImmoGucker!</b>\n\n"
        f"Ich helfe dir, die perfekte Wohnung zu finden.\n"
        f"Nutze das Menü unten, um zu beginnen.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )


# --- 2. SUCHE EINRICHTEN ---
@router.message(F.text == BTN_SEARCH)
async def cmd_setup_search(message: Message, state: FSMContext):
    await message.answer(
        "⚙️ <b>Suchauftrag konfigurieren</b>\n\n"
        "Bitte sende mir jetzt den <b>Link</b> von WG-Gesucht.\n"
        "1. Gehe auf wg-gesucht.de\n"
        "2. Wähle Stadt und Filter\n"
        "3. Kopiere den Link und sende ihn mir hier.",
        parse_mode="HTML"
    )
    await state.set_state(UserState.waiting_for_link)


# --- 3. PROFIL (ИСПРАВЛЕНО) ---
@router.message(F.text == BTN_PROFILE)
async def cmd_profile(message: Message):
    user_id = message.from_user.id  # ID того, кто нажал кнопку
    db = SessionLocal()

    # --- ИСПРАВЛЕНИЕ: Ищем настройки ИМЕННО ЭТОГО пользователя ---
    settings = db.query(Settings).filter(Settings.user_id == user_id).first()
    db.close()

    if settings and settings.search_url:
        await message.answer(
            f"👤 <b>Dein Profil</b>\n\n"
            f"🆔 <b>User ID:</b> {user_id}\n"
            f"✅ <b>Status:</b> Aktiv\n"
            f"🔗 <b>Aktueller Link:</b>\n{settings.search_url}",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "👤 <b>Dein Profil</b>\n\n"
            "❌ Du hast noch keine Suche eingerichtet.",
            parse_mode="HTML"
        )


# --- 4. HILFE ---
@router.message(F.text == BTN_HELP)
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ <b>Hilfe & FAQ</b>\n\n"
        "Ich prüfe alle 60 Sekunden, ob es neue Wohnungen gibt.\n"
        "Jeder Benutzer hat seine eigenen Einstellungen.",
        parse_mode="HTML"
    )


# --- 5. ОБРАБОТКА ССЫЛКИ (ИСПРАВЛЕНО) ---
@router.message(UserState.waiting_for_link)
async def process_link(message: Message, state: FSMContext):
    link = message.text.strip()
    user_id = message.from_user.id  # ID отправителя

    if "wg-gesucht.de" not in link and "scout24" not in link:
        await message.answer("⚠️ Das ist kein gültiger WG-Gesucht oder ImmoScout Link.")
        return

    # Сохраняем в БД
    db = SessionLocal()

    # --- ИСПРАВЛЕНИЕ: Ищем запись ЭТОГО юзера ---
    settings = db.query(Settings).filter(Settings.user_id == user_id).first()

    if not settings:
        # Если записи нет - создаем новую
        settings = Settings(search_url=link, user_id=user_id)
        db.add(settings)
        print(f"🆕 Neue User-Settings erstellt für ID {user_id}")
    else:
        # Если есть - обновляем ЕГО запись
        settings.search_url = link
        print(f"🔄 User-Settings aktualisiert für ID {user_id}")

    db.commit()
    db.close()

    await message.answer("✅ <b>Link gespeichert!</b> Ich teste die Verbindung...", parse_mode="HTML")

    # Тест
    try:
        provider = None
        if "scout24" in link:
            provider = ImmoscoutProvider()  # Nimm den Browser für Scout24
        else:
            provider = WGGesuchtProvider()  # Nimm Requests für WG-Gesucht

        items = await provider.fetch_listings(url=link)
        count = len(items)

        await message.answer(
            f"🎉 <b>Erfolg!</b>\n"
            f"Ich sehe aktuell <b>{count} Angebote</b> für deinen Link.\n"
            f"Suche ist aktiv!",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        await message.answer(f"⚠️ Fehler beim Testen: {e}")
        # Logge den Fehler für dich als Admin
        print(f"❌ Test-Fehler: {e}")

    await state.clear()


# --- 1. ПОКАЗАТЬ ИЗБРАННОЕ ---
@router.message(F.text == BTN_FAVORITES)
async def cmd_show_favorites(message: Message):
    user_id = message.from_user.id
    db = SessionLocal()

    # Получаем все избранные пользователя
    favs = db.query(Favorite).filter(Favorite.user_id == user_id).all()

    if not favs:
        await message.answer("⭐️ <b>Deine Favoritenliste ist leer.</b>", parse_mode="HTML")
        db.close()
        return

    await message.answer(f"⭐️ <b>Du hast {len(favs)} Wohnungen gespeichert:</b>", parse_mode="HTML")

    for fav in favs:
        # Для каждой избранной записи подгружаем данные квартиры
        flat = fav.immobilie

        # Считаем, сколько людей ВСЕГО лайкнули эту квартиру (популярность)
        count_likes = db.query(func.count(Favorite.id)).filter(Favorite.immobilie_id == flat.id).scalar()

        text = (
            f"🏠 <b>{flat.titel}</b>\n"
            f"💶 {flat.kaltmiete} € | 📏 {flat.flaeche} m²\n"
            f"🔥 <i>Interessenten: {count_likes}</i>"  # <--- Показываем интерес
        )

        await message.answer(
            text,
            reply_markup=get_fav_keyboard(flat_id=flat.id, link=flat.link),
            parse_mode="HTML"
        )
        # Небольшая задержка, чтобы не зафлудить
        await asyncio.sleep(0.3)

    db.close()


# --- 2. ДОБАВИТЬ В ИЗБРАННОЕ (Нажатие на ❤️) ---
@router.callback_query(FavCallback.filter(F.action == "add"))
async def cb_add_fav(callback: CallbackQuery, callback_data: FavCallback):
    flat_id = callback_data.id
    user_id = callback.from_user.id

    db = SessionLocal()

    # Проверяем, не добавлено ли уже
    exists = db.query(Favorite).filter(
        Favorite.user_id == user_id,
        Favorite.immobilie_id == flat_id
    ).first()

    if exists:
        await callback.answer("⚠️ Bereits in Favoriten! (Уже в избранном)", show_alert=True)
    else:
        new_fav = Favorite(user_id=user_id, immobilie_id=flat_id)
        db.add(new_fav)
        db.commit()
        await callback.answer("✅ Gespeichert! (Сохранено)")

    db.close()


# --- 3. УДАЛИТЬ ИЗ ИЗБРАННОГО (Нажатие на 🗑) ---
@router.callback_query(FavCallback.filter(F.action == "del"))
async def cb_del_fav(callback: CallbackQuery, callback_data: FavCallback):
    flat_id = callback_data.id
    user_id = callback.from_user.id

    db = SessionLocal()

    fav = db.query(Favorite).filter(
        Favorite.user_id == user_id,
        Favorite.immobilie_id == flat_id
    ).first()

    if fav:
        db.delete(fav)
        db.commit()
        await callback.answer("🗑 Gelöscht! (Удалено)")
        # Удаляем сообщение из чата визуально
        await callback.message.delete()
    else:
        await callback.answer("❌ Fehler: Nicht gefunden.")

    db.close()