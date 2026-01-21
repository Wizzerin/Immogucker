from sqlalchemy import Column, String, Boolean, BigInteger, Date
from app.core.database import Base


class Settings(Base):
    __tablename__ = "settings"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, unique=True)

    search_url = Column(String, nullable=True)

    wg_url = Column(String, nullable=True)
    immo_url = Column(String, nullable=True)
    immowelt_url = Column(String, nullable=True)
    kleinanzeigen_url = Column(String, nullable=True)  # <-- Новое поле

    is_active = Column(Boolean, default=True)


    is_premium = Column(Boolean, default=False)
    premium_until = Column(Date, nullable=True)