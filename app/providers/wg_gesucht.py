import asyncio
import logging
import random
import re
import requests
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from app.providers.base import BaseProvider

logger = logging.getLogger(__name__)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
]


class WGGesuchtProvider(BaseProvider):
    def _clean_number(self, text: str) -> str:
        """Ищет первое число в строке"""
        if not text: return "0"
        # Ищем цифры, игнорируя точки (тысячи)
        match = re.search(r'\d+', text.replace('.', ''))
        return match.group(0) if match else "0"

    async def fetch_listings(self, url: str, driver: Any = None) -> List[Dict]:
        logger.info(f"🤖 [WG-Gesucht] Запрос...")
        listings = []

        current_ua = random.choice(USER_AGENTS)
        headers = {'User-Agent': current_ua,
                   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}

        try:
            loop = asyncio.get_event_loop()

            def make_req():
                session = requests.Session()
                return session.get(url, headers=headers, timeout=30)

            response = await loop.run_in_executor(None, make_req)

            if response.status_code != 200:
                logger.error(f"❌ WG-Gesucht статус: {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, 'lxml')
            cards = soup.find_all("div", class_="wgg_card")

            # Если 0 карточек, возможно бан или капча
            if not cards and "captcha" in response.text.lower():
                logger.warning("⚠️ WG-Gesucht CAPTCHA!")
                return []

            logger.info(f"🔎 WG-Gesucht: Найдено {len(cards)} карточек")

            for card in cards:
                if "ad_listing" in card.get("class", []): continue

                try:
                    # 1. ССЫЛКА
                    link_tag = card.find("a", class_="detailansicht")
                    if not link_tag: continue

                    href = link_tag['href']
                    if not href.startswith("/") and "wg-gesucht.de" not in href: continue  # Реклама

                    full_link = "https://www.wg-gesucht.de" + href if not href.startswith("http") else href

                    # 2. ЗАГОЛОВОК (Безопасный поиск)
                    title_tag = card.find("h3", class_="truncate_title")
                    if title_tag:
                        title = title_tag.text.strip()
                    else:
                        # Запасной вариант: ищем любой заголовок внутри ссылки
                        title = link_tag.text.strip() or "Wohnung"

                    # 3. ДЕТАЛИ (Цена и Площадь)
                    price = "0"
                    area = "0"

                    # Попытка 1: По колонкам (стандартная верстка)
                    details = card.find_all("div", class_="col-xs-3")
                    if len(details) >= 2:
                        price = self._clean_number(details[0].text.strip())
                        area = self._clean_number(details[1].text.strip())
                    else:
                        # Попытка 2: Ищем по тексту (если верстка поехала)
                        card_text = card.text

                        # Ищем цену (число перед евро)
                        price_match = re.search(r'(\d+)\s*€', card_text)
                        if price_match: price = price_match.group(1)

                        # Ищем площадь (число перед м2)
                        area_match = re.search(r'(\d+)\s*m²', card_text)
                        if area_match: area = area_match.group(1)

                    listings.append({
                        'titel': title, 'preis': price, 'flaeche': area,
                        'link': full_link, 'quelle': 'WG-Gesucht'
                    })
                except Exception as e:
                    logger.warning(f"⚠️ Пропуск карточки: {e}")
                    continue

        except Exception as e:
            logger.error(f"❌ WG-Gesucht Global Error: {e}")

        logger.info(f"✅ WG-Gesucht: Обработано {len(listings)} объявлений")
        return listings