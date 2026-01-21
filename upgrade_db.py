from sqlalchemy import text
from app.core.database import engine


def upgrade_database():
    print("🛠 Обновляю базу данных (PostgreSQL fix)...")

    # 1. Добавляем is_premium
    with engine.connect() as conn:
        try:
            # Используем FALSE вместо 0
            conn.execute(text("ALTER TABLE settings ADD COLUMN is_premium BOOLEAN DEFAULT FALSE;"))
            conn.commit()
            print("✅ Колонка is_premium добавлена.")
        except Exception as e:
            conn.rollback()  # Сбрасываем ошибку, чтобы продолжить
            # Проверяем, действительно ли колонка уже есть, или это другая ошибка
            if "already exists" in str(e):
                print("ℹ️ Колонка is_premium уже существует.")
            else:
                print(f"⚠️ Ошибка с is_premium (возможно, уже есть): {e}")

    # 2. Добавляем premium_until
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE settings ADD COLUMN premium_until DATE;"))
            conn.commit()
            print("✅ Колонка premium_until добавлена.")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e):
                print("ℹ️ Колонка premium_until уже существует.")
            else:
                print(f"⚠️ Ошибка с premium_until (возможно, уже есть): {e}")

    print("🎉 База данных готова!")


if __name__ == "__main__":
    upgrade_database()