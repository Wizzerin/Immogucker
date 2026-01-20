from sqlalchemy import Column, Integer, String, Boolean, BigInteger
from app.core.database import Base

class Settings(Base):
    __tablename__ = "settings"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, unique=True)  # Твой ID в телеграм
    search_url = Column(String)             # Ссылка, которую парсим
    is_active = Column(Boolean, default=True) # Можно поставить на паузу