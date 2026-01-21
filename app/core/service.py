import logging
import asyncio
from sqlalchemy.orm import Session
from app.models.immobilien import Immobilie
from app.models.sent import SentListing
from app.providers.wg_gesucht import WGGesuchtProvider
from app.providers.immoscout import ImmoscoutProvider
from app.providers.immowelt import ImmoweltProvider
from app.providers.kleinanzeigen import KleinanzeigenProvider  # <-- Импорт
from app.core.browser import browser_manager

logger = logging.getLogger(__name__)


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
        elif "kleinanzeigen.de" in url:  # <-- Проверка
            return KleinanzeigenProvider()
        else:
            return None

    async def process_user(self, user_id: int, search_url: str):
        provider = self._get_provider(search_url)
        if not provider: return []

        listings = []

        # Проверяем, нужен ли браузер (теперь это 3 провайдера)
        is_selenium = isinstance(provider, (ImmoscoutProvider, ImmoweltProvider, KleinanzeigenProvider))

        if is_selenium:
            async with browser_manager.lock:
                driver = await browser_manager.get_driver()
                listings = await provider.fetch_listings(url=search_url, driver=driver)
        else:
            listings = await provider.fetch_listings(url=search_url)

        if not listings: return []

        # ... (Код сохранения в БД - без изменений) ...
        new_for_user = []
        for item in listings:
            try:
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
                            flaeche=item['flaeche'],
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