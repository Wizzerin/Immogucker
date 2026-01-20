import asyncio
import os
import logging
import random
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from app.bot.handlers import router
from app.bot.keyboards import get_listing_keyboard
from app.bot.middleware import ThrottlingMiddleware
from app.core.database import Base, engine, SessionLocal
from app.core.service import ImmoService
from app.models.settings import Settings  # Нам нужно читать настройки всех юзеров

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def scanner_loop(bot: Bot):
    logger.info("🔄 Multi-User Scanner gestartet...")

    while True:
        db = SessionLocal()
        try:
            # 1. Получаем список ВСЕХ пользователей, у которых есть настройки
            all_users = db.query(Settings).all()

            if not all_users:
                logger.info("💤 Keine aktiven Nutzer (Нет пользователей).")

            # 2. Проходим по каждому пользователю отдельно
            service = ImmoService(db)

            for user_setting in all_users:
                try:
                    # Пропускаем, если нет ссылки
                    if not user_setting.search_url:
                        continue

                    # Ищем квартиры персонально для этого юзера
                    new_flats = await service.process_user(
                        user_id=user_setting.user_id,
                        search_url=user_setting.search_url
                    )

                    # Отправляем уведомления (если нашли)
                    if new_flats:
                        logger.info(f"🔥 User {user_setting.user_id}: {len(new_flats)} neue Angebote!")
                        for flat in new_flats:
                            text = (
                                f"🏠 <b>Neues Angebot!</b>\n\n"
                                f"💶 <b>Preis:</b> {flat['preis']} €\n"
                                f"📏 <b>Größe:</b> {flat['flaeche']} m²\n"
                                f"📝 <b>Titel:</b> {flat['titel']}\n\n"
                                f"<a href='{flat['link']}'>👉 Zum Angebot öffnen</a>"
                            )
                            # Шлем конкретному пользователю!
                            try:
                                # ВАЖНО: Передаем ID из базы (flat['db_id']) в клавиатуру
                                kb = get_listing_keyboard(link=flat['link'], flat_id=flat['db_id'])

                                await bot.send_message(chat_id=user_setting.user_id, text=text, parse_mode="HTML", reply_markup=kb)
                            except Exception as e:
                                logger.error(f"❌ Не смог отправить юзеру {user_setting.user_id}: {e}")

                    # Маленькая пауза между юзерами, чтобы не банили прокси (1-2 сек)
                    await asyncio.sleep(2)

                except Exception as user_error:
                    logger.error(f"❌ Ошибка у юзера {user_setting.user_id}: {user_error}")

        except Exception as e:
            logger.error(f"❌ Глобальная ошибка сканера: {e}")

        finally:
            db.close()

        # Ждем 60 секунд перед следующим кругом
        wait_time = random.randint(200, 400)
        logger.info(f"💤 Schlafe für {wait_time} Sekunden...")
        await asyncio.sleep(wait_time)


async def main():
    Base.metadata.create_all(bind=engine)

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("Error: BOT_TOKEN not found")
        return

    bot = Bot(token=bot_token)
    dp = Dispatcher()
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())
    dp.include_router(router)

    asyncio.create_task(scanner_loop(bot))

    print("🤖 Der Bot läuft für ALLE User!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot gestoppt.")