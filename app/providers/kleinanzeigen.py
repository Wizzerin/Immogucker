import asyncio
import logging
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from app.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class KleinanzeigenProvider(BaseProvider):
    async def fetch_listings(self, url: str, driver: Any = None) -> List[Dict]:
        if not driver:
            logger.error("❌ Kleinanzeigen требует драйвер!")
            return []

        logger.info(f"🤖 [Kleinanzeigen] Работаю в открытом окне...")
        listings = []

        try:
            loop = asyncio.get_event_loop()

            def interact():
                driver.get(url)
                return driver.page_source

            await loop.run_in_executor(None, interact)

            logger.info("⏳ Жду 5 сек...")
            await asyncio.sleep(5)

            # Попытка закрыть баннер (GDPR)
            try:
                driver.execute_script("""
                    let btn = document.querySelector('#gdpr-banner-accept');
                    if (btn) btn.click();
                """)
            except:
                pass

            # Скролл для подгрузки (хотя там пагинация, но на всякий случай)
            driver.execute_script("window.scrollTo(0, 700);")
            await asyncio.sleep(1)

            html = driver.page_source
            soup = BeautifulSoup(html, 'lxml')

            # Ищем список объявлений
            ad_list = soup.find("ul", id="srchrslt-adtable")
            if not ad_list:
                logger.warning("⚠️ Не нашел таблицу объявлений (#srchrslt-adtable). Возможно, бан или пусто.")
                return []

            items = ad_list.find_all("li", class_="ad-listitem")
            logger.info(f"🔎 Kleinanzeigen: Найдено {len(items)} блоков")

            for i, item in enumerate(items):
                try:
                    article = item.find("article", class_="aditem")
                    if not article: continue  # Пропускаем баннеры/пустые блоки

                    # 1. Ссылка и ID
                    # data-href="/s-anzeige/..."
                    rel_link = article.get("data-href")
                    if not rel_link:
                        # Запасной вариант через заголовок
                        link_tag = article.find("a", class_="ellipsis")
                        if link_tag: rel_link = link_tag['href']

                    if not rel_link: continue

                    full_link = f"https://www.kleinanzeigen.de{rel_link}"

                    # 2. Заголовок
                    title_tag = article.find("a", class_="ellipsis")
                    title = title_tag.text.strip() if title_tag else "Wohnung"

                    # 3. Фильтр Tausch (Обмен)
                    full_text = article.text.lower()
                    if "tausch" in full_text or "swap" in full_text or "suche" in title.lower():
                        logger.info(f"  [{i}] Пропуск: ♻️ Tausch/Suche")
                        continue

                        # 4. Цена
                    price_p = article.find("p", class_="aditem-main--middle--price-shipping--price")
                    price = "0"
                    if price_p:
                        # "600 €" -> "600"
                        raw_price = price_p.text.strip()
                        clean_match = re.search(r'[\d\.]+', raw_price)
                        if clean_match:
                            price = clean_match.group(0).replace(".", "")

                    # 5. Площадь и Комнаты (они в тегах)
                    # Пример: "64 m² \n · \n 2 Zi."
                    tags_p = article.find("p", class_="aditem-main--middle--tags")
                    area = "0"
                    if tags_p:
                        tags_text = tags_p.text
                        # Ищем площадь
                        area_match = re.search(r'(\d+([.,]\d+)?)\s*m²', tags_text)
                        if area_match:
                            area = area_match.group(1).replace(",", ".")

                    logger.info(f"  [{i}] ✅ KA: {title[:30]}... | {price}€")

                    listings.append({
                        'titel': title,
                        'preis': price,
                        'flaeche': area,
                        'link': full_link,
                        'quelle': 'Kleinanzeigen'
                    })
                except Exception as e:
                    logger.warning(f"  [{i}] Ошибка KA: {e}")
                    continue

        except Exception as e:
            logger.error(f"❌ Kleinanzeigen Error: {e}")

        finally:
            # Чистка
            try:
                driver.delete_all_cookies()
                driver.execute_script("window.localStorage.clear();")
            except:
                pass

        return listings