import asyncio
import logging
import time
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from app.providers.base import BaseProvider
from app.core.browser import browser_manager

logger = logging.getLogger(__name__)


class KleinanzeigenProvider(BaseProvider):
    async def fetch_listings(self, url: str, driver: Any = None) -> List[Dict]:
        if not driver:
            return []

        logger.info(f"🤖 [Kleinanzeigen] Работаю в открытом окне...")
        listings = []

        try:
            loop = asyncio.get_event_loop()

            def interact():
                try:
                    # [FIX] СБРОС СОСТОЯНИЯ БРАУЗЕРА
                    # Переход на пустую страницу убивает скрипты Immowelt, которые вешают браузер
                    driver.get("about:blank")
                    time.sleep(1)

                    # Теперь переходим на Kleinanzeigen с чистой совестью
                    driver.set_page_load_timeout(25)
                    driver.get(url)

                except TimeoutException:
                    logger.warning("⚠️ Kleinanzeigen: Timeout загрузки. Останавливаю и паршу что есть.")
                    try:
                        driver.execute_script("window.stop();")
                    except:
                        pass
                except Exception as e:
                    raise e

                # Закрытие куки
                try:
                    driver.execute_script("document.getElementById('gdpr-banner-accept').click();")
                except:
                    pass

                return driver.page_source

            html = await loop.run_in_executor(None, interact)

            try:
                driver.execute_script("window.scrollTo(0, 300);")
                await asyncio.sleep(1)
            except:
                pass

            soup = BeautifulSoup(html, 'lxml')

            # --- ПАРСИНГ ---
            items = []
            main_list = soup.find("ul", id="srchrslt-adtable")

            if main_list:
                items = main_list.find_all("li", class_="ad-listitem")

            if not items:
                items = soup.find_all("article", class_="aditem")

            logger.info(f"🔎 Kleinanzeigen: Найдено {len(items)} блоков")

            if len(items) == 0:
                # Если снова 0 — можно раскомментировать для проверки, что видит бот
                # with open("kleinanzeigen_fail_debug.html", "w", encoding="utf-8") as f: f.write(html)
                pass

            for i, item in enumerate(items):
                try:
                    if item.name == 'li':
                        article = item.find("article")
                    else:
                        article = item

                    if not article: continue

                    # Заголовок (ищем в h2, чтобы не брать цифры с картинок)
                    h2 = article.find("h2")
                    if not h2: continue
                    link_tag = h2.find("a", href=True)
                    if not link_tag: continue

                    title = link_tag.text.strip()

                    # Ссылка
                    partial_link = link_tag['href']
                    if "kleinanzeigen.de" not in partial_link:
                        link = f"https://www.kleinanzeigen.de{partial_link}"
                    else:
                        link = partial_link

                    # Цена (с очисткой от значка евро, чтобы не двоилось)
                    price = "VB"
                    price_tag = article.find("p", class_=lambda x: x and "price" in x)
                    if price_tag:
                        raw_price = price_tag.text.strip()
                        clean_price = raw_price.replace("€", "").replace("VB", "").strip()
                        if clean_price:
                            price = clean_price
                        else:
                            price = raw_price

                    # Площадь
                    area = "-"
                    details_div = article.find("div", class_=lambda x: x and "simple-attribute" in x)
                    raw_text = article.get_text(" ", strip=True)

                    if "m²" in raw_text:
                        words = raw_text.split()
                        for idx, w in enumerate(words):
                            if "m²" in w or "m2" in w:
                                if idx > 0:
                                    prev_word = words[idx - 1].replace(",", ".")
                                    if prev_word.replace(".", "").isdigit():
                                        area = prev_word
                                break

                    listings.append({
                        'titel': title,
                        'preis': price,
                        'flaeche': area,
                        'link': link,
                        'quelle': 'Kleinanzeigen'
                    })

                except Exception as e:
                    continue

        except Exception as e:
            logger.error(f"❌ Kleinanzeigen Error: {e}")
            await browser_manager.force_restart()

        return listings