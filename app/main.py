import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, DATABASE_URL
from app.models.settings import Settings
from app.core.service import ImmoService
from app.core.subscription import subscription_loop
from app.bot.handlers import router, get_listing_keyboard
from app.core.browser import browser_manager

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка БД
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Инициализация бота
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.include_router(router)

# === [NEW] ОГРАНИЧЕНИЕ НА КОЛИЧЕСТВО ОДНОВРЕМЕННЫХ ЗАДАЧ ===
# 3 - оптимально для слабого сервера.
# WG-Gesucht будут летать, а Selenium-задачи (Immo/KA) все равно встанут в очередь
# внутри browser_manager.lock, но не будут блокировать остальных.
CONCURRENT_LIMIT = asyncio.Semaphore(3)


async def check_and_send(service: ImmoService, user_id: int, url: str, platform_name: str):
    """
    Асинхронная функция для проверки одной ссылки.
    Использует семафор, чтобы не запускать 100 проверок одновременно.
    """
    async with CONCURRENT_LIMIT:
        try:
            # Парсинг (здесь внутри может быть ожидание браузера)
            new_flats = await service.process_user(user_id, url)

            if new_flats:
                logger.info(f"🔥 User {user_id}: {len(new_flats)} neue Angebote auf {platform_name}!")

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
                        kb = get_listing_keyboard(link=flat['link'], flat_id=flat.get('db_id'))
                        await bot.send_message(
                            chat_id=user_id,
                            text=text,
                            reply_markup=kb,
                            disable_web_page_preview=False
                        )
                        # Небольшая пауза между сообщениями, чтобы телеграм не забанил за спам
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Send error to {user_id}: {e}")

        except Exception as e:
            logger.error(f"Check error ({platform_name}): {e}")


async def scanner_loop():
    """
    Главный цикл сканирования.
    Создает задачи для всех пользователей и всех их ссылок.
    """
    logger.info("🔄 Async Scanner gestartet...")

    # Создаем таблицы, если их нет (для ваучеров и обновлений)
    Base.metadata.create_all(bind=engine)

    while True:
        try:
            db = SessionLocal()
            service = ImmoService(db)
            all_users = db.query(Settings).all()

            tasks = []

            for user in all_users:
                # Собираем все активные ссылки пользователя
                # (Тут можно добавить проверку Premium, если нужно отключить лишние ссылки)

                if user.wg_url:
                    tasks.append(check_and_send(service, user.user_id, user.wg_url, "WG-Gesucht"))

                if user.immo_url:
                    tasks.append(check_and_send(service, user.user_id, user.immo_url, "ImmoScout24"))

                if user.immowelt_url:
                    tasks.append(check_and_send(service, user.user_id, user.immowelt_url, "Immowelt"))

                if user.kleinanzeigen_url:
                    tasks.append(check_and_send(service, user.user_id, user.kleinanzeigen_url, "Kleinanzeigen"))

            if tasks:
                logger.info(f"🚀 Starte {len(tasks)} Suchaufträge parallel...")
                # Запускаем все задачи одновременно (но с учетом лимита Semaphore)
                await asyncio.gather(*tasks)
            else:
                logger.info("💤 Keine aktiven Suchaufträge.")

            db.close()

        except Exception as e:
            logger.error(f"Global Loop Error: {e}")

        # Пауза между полными циклами проверки
        wait_time = 300  # 5 минут
        logger.info(f"💤 Schlafe für {wait_time} Sekunden...")
        await asyncio.sleep(wait_time)


async def on_startup():
    asyncio.create_task(scanner_loop())
    asyncio.create_task(subscription_loop(bot))
    logger.info("🤖 Bot gestartet (Async Mode + Subscription Check)!")

async def on_shutdown():
    logger.info("🛑 Остановка... Закрываю браузер.")
    await browser_manager.close()


async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    await dp.start_polling(bot)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot gestoppt.")