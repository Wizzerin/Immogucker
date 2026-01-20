from sqlalchemy import Column, Integer, String, BigInteger
from app.core.database import Base

class SentListing(Base):
    __tablename__ = "sent_listings"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger) # Кому отправили
    link = Column(String) # Какую ссылку отправили