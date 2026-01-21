import os
import datetime
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.core.database import SessionLocal
from app.models.settings import Settings
from app.models.favorites import Favorite
from app.models.immobilien import Immobilie
from app.core.service import ImmoService
from app.bot.keyboards import get_listing_keyboard, get_main_keyboard, get_profile_keyboard

router = Router()


def get_or_create_settings(session, user_id):
    settings = session.query(Settings).filter(Settings.user_id == user_id).first()
    if not settings:
        settings = Settings(user_id=user_id)
        session.add(settings)
        session.commit()
    return settings


# === КОМАНДА /START ===
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Hallo! Ich bin ImmoGucker.\n"
        "Nutze das Menü unten, um mich zu steuern.",
        reply_markup=get_main_keyboard()
    )


# === КНОПКА: SUCHE EINRICHTEN (Исправлено) ===
@router.message(F.text == "🔍 Suche einrichten")
async def btn_search(message: types.Message):
    await message.answer(
        "Sende mir jetzt einen Link von:\n"
        "🔸 **WG-Gesucht**\n"
        "🔹 **ImmoScout24**\n"
        "🟡 **Immowelt**\n"
        "🟢 **Kleinanzeigen**"
    )


# === КНОПКА: MEIN PROFIL ===
@router.message(F.text == "👤 Mein Profil")
@router.message(Command("profile"))
async def btn_profile(message: types.Message):
    db = SessionLocal()
    try:
        settings = get_or_create_settings(db, message.from_user.id)

        # Проверяем, не истек ли премиум
        if settings.is_premium and settings.premium_until:
            if settings.premium_until < datetime.date.today():
                settings.is_premium = False
                settings.premium_until = None
                db.commit()

        # Формируем статус
        if settings.is_premium:
            status = f"🌟 <b>PREMIUM</b> (bis {settings.premium_until})"
        else:
            status = "🆓 <b>Kostenlos</b> (Max. 1 Suche)"

        wg_state = "✅" if settings.wg_url else "❌"
        immo_state = "✅" if settings.immo_url else "❌"
        iw_state = "✅" if settings.immowelt_url else "❌"
        ka_state = "✅" if settings.kleinanzeigen_url else "❌"

        text = (
            f"📋 <b>Dein Suchprofil</b>\n"
            f"Status: {status}\n\n"
            f"🔸 WG-Gesucht: {wg_state}\n"
            f"🔹 ImmoScout24: {immo_state}\n"
            f"🟡 Immowelt: {iw_state}\n"
            f"🟢 Kleinanzeigen: {ka_state}\n\n"
            f"🔗 {settings.wg_url or settings.immo_url or settings.immowelt_url or settings.kleinanzeigen_url or 'Keine Links'}\n\n"
            f"<i>Sende einen neuen Link zum Hinzufügen/Ändern.</i>"
        )

        kb = get_profile_keyboard(settings)
        await message.answer(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
    finally:
        db.close()


# === КНОПКА: FAVORITEN ===
@router.message(F.text == "⭐ Favoriten")
async def btn_favorites(message: types.Message):
    db = SessionLocal()
    try:
        favs = db.query(Immobilie).join(Favorite, Favorite.immobilie_id == Immobilie.id) \
            .filter(Favorite.user_id == message.from_user.id).all()

        if not favs:
            await message.answer("📭 Deine Favoritenliste ist leer.")
            return

        await message.answer(f"⭐ **Gespeicherte Wohnungen ({len(favs)}):**")

        for flat in favs:
            text = (
                f"🏠 <b>{flat.titel}</b>\n"
                f"💶 {flat.kaltmiete} € | 📏 {flat.flaeche} m²\n"
                f"<a href='{flat.link}'>Link öffnen</a>"
            )
            kb = get_listing_keyboard(flat.link, flat.id)
            await message.answer(text, parse_mode="HTML", reply_markup=kb)

    except Exception as e:
        await message.answer(f"❌ Fehler: {e}")
    finally:
        db.close()


# === КНОПКА: HILFE (Исправлено) ===
@router.message(F.text == "ℹ️ Hilfe")
async def btn_help(message: types.Message):
    await message.answer(
        "ℹ️ **Hilfe**\n\n"
        "1. Klicke auf **'Suche einrichten'**.\n"
        "2. Sende einen Link von:\n"
        "   • ImmoScout24\n"
        "   • WG-Gesucht\n"
        "   • Immowelt\n"
        "   • Kleinanzeigen\n"
        "3. Ich suche automatisch alle 5-10 Minuten nach neuen Angeboten.\n\n"
        "Wenn du ein Angebot **merkst** (⭐), landet es in deinen **Favoriten**."
    )


# === АДМИНКА ===
@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    admin_id = os.getenv("ADMIN_ID")
    if str(message.from_user.id) != str(admin_id):
        return

    db = SessionLocal()
    try:
        total_users = db.query(Settings).count()
        active_users = db.query(Settings).filter(Settings.is_active == True).count()

        wg_count = db.query(Settings).filter(Settings.wg_url != None).count()
        immo_count = db.query(Settings).filter(Settings.immo_url != None).count()
        iw_count = db.query(Settings).filter(Settings.immowelt_url != None).count()
        ka_count = db.query(Settings).filter(Settings.kleinanzeigen_url != None).count()

        total_tasks = wg_count + immo_count + iw_count + ka_count

        text = (
            f"👑 <b>Admin-Panel</b>\n\n"
            f"👥 <b>Nutzer:</b> {total_users} (Aktiv: {active_users})\n"
            f"🔄 <b>Aktive Suchaufträge:</b> {total_tasks}\n\n"
            f"🔸 WG-Gesucht: {wg_count}\n"
            f"🔹 ImmoScout24: {immo_count}\n"
            f"🟡 Immowelt: {iw_count}\n"
            f"🟢 Kleinanzeigen: {ka_count}\n"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Рассылка (Coming soon)", callback_data="admin_broadcast")]
        ])

        await message.answer(text, parse_mode="HTML", reply_markup=kb)

    except Exception as e:
        await message.answer(f"Error: {e}")
    finally:
        db.close()


