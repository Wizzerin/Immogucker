from sqlalchemy import Column, Integer, String, Float, DateTime
from app.core.database import Base

class Immobilie(Base):
    __tablename__ = "immobilien"

    id = Column(Integer, primary_key=True)
    titel = Column(String)
    stadtteil = Column(String)
    kaltmiete = Column(String)
    warmmiete =Column(String)
    zimmer_anzahl = Column(Float)
    flaeche = Column(Float) # Площадь (m²)
    link = Column(String, unique=True)
    anbieter = Column(String) # Кто выставил (сайт-провайдер)