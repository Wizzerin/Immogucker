from sqlalchemy import text
from app.core.database import engine


def fix_sent_table():
    print("🚑 Лечим таблицу sent_listings...")

    with engine.connect() as conn:
        try:
            # 1. Принудительно меняем тип
            conn.execute(text("ALTER TABLE sent_listings ALTER COLUMN user_id TYPE BIGINT;"))
            conn.commit()  # <--- Важно! Фиксируем изменения
            print("✅ УСПЕШНО: sent_listings теперь принимает огромные ID.")
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
            print("Возможно, таблица уже исправлена или занята.")


if __name__ == "__main__":
    fix_sent_table()