# db_upgrade.py (создай в корне и запусти)
from app.core.database import engine, Base
from sqlalchemy import text
from app.models.voucher import Voucher  # Импорт нужен для create_all


def upgrade():
    with engine.connect() as conn:
        conn.commit()  # Сброс транзакции
        try:
            # Пытаемся добавить колонку
            conn.execute(text("ALTER TABLE user_settings ADD COLUMN premium_until TIMESTAMP"))
            print("✅ Колонка premium_until добавлена.")
            conn.commit()
        except Exception as e:
            print(f"ℹ️ Колонка, возможно, уже есть: {e}")

    # Создаем таблицу ваучеров
    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы обновлены.")


if __name__ == "__main__":
    upgrade()