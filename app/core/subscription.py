import asyncio
import logging
from datetime import datetime, timedelta, date  # <--- Добавлен импорт date
from aiogram import Bot
from app.models.settings import Settings
from sqlalchemy.orm import sessionmaker
from app.core.database import engine

logger = logging.getLogger(__name__)
SessionLocal = sessionmaker(bind=engine)


async def check_subscriptions(bot: Bot):
    """
    Проверяет подписки пользователей.
    1. Если срок вышел -> снимает Premium и уведомляет.
    2. Если осталось 3 дня -> предупреждает.
    """
    logger.info("⏳ Prüfe Abonnements...")
    db = SessionLocal()

    try:
        # Берем только премиум пользователей с установленной датой
        premium_users = db.query(Settings).filter(
            Settings.is_premium == True,
            Settings.premium_until != None
        ).all()

        now = datetime.now()

        for user in premium_users:
            expiry = user.premium_until

            # === [FIX] ИСПРАВЛЕНИЕ ТИПА ДАННЫХ ===
            # Если база вернула просто дату (date), превращаем её в datetime (на начало дня)
            if type(expiry) == date:
                expiry = datetime.combine(expiry, datetime.min.time())

            time_left = expiry - now
            days_left = time_left.days
            seconds_left = time_left.total_seconds()

            # 1. ПОДПИСКА ИСТЕКЛА
            if seconds_left <= 0:
                user.is_premium = False

                try:
                    await bot.send_message(
                        user.user_id,
                        "🚫 <b>Premium abgelaufen!</b>\n\n"
                        "Dein Premium-Zugang ist soeben abgelaufen.\n"
                        "Du wurdest auf den <b>Free-Plan</b> zurückgestuft (max. 1 Suche).\n\n"
                        "<i>Verlängern? Nutze /redeem [CODE]</i>",
                        parse_mode="HTML"
                    )
                    logger.info(f"🚫 Abo abgelaufen für User {user.user_id}")
                except Exception as e:
                    logger.warning(f"Konnte User {user.user_id} nicht benachrichtigen: {e}")

            # 2. ПРЕДУПРЕЖДЕНИЕ (3 дня)
            # Проверяем, находится ли время в интервале [72ч ... 73ч]
            elif 72 * 3600 < seconds_left < 73 * 3600:
                try:
                    expiry_date = expiry.strftime("%d.%m.%Y")
                    await bot.send_message(
                        user.user_id,
                        f"⚠️ <b>Abo läuft bald ab!</b>\n\n"
                        f"Dein Premium endet in <b>3 Tagen</b> (am {expiry_date}).\n"
                        "Besorge dir rechtzeitig einen neuen Code!",
                        parse_mode="HTML"
                    )
                    logger.info(f"⚠️ Warnung gesendet an User {user.user_id}")
                except Exception as e:
                    logger.warning(f"Konnte User {user.user_id} nicht warnen: {e}")

        db.commit()

    except Exception as e:
        logger.error(f"Fehler im Subscription-Loop: {e}")
    finally:
        db.close()


async def subscription_loop(bot: Bot):
    """Фоновый цикл, запускается раз в час"""
    # Ждем 10 секунд перед первым запуском, чтобы основной бот успел прогрузиться
    await asyncio.sleep(10)

    while True:
        await check_subscriptions(bot)
        # Ждем 1 час (3600 секунд)
        await asyncio.sleep(3600)