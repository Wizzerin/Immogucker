import asyncio
import os
import logging
import random
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv


# === ИМПОРТЫ ===
from app.bot.handlers import router as handlers_router
from app.bot.callbacks import router as callbacks_router
from app.bot.keyboards import get_listing_keyboard
from app.bot.middleware import ThrottlingMiddleware, SubscriptionMiddleware
from app.core.database import Base, engine, SessionLocal
from app.core.service import ImmoService
from app.core.browser import browser_manager
from app.models.settings import Settings

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def scanner_loop(bot: Bot):
    logger.info("🔄 Multi-User Scanner gestartet...")
    while True:
        db = SessionLocal()
        try:
            all_users = db.query(Settings).all()
            if not all_users:
                logger.info("💤 Keine aktiven Nutzer.")

            service = ImmoService(db)

            for user_setting in all_users:
                tasks = []
                if user_setting.wg_url: tasks.append(user_setting.wg_url)
                if user_setting.immo_url: tasks.append(user_setting.immo_url)
                if user_setting.immowelt_url: tasks.append(user_setting.immowelt_url)
                if user_setting.kleinanzeigen_url: tasks.append(user_setting.kleinanzeigen_url)

                if not tasks: continue

                for url in tasks:
                    try:
                        new_flats = await service.process_user(user_setting.user_id, url)
                        if new_flats:
                            logger.info(f"🔥 User {user_setting.user_id}: {len(new_flats)} neue Angebote!")
                            for flat in new_flats:
                                text = (
                                    f"✨ <b>Neues Angebot auf {flat['quelle']}</b>\n\n"
                                    f"<b>{flat['titel']}</b>\n"
                                    f"───────────────\n"
                                    f"💶 <b>{flat['preis']} €</b>   |   📏 <b>{flat['flaeche']} m²</b>\n"
                                    f"───────────────\n"
                                    f"<a href='{flat['link']}'>👉 Hier klicken zum Öffnen</a>"
                                )
                                try:
                                    kb = get_listing_keyboard(link=flat['link'], flat_id=flat['db_id'])
                                    await bot.send_message(
                                        chat_id=user_setting.user_id,
                                        text=text,
                                        parse_mode="HTML",
                                        reply_markup=kb,
                                        disable_web_page_preview=False
                                    )
                                except Exception as e:
                                    logger.error(f"❌ Sende-Fehler: {e}")

                        await asyncio.sleep(5)
                    except Exception as e:
                        logger.error(f"❌ Scan-Fehler ({url}): {e}")

        except Exception as e:
            logger.error(f"❌ Globaler Fehler: {e}")
        finally:
            db.close()

        wait_time = random.randint(300, 420)
        logger.info(f"💤 Schlafe für {wait_time} Sekunden...")
        await asyncio.sleep(wait_time)


async def main():
    Base.metadata.create_all(bind=engine)
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("Error: BOT_TOKEN fehlt!")
        return

    bot = Bot(token=bot_token)
    dp = Dispatcher()


    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())

    # Потом проверка подписки (Gatekeeper)
    # Применяем и к сообщениям, и к кнопкам
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())

    # === РЕГИСТРАЦИЯ РОУТЕРОВ ===
    dp.include_router(handlers_router)
    dp.include_router(callbacks_router)  # <--- Кнопки должны быть тут!

    asyncio.create_task(scanner_loop(bot))

    print("🤖 Bot gestartet (Persistent Browser Mode)!")
    try:
        await dp.start_polling(bot)
    finally:
        # Эта часть сработает при остановке
        print("🛑 Остановка... Закрываю браузер.")
        await browser_manager.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot gestoppt.")