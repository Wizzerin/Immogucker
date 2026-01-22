import os
import datetime
import logging
import asyncio
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker

from app.core.database import SessionLocal, engine
from app.models.sent import SentListing
from app.models.settings import Settings
from app.models.favorites import Favorite
from app.models.immobilien import Immobilie
from app.models.voucher import Voucher
from app.core.service import ImmoService, health_status
from app.core.voucher_service import create_voucher, redeem_voucher
from app.core.browser import browser_manager
from app.bot.keyboards import get_listing_keyboard, get_main_keyboard, get_profile_keyboard

router = Router()
logger = logging.getLogger(__name__)


# Хелпер для настроек
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


# === КНОПКА: SUCHE EINRICHTEN ===
@router.message(F.text == "🔍 Suche einrichten")
async def btn_search(message: types.Message):
    await message.answer(
        "Sende mir jetzt einen Link von:\n"
        "🔸 WG-Gesucht\n"
        "🔹 ImmoScout24\n"
        "🟡 Immowelt\n"
        "🟢 Kleinanzeigen"
    )


# === КНОПКА: MEIN PROFIL ===
@router.message(F.text == "👤 Mein Profil")
@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    db = SessionLocal()
    settings = get_or_create_settings(db, message.from_user.id)

    # [UI UPDATE] Чистый статус
    status = "Free User"
    if settings.is_premium:
        if settings.premium_until:
            date_str = settings.premium_until.strftime("%d.%m.%Y")
            status = f"Premium (bis {date_str})"
        else:
            status = "Premium (Lifetime)"

    # [UI UPDATE] Убраны галочки/крестики, заменены на текст
    info = (
        f"👤 <b>Dein Profil</b>\n\n"
        f"Status: <b>{status}</b>\n"
        f"───────────────\n"
        f"WG-Gesucht: {'Aktiv' if settings.wg_url else '-'}\n"
        f"ImmoScout: {'Aktiv' if settings.immo_url else '-'}\n"
        f"Immowelt: {'Aktiv' if settings.immowelt_url else '-'}\n"
        f"Kleinanzeigen: {'Aktiv' if settings.kleinanzeigen_url else '-'}\n\n"
        f"<i>Code einlösen: /redeem [CODE]</i>"
    )
    await message.answer(info, parse_mode="HTML")
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

        await message.answer(f"⭐ <b>Gespeicherte Wohnungen ({len(favs)}):</b>", parse_mode="HTML")

        for flat in favs:
            # [UI UPDATE] Убраны лишние эмодзи
            text = (
                f"🏠 <b>{flat.titel}</b>\n"
                f"Preis: {flat.kaltmiete} € | Fläche: {flat.flaeche} m²\n"
                # Ссылка теперь в кнопке
            )
            # Используем твою функцию клавиатуры, передаем только ссылку и id
            kb = get_listing_keyboard(flat.link, flat.id)
            await message.answer(text, parse_mode="HTML", reply_markup=kb)

    except Exception as e:
        await message.answer(f"❌ Fehler: {e}")
    finally:
        db.close()


# === КНОПКА: HILFE ===
@router.message(F.text == "ℹ️ Hilfe")
async def btn_help(message: types.Message):
    await message.answer(
        "ℹ️ <b>Hilfe</b>\n\n"
        "1. Klicke auf <b>'Suche einrichten'</b>.\n"
        "2. Sende einen Link von:\n"
        "   • ImmoScout24\n"
        "   • WG-Gesucht\n"
        "   • Immowelt\n"
        "   • Kleinanzeigen\n"
        "3. Ich suche automatisch alle 5-10 Minuten nach neuen Angeboten.\n\n"
        "Wenn du ein Angebot merkst (⭐), landet es in deinen Favoriten.",
        parse_mode="HTML"
    )


