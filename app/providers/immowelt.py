import asyncio
import logging
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from app.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class ImmoweltProvider(BaseProvider):
    async def fetch_listings(self, url: str, driver: Any = None) -> List[Dict]:
        if not driver:
            logger.error("❌ Immowelt требует драйвер!")
            return []

        logger.info(f"🤖 [Immowelt] Работаю в открытом окне...")
        listings = []

        try:
            loop = asyncio.get_event_loop()

            def interact():
                driver.get(url)
                return driver.page_source

            await loop.run_in_executor(None, interact)

            logger.info("⏳ Жду 5 сек...")
            await asyncio.sleep(5)

            driver.execute_script("window.scrollTo(0, 700);")
            await asyncio.sleep(1)

            html = driver.page_source
            soup = BeautifulSoup(html, 'lxml')

            cards = soup.find_all("div", attrs={"data-testid": "serp-core-classified-card-testid"})
            logger.info(f"🔎 Immowelt: Найдено {len(cards)} карточек")

            for i, card in enumerate(cards):
                try:
                    link_tag = card.find("a", attrs={"data-testid": "card-mfe-covering-link-testid"})
                    if not link_tag: continue
                    link = link_tag['href']

                    if "tausch" in card.text.lower() or "swap" in card.text.lower():
                        continue

                    title = link_tag.get("title", "Wohnung").replace("Wohnung zur Miete", "").strip() or "Wohnung"

                    price_div = card.find("div", attrs={"data-testid": "cardmfe-price-testid"})
                    price = "0"
                    if price_div:
                        cl_price = re.search(r'[\d\.]+', price_div.text)
                        if cl_price: price = cl_price.group(0).replace(".", "")

                    facts_div = card.find("div", attrs={"data-testid": "cardmfe-keyfacts-testid"})
                    area = "0"
                    if facts_div:
                        area_match = re.search(r'(\d+([.,]\d+)?)\s*m²', facts_div.text)
                        if area_match: area = area_match.group(1).replace(",", ".")

                    listings.append(
                        {'titel': title, 'preis': price, 'flaeche': area, 'link': link, 'quelle': 'Immowelt'})
                except:
                    continue

        except Exception as e:
            logger.error(f"❌ Immowelt Error: {e}")

        finally:
            # === ЧИСТКА СЛЕДОВ ===
            try:
                driver.delete_all_cookies()
                driver.execute_script("window.localStorage.clear();")
                logger.info("🧹 Куки Immowelt очищены.")
            except:
                pass

        return listings