# === СОХРАНЕНИЕ ССЫЛКИ ===
@router.message(F.text.contains("http"))
async def save_url(message: types.Message):
    url = message.text.strip()
    db = SessionLocal()

    try:
        settings = get_or_create_settings(db, message.from_user.id)

        # === ПРОВЕРКА PREMIUM ===
        # Считаем, сколько ссылок уже есть
        active_links = 0
        if settings.wg_url: active_links += 1
        if settings.immo_url: active_links += 1
        if settings.immowelt_url: active_links += 1
        if settings.kleinanzeigen_url: active_links += 1

        # Определяем тип новой ссылки
        new_type = None
        if "wg-gesucht.de" in url:
            new_type = "wg"
        elif "immobilienscout24.de" in url:
            new_type = "immo"
        elif "immowelt.de" in url:
            new_type = "iw"
        elif "kleinanzeigen.de" in url:
            new_type = "ka"
        else:
            await message.answer("⚠️ Unbekannter Link.")
            return

        # Если юзер НЕ премиум
        if not settings.is_premium:
            # Если у него уже есть ссылка, и он пытается добавить ДРУГОЙ тип -> Блок
            # (Если он обновляет уже существующую ссылку того же типа - разрешаем)
            is_update = False
            if new_type == "wg" and settings.wg_url: is_update = True
            if new_type == "immo" and settings.immo_url: is_update = True
            if new_type == "iw" and settings.immowelt_url: is_update = True
            if new_type == "ka" and settings.kleinanzeigen_url: is_update = True

            if active_links >= 1 and not is_update:
                await message.answer(
                    "🚫 <b>Limit erreicht!</b>\n\n"
                    "Als Free-User kannst du nur <b>eine</b> Suche gleichzeitig aktiv haben.\n"
                    "Bitte lösche erst die alte Suche im Profil oder upgrade auf Premium.",
                    parse_mode="HTML"
                )
                return

        # Сохранение (как и раньше)
        saved_type = ""
        if new_type == "wg":
            settings.wg_url = url
            saved_type = "WG-Gesucht"
        elif new_type == "immo":
            settings.immo_url = url
            saved_type = "ImmoScout24"
        elif new_type == "iw":
            settings.immowelt_url = url
            saved_type = "Immowelt"
        elif new_type == "ka":
            settings.kleinanzeigen_url = url
            saved_type = "Kleinanzeigen"

        db.commit()
        await message.answer(f"✅ <b>{saved_type}</b> Link gespeichert!\n🔎 Suche läuft...", parse_mode="HTML")

        # Запуск поиска (тот же код)
        service = ImmoService(db)
        new_flats = await service.process_user(message.from_user.id, url)
        # ... (код вывода объявлений оставь как был) ...

    except Exception as e:
        await message.answer(f"❌ Fehler: {e}")
    finally:
        db.close()


@router.message(Command("promo"))
async def cmd_promo(message: types.Message):
    # Проверка админа
    admin_id = os.getenv("ADMIN_ID")
    if str(message.from_user.id) != str(admin_id):
        return

    try:
        # Парсим аргументы: /promo 12345 30
        args = message.text.split()
        if len(args) != 3:
            await message.answer("⚠️ Format: /promo <user_id> <days>")
            return

        target_id = int(args[1])
        days = int(args[2])

        db = SessionLocal()
        settings = db.query(Settings).filter(Settings.user_id == target_id).first()

        if not settings:
            # Если юзера нет в базе, создаем
            settings = Settings(user_id=target_id)
            db.add(settings)

        # Выдаем премиум
        settings.is_premium = True
        settings.premium_until = datetime.date.today() + datetime.timedelta(days=days)
        db.commit()

        await message.answer(f"✅ Premium für User {target_id} aktiviert ({days} Tage).")

        # Опционально: уведомить юзера
        try:
            await message.bot.send_message(target_id, f"🌟 <b>Glückwunsch!</b>\nDu hast {days} Tage Premium erhalten!")
        except:
            pass

        db.close()
    except Exception as e:
        await message.answer(f"Error: {e}")