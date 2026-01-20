from abc import ABC, abstractmethod
from typing import List, Dict


class BaseProvider(ABC):
    # Мы убрали __init__ и parse_listing.
    # Теперь родитель требует только одного: уметь скачивать список (fetch_listings).

    @abstractmethod
    async def fetch_listings(self, url: str) -> List[Dict]:
        """
        Главная функция: Загружает страницу и возвращает список квартир.
        Все провайдеры (WGGesucht, ImmoScout) обязаны иметь этот метод.
        """
        pass