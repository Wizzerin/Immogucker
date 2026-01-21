from aiogram import Router, F, types

from app.bot.keyboards import get_profile_keyboard
from app.core.database import SessionLocal
from app.models.favorites import Favorite
from app.models.settings import Settings

router = Router()


@router.callback_query(F.data.startswith("like_"))
async def handle_like(callback: types.CallbackQuery):
    flat_id = int(callback.data.split("_")[1])
    db = SessionLocal()
    try:
        exists = db.query(Favorite).filter(
            Favorite.user_id == callback.from_user.id,
            Favorite.immobilie_id == flat_id
        ).first()

        if not exists:
            fav = Favorite(user_id=callback.from_user.id, immobilie_id=flat_id)
            db.add(fav)
            db.commit()

            await callback.message.edit_text(
                f"{callback.message.html_text}\n\n✅ <b>Gespeichert!</b>",
                parse_mode="HTML",
                reply_markup=None
            )
            await callback.answer("Gespeichert!")
        else:
            await callback.answer("Bereits in Favoriten!")
    except Exception as e:
        print(f"Like Error: {e}")
        await callback.answer("Fehler")
    finally:
        db.close()


@router.callback_query(F.data.startswith("dislike_"))
async def handle_dislike(callback: types.CallbackQuery):
    flat_id = int(callback.data.split("_")[1])
    db = SessionLocal()
    try:
        # Пытаемся удалить из базы (если это избранное)
        db.query(Favorite).filter(
            Favorite.user_id == callback.from_user.id,
            Favorite.immobilie_id == flat_id
        ).delete()
        db.commit()
    except Exception as e:
        print(f"Dislike Error: {e}")
    finally:
        db.close()

    # Удаляем сообщение из чата
    await callback.message.delete()
    await callback.answer("Entfernt")

@router.callback_query(F.data == "check_sub")
async def handle_sub_check(callback: types.CallbackQuery):
    # Сюда код попадет ТОЛЬКО если Middleware пропустил юзера (значит, он подписан)
    await callback.message.delete() # Удаляем сообщение с требованием подписки
    await callback.message.answer("✅ <b>Danke!</b> Du kannst den Bot jetzt nutzen.", parse_mode="HTML")
    # Можно сразу показать меню
    from app.bot.keyboards import get_main_keyboard
    await callback.message.answer("Was möchtest du tun?", reply_markup=get_main_keyboard())


@router.callback_query(F.data.in_({"del_wg", "del_immo", "del_iw", "del_ka"}))
async def delete_search_link(callback: types.CallbackQuery):
    action = callback.data
    db = SessionLocal()

    try:
        settings = db.query(Settings).filter(Settings.user_id == callback.from_user.id).first()

        if not settings:
            await callback.answer("Fehler: Profil nicht gefunden.")
            return

        deleted_name = ""

        if action == "del_wg":
            settings.wg_url = None
            deleted_name = "WG-Gesucht"
        elif action == "del_immo":
            settings.immo_url = None
            deleted_name = "ImmoScout24"
        elif action == "del_iw":
            settings.immowelt_url = None
            deleted_name = "Immowelt"
        elif action == "del_ka":
            settings.kleinanzeigen_url = None
            deleted_name = "Kleinanzeigen"

        db.commit()

        # Обновляем текст сообщения и клавиатуру (убираем нажатую кнопку)
        wg_state = "✅ Aktiv" if settings.wg_url else "❌ Inaktiv"
        immo_state = "✅ Aktiv" if settings.immo_url else "❌ Inaktiv"
        iw_state = "✅ Aktiv" if settings.immowelt_url else "❌ Inaktiv"
        ka_state = "✅ Aktiv" if settings.kleinanzeigen_url else "❌ Inaktiv"

        text = (
            f"📋 <b>Dein Suchprofil</b>\n\n"
            f"🔸 <b>WG-Gesucht:</b> {wg_state}\n"
            f"🔹 <b>ImmoScout24:</b> {immo_state}\n"
            f"🟡 <b>Immowelt:</b> {iw_state}\n"
            f"🟢 <b>Kleinanzeigen:</b> {ka_state}\n\n"
            f"<i>Sende einen neuen Link, um die Suche zu ändern, oder nutze die Buttons unten zum Löschen.</i>"
        )

        new_kb = get_profile_keyboard(settings)

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=new_kb, disable_web_page_preview=True)
        await callback.answer(f"✅ {deleted_name} gelöscht!")

    except Exception as e:
        print(f"Delete Error: {e}")
        await callback.answer("Fehler beim Löschen.")
    finally:
        db.close()


@router.callback_query(F.data == "close_profile")
async def close_profile(callback: types.CallbackQuery):
    await callback.message.delete()