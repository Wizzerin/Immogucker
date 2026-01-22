import logging
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.immobilien import Immobilie
from app.models.sent import SentListing
from app.providers.wg_gesucht import WGGesuchtProvider
from app.providers.immoscout import ImmoscoutProvider
from app.providers.immowelt import ImmoweltProvider
from app.providers.kleinanzeigen import KleinanzeigenProvider
from app.core.browser import browser_manager

logger = logging.getLogger(__name__)

# [NEW] Глобальное хранилище статусов
health_status = {}


class ImmoService:
    def __init__(self, db: Session):
        self.db = db

    def _get_provider(self, url: str):
        if "wg-gesucht.de" in url:
            return WGGesuchtProvider()
        elif "scout24" in url:
            return ImmoscoutProvider()
        elif "immowelt.de" in url:
            return ImmoweltProvider()
        elif "kleinanzeigen.de" in url:
            return KleinanzeigenProvider()
        else:
            return None

    def _clean_number(self, value):
        if not value: return 0.0
        s = str(value).lower().strip()
        if s in ["-", "k.a.", ""]: return 0.0
        s = s.replace("m²", "").replace("m2", "").replace(" ", "")
        s = s.replace(".", "").replace(",", ".")
        try:
            return float(s)
        except:
            return 0.0

    async def process_user(self, user_id: int, search_url: str):
        provider = self._get_provider(search_url)
        if not provider: return []

        # Получаем красивое имя провайдера (WGGesucht, Immoscout...)
        provider_name = provider.__class__.__name__.replace("Provider", "")
        listings = []

        is_selenium = isinstance(provider, (ImmoscoutProvider, ImmoweltProvider, KleinanzeigenProvider))

        # [NEW] Блок попытки скачивания с записью в Health
        try:
            if is_selenium:
                async with browser_manager.lock:
                    driver = await browser_manager.get_driver()
                    listings = await provider.fetch_listings(url=search_url, driver=driver)
            else:
                listings = await provider.fetch_listings(url=search_url)

            # Если всё прошло успешно (даже если 0 квартир)
            count = len(listings) if listings else 0
            health_status[provider_name] = {
                "status": "✅ OK" if count > 0 else "⚠️ Leer",
                "time": datetime.now().strftime("%H:%M:%S"),
                "msg": f"Gefunden: {count}"
            }

        except Exception as e:
            # Если упало с ошибкой
            logger.error(f"Error fetching {provider_name}: {e}")
            health_status[provider_name] = {
                "status": "❌ ERROR",
                "time": datetime.now().strftime("%H:%M:%S"),
                "msg": str(e)[:20] + "..."  # Обрезаем длинные ошибки
            }
            return []

        if not listings: return []

        new_for_user = []

        exclude_keywords = [
            "tausch", "swap", "exchange", "wohnungstausch",
            "tausche", "swapping", "only swap", "nur tausch"
        ]

        for item in listings:
            try:
                # Фильтр Tausch
                text_to_check = (str(item.get('titel', '')) + " " + str(item.get('link', ''))).lower()
                is_swap = False
                for keyword in exclude_keywords:
                    if keyword in text_to_check:
                        is_swap = True
                        break

                if is_swap: continue

                clean_area = self._clean_number(item.get('flaeche'))

                already_sent = self.db.query(SentListing).filter(
                    SentListing.user_id == user_id,
                    SentListing.link == item['link']
                ).first()

                if not already_sent:
                    flat_in_db = self.db.query(Immobilie).filter(Immobilie.link == item['link']).first()

                    if not flat_in_db:
                        flat_in_db = Immobilie(
                            titel=item['titel'],
                            kaltmiete=item['preis'],
                            flaeche=clean_area,
                            link=item['link'],
                            anbieter=item['quelle']
                        )
                        self.db.add(flat_in_db)
                        self.db.commit()
                        self.db.refresh(flat_in_db)

                    item['db_id'] = flat_in_db.id
                    sent_record = SentListing(user_id=user_id, link=item['link'])
                    self.db.add(sent_record)
                    self.db.commit()
                    new_for_user.append(item)

            except Exception as e:
                logger.error(f"Save error: {e}")
                self.db.rollback()
                continue

        return new_for_user