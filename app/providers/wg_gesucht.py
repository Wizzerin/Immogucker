import asyncio
import logging
import time
import random
from typing import List, Dict
from bs4 import BeautifulSoup
import undetected_chromedriver as uc  # Используем хром!
from app.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class WGGesuchtProvider(BaseProvider):
    async def fetch_listings(self, url: str) -> List[Dict]:
        logger.info(f"🤖 [WG-Gesucht] Запуск браузера (Selenium)...")

        # Настройки такие же, как для ImmoScout
        options = uc.ChromeOptions()
        # options.add_argument("--headless=new") # Для тестов выключено
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")

        driver = None
        listings = []

        try:
            loop = asyncio.get_event_loop()

            def run_browser():
                d = uc.Chrome(options=options, version_main=None)
                d.get(url)
                return d

            driver = await loop.run_in_executor(None, run_browser)

            # Ждем загрузки (WG-Gesucht быстрый, но дадим 5 сек для верности)
            await asyncio.sleep(5)

            # Берем HTML
            html = driver.page_source
            soup = BeautifulSoup(html, 'lxml')

            # Парсим (код парсинга тот же, что и был)
            cards = soup.find_all("div", class_="wgg_card")
            logger.info(f"🔎 WG-Gesucht: Найдено {len(cards)} карточек")

            for card in cards:
                if "ad_listing" in card.get("class", []): continue
                try:
                    link_tag = card.find("a", class_="detailansicht")
                    if not link_tag: continue
                    full_link = "https://www.wg-gesucht.de" + link_tag['href']

                    title = card.find("h3", class_="truncate_title").text.strip()

                    # Цена и площадь
                    details = card.find_all("div", class_="col-xs-3")
                    price = details[0].text.strip().replace("€", "") if len(details) > 0 else "0"
                    area = details[1].text.strip().replace("m²", "") if len(details) > 1 else "0"

                    listings.append({
                        'titel': title, 'preis': price, 'flaeche': area,
                        'link': full_link, 'quelle': 'WG-Gesucht'
                    })
                except:
                    continue

        except Exception as e:
            logger.error(f"❌ Ошибка WG-Gesucht Browser: {e}")

        finally:
            if driver:
                driver.quit()  # Тут можно закрывать сразу

        return listings