from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Используем localhost, так как Python запущен на компе, а БД в Докере проброшена на порт 5432
# Формат: postgresql://user:password@localhost:5432/dbname
DATABASE_URL = "postgresql://user:password@localhost:5432/immogucker"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Функция для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()