# === [NEW] BROADCAST (РАССЫЛКА) ===
@router.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):
    ADMIN_ID = 515664298  # Твой ID
    if message.from_user.id != ADMIN_ID:
        return

    # /broadcast Текст
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("ℹ️ Nutzung: `/broadcast Deine Nachricht`", parse_mode="Markdown")
        return

    text_to_send = parts[1]

    db = SessionLocal()
    users = db.query(Settings).all()
    count_success = 0
    count_fail = 0

    status_msg = await message.answer(f"⏳ Sende Nachricht an {len(users)} Nutzer...")

    for user in users:
        try:
            final_text = f"📢 <b>Mitteilung von Immogucker</b>\n\n{text_to_send}"
            await message.bot.send_message(user.user_id, final_text, parse_mode="HTML")
            count_success += 1
        except Exception:
            count_fail += 1

        await asyncio.sleep(0.05)  # Пауза, чтобы не забанили

    await status_msg.edit_text(
        f"✅ <b>Fertig</b>\n\n"
        f"Erfolg: {count_success}\n"
        f"Fehler: {count_fail}",
        parse_mode="HTML"
    )
    db.close()


# === АДМИНКА (СТАРАЯ КОМАНДА) ===
@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    # ! ВАЖНО: Тут была проверка через os.getenv, но лучше по ID
    if message.from_user.id != 515664298:
        return

    db = SessionLocal()
    try:
        total_users = db.query(Settings).count()
        # active_users = db.query(Settings).filter(Settings.is_active == True).count() # Если поля нет, убрать

        wg_count = db.query(Settings).filter(Settings.wg_url != None).count()
        immo_count = db.query(Settings).filter(Settings.immo_url != None).count()
        iw_count = db.query(Settings).filter(Settings.immowelt_url != None).count()
        ka_count = db.query(Settings).filter(Settings.kleinanzeigen_url != None).count()

        total_tasks = wg_count + immo_count + iw_count + ka_count

        text = (
            f"👑 <b>Admin-Panel</b>\n\n"
            f"Nutzer: {total_users}\n"
            f"Suchaufträge: {total_tasks}\n\n"
            f"WG: {wg_count} | IS24: {immo_count}\n"
            f"IW: {iw_count} | KA: {ka_count}\n"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Рассылка (через /broadcast)", callback_data="admin_broadcast")]
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
        active_links = 0
        if settings.wg_url: active_links += 1
        if settings.immo_url: active_links += 1
        if settings.immowelt_url: active_links += 1
        if settings.kleinanzeigen_url: active_links += 1

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

        if not settings.is_premium:
            is_update = False
            if new_type == "wg" and settings.wg_url: is_update = True
            if new_type == "immo" and settings.immo_url: is_update = True
            if new_type == "iw" and settings.immowelt_url: is_update = True
            if new_type == "ka" and settings.kleinanzeigen_url: is_update = True

            if active_links >= 1 and not is_update:
                await message.answer(
                    "🔒 <b>Limit erreicht</b>\n\n"
                    "Als Free-User kannst du nur <b>eine</b> Suche gleichzeitig aktiv haben.\n"
                    "Nutze <code>/profile</code> für mehr Infos oder Upgrade.",
                    parse_mode="HTML"
                )
                return

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
        await message.answer(f"✅ <b>{saved_type}</b> gespeichert.\nSuche läuft...", parse_mode="HTML")

        # === ЗАПУСК ПОИСКА И ОТПРАВКА ===
        service = ImmoService(db)
        new_flats = await service.process_user(message.from_user.id, url)

        if new_flats:
            await message.answer(f"🔎 {len(new_flats)} Angebote gefunden:")
            for flat in new_flats:
                # [UI UPDATE] Чистый дизайн
                text = (
                    f"🏠 <b>{flat['quelle']}</b>\n\n"
                    f"{flat['titel']}\n"
                    f"───────────────\n"
                    f"Preis: <b>{flat['preis']} €</b>\n"
                    f"Fläche: <b>{flat['flaeche']} m²</b>\n"
                )
                try:
                    kb = get_listing_keyboard(link=flat['link'], flat_id=flat['db_id'])
                    await message.answer(
                        text=text,
                        parse_mode="HTML",
                        reply_markup=kb,
                        disable_web_page_preview=True  # Отключаем превью, чтобы было чище
                    )
                except Exception as e:
                    print(f"Send error: {e}")
        else:
            await message.answer("🔎 Aktuell keine neuen Angebote. Ich melde mich, sobald etwas reinkommt!")

    except Exception as e:
        await message.answer(f"❌ Fehler: {e}")
    finally:
        db.close()


# === PROMO (СТАРАЯ КОМАНДА) ===
@router.message(Command("promo"))
async def cmd_promo(message: types.Message):
    admin_id = 515664298
    if message.from_user.id != admin_id: return

    try:
        args = message.text.split()
        if len(args) != 3:
            await message.answer("⚠️ Format: /promo <user_id> <days>")
            return

        target_id = int(args[1])
        days = int(args[2])

        db = SessionLocal()
        settings = db.query(Settings).filter(Settings.user_id == target_id).first()

        if not settings:
            settings = Settings(user_id=target_id)
            db.add(settings)

        settings.is_premium = True
        # Исправляем возможную ошибку с типами дат, если она была
        if not settings.premium_until:
            settings.premium_until = datetime.datetime.now()

        settings.premium_until += datetime.timedelta(days=days)

        db.commit()

        await message.answer(f"✅ Premium für User {target_id} aktiviert ({days} Tage).")
        db.close()
    except Exception as e:
        await message.answer(f"Error: {e}")


# === HEALTH CHECK (ADMIN) ===
@router.message(Command("health"))
async def cmd_health(message: types.Message):
    if message.from_user.id != 515664298: return

    if not health_status:
        await message.answer("💤 <b>Status:</b> Noch keine Scans durchgeführt.", parse_mode="HTML")
        return

    lines = ["🏥 <b>System Status</b>", ""]

    for provider, data in health_status.items():
        state_symbol = "OK"
        if "Leer" in data['status']: state_symbol = "Leer"
        if "ERROR" in data['status']: state_symbol = "ERR"

        # [UI UPDATE] Минимализм
        lines.append(f"<b>{provider}</b>: {state_symbol}")
        lines.append(f"└ {data['time']} | {data['msg']}")

    browser_state = "UP" if browser_manager.driver else "DOWN"
    lines.append("")
    lines.append(f"Browser: <b>{browser_state}</b>")

    await message.answer("\n".join(lines), parse_mode="HTML")


# === [ADMIN] СОЗДАНИЕ КОДА ===
@router.message(Command("create_code"))
async def cmd_create_code(message: types.Message):
    ADMIN_ID = 515664298
    if message.from_user.id != ADMIN_ID: return

    args = message.text.split()
    days = 30
    if len(args) > 1 and args[1].isdigit():
        days = int(args[1])

    db = SessionLocal()
    try:
        code = create_voucher(db, days)
        await message.answer(f"🎫 <b>Code ({days} Tage):</b>\n<code>{code}</code>", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Fehler: {e}")
    finally:
        db.close()


# === [USER] АКТИВАЦИЯ КОДА ===
@router.message(Command("redeem"))
async def cmd_redeem(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("ℹ️ Nutzung: <code>/redeem CODE</code>", parse_mode="HTML")
        return

    code = args[1].strip().upper()
    db = SessionLocal()

    try:
        result_text = redeem_voucher(db, message.from_user.id, code)
        await message.answer(result_text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Fehler: {e}")
    finally:
        db.close()


# === [ADMIN] СТАТИСТИКА ===
@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    ADMIN_ID = 515664298
    if message.from_user.id != ADMIN_ID: return

    db = SessionLocal()
    try:
        total_users = db.query(Settings).count()
        premium_users = db.query(Settings).filter(Settings.is_premium == True).count()
        free_users = total_users - premium_users

        wg_count = db.query(Settings).filter(Settings.wg_url != None).count()
        immo_count = db.query(Settings).filter(Settings.immo_url != None).count()
        iw_count = db.query(Settings).filter(Settings.immowelt_url != None).count()
        ka_count = db.query(Settings).filter(Settings.kleinanzeigen_url != None).count()

        total_searches = wg_count + immo_count + iw_count + ka_count
        total_sent = db.query(SentListing).count()

        text = (
            f"📊 <b>Statistik</b>\n"
            f"───────────────\n"
            f"Nutzer: <b>{total_users}</b> (P: {premium_users} / F: {free_users})\n"
            f"Exposés gesendet: <b>{total_sent}</b>\n\n"
            f"<b>Aktive Suchen</b>\n"
            f"WG: {wg_count} | KA: {ka_count}\n"
            f"IS24: {immo_count} | IW: {iw_count}"
        )

        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Fehler: {e}")
    finally:
        db.close()