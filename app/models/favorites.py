from sqlalchemy import Column, Integer, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from app.core.database import Base


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)  # ID пользователя (BigInt!)
    immobilie_id = Column(Integer, ForeignKey("immobilien.id"))  # Ссылка на квартиру

    # Связь, чтобы удобно получать данные квартиры
    immobilie = relationship("Immobilie")