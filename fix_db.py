from sqlalchemy import text
from app.core.database import engine


def fix_database():
    print("🚑 Начинаю принудительное лечение базы данных...")

    with engine.connect() as conn:
        # 1. Прямой SQL-запрос к базе данных, чтобы изменить тип колонки
        print("🛠 Исправляю таблицу settings...")
        try:
            conn.execute(text("ALTER TABLE settings ALTER COLUMN user_id TYPE BIGINT;"))
            print("✅ Успешно: settings.user_id теперь BIGINT.")
        except Exception as e:
            print(f"⚠️ Ошибка (возможно уже исправлено): {e}")

        # 2. То же самое для таблицы sent_listings
        print("🛠 Исправляю таблицу sent_listings...")
        try:
            conn.execute(text("ALTER TABLE sent_listings ALTER COLUMN user_id TYPE BIGINT;"))
            print("✅ Успешно: sent_listings.user_id теперь BIGINT.")
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")

        conn.commit()

    print("🎉 Лечение завершено. Теперь база принимает большие ID (8+ млрд).")


if __name__ == "__main__":
    fix_database()