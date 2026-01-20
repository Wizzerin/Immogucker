from sqlalchemy.orm import Session
from app.models.immobilien import Immobilie
from app.models.sent import SentListing
from app.models.settings import Settings
from app.providers.wg_gesucht import WGGesuchtProvider
from app.providers.immoscout import ImmoscoutProvider

class ImmoService:
    def __init__(self, db: Session):
        self.db = db
        self.provider = WGGesuchtProvider()

    def _get_provider(self, url: str):
        """Фабрика: выбирает парсер по ссылке"""
        if "wg-gesucht.de" in url:
            return WGGesuchtProvider()
        elif "scout24" in url:
            return ImmoscoutProvider()
        else:
            return None

    async def process_user(self, user_id: int, search_url: str):
        """Обрабатывает поиск для ОДНОГО конкретного пользователя"""
        # Выбираем правильного провайдера
        provider = self._get_provider(search_url)

        if not provider:
            print(f"❌ Неизвестный сайт: {search_url}")
            return []
        # 1. Скачиваем свежие данные по ссылке юзера
        # (Провайдер сам применит фильтры цены/площади из URL)
        listings = await self.provider.fetch_listings(url=search_url)

        new_for_user = []

        for item in listings:
            # 1. Проверяем, отправляли ли мы это уже
            already_sent = self.db.query(SentListing).filter(
                SentListing.user_id == user_id,
                SentListing.link == item['link']
            ).first()

            if not already_sent:
                # 2. ГАРАНТИРУЕМ, что квартира есть в базе (чтобы получить ID)
                # Ищем квартиру в общей базе
                flat_in_db = self.db.query(Immobilie).filter(Immobilie.link == item['link']).first()

                if not flat_in_db:
                    # Если нет - создаем
                    flat_in_db = Immobilie(
                        titel=item['titel'],
                        kaltmiete=item['preis'],
                        flaeche=item['flaeche'],
                        link=item['link'],
                        anbieter=item['quelle']
                    )
                    self.db.add(flat_in_db)
                    self.db.commit()  # Сохраняем, чтобы получить ID
                    self.db.refresh(flat_in_db)  # Получаем ID обратно в объект

                # 3. Добавляем ID квартиры в объект item, чтобы использовать в кнопке
                item['db_id'] = flat_in_db.id

                # 4. Записываем в отправленные
                record = SentListing(user_id=user_id, link=item['link'])
                self.db.add(record)
                new_for_user.append(item)

        # Сохраняем факт отправки в БД
        if new_for_user:
            self.db.commit()

        return new_for_user