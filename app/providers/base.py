from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseProvider(ABC):
    @abstractmethod
    async def fetch_listings(self, url: str, driver: Any = None) -> List[Dict]:
        """
        driver: Экземпляр Selenium драйвера (если нужен)
        """
        pass