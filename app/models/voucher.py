from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.core.database import Base

class Voucher(Base):
    __tablename__ = "vouchers"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)  # Сам код (например "X8K2-9LPA")
    days = Column(Integer)  # На сколько дней дает доступ
    is_used = Column(Boolean, default=False)  # Использован или нет
    created_at = Column(DateTime, server_default=func.now())