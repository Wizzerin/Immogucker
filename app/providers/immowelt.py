import asyncio
import logging
import os
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from app.providers.base import BaseProvider
from app.core.browser import browser_manager

logger = logging.getLogger(__name__)


class ImmoweltProvider(BaseProvider):
    async def fetch_listings(self, url: str, driver: Any = None) -> List[Dict]:
        if not driver:
            return []

        logger.info(f"🤖 [Immowelt] Работаю в открытом окне...")
        listings = []

        try:
            loop = asyncio.get_event_loop()

            def interact():
                driver.get(url)
                return driver.page_source

            await loop.run_in_executor(None, interact)

            # Ждем чуть дольше, чтобы React успел отрисовать карточки
            logger.info("⏳ Жду 6 сек (рендеринг)...")
            await asyncio.sleep(6)

            # === АГРЕССИВНОЕ ЗАКРЫТИЕ КУКИ ===
            try:
                driver.execute_script("""
                try {
                    let host = document.querySelector('#usercentrics-root');
                    if (host && host.shadowRoot) {
                        let btn = host.shadowRoot.querySelector('button[data-testid="uc-accept-all-button"]');
                        if (btn) btn.click();
                    }
                } catch(e) {}

                // Разблокировка прокрутки
                document.body.style.overflow = 'auto';
                document.documentElement.style.overflow = 'auto';
                """)
            except:
                pass

            # === СКРОЛЛ (Обязательно для подгрузки картинок и цен) ===
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 3);")
            await asyncio.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 1.5);")
            await asyncio.sleep(1)
            driver.execute_script("window.scrollTo(0, 0);")  # Вернуться наверх (иногда помогает)
            await asyncio.sleep(1)

            html = driver.page_source
            soup = BeautifulSoup(html, 'lxml')

            # === [NEW] НОВЫЕ СЕЛЕКТОРЫ (из твоего snapshot.html) ===

            # Ищем контейнеры по новому data-testid
            items = soup.find_all("div", attrs={"data-testid": "serp-core-classified-card-testid"})

            # Если вдруг не нашло, пробуем запасной вариант (по ID)
            if not items:
                items = soup.find_all("div", id=lambda x: x and x.startswith("classified-card-"))

            logger.info(f"🔎 Immowelt: Найдено {len(items)} карточек")

            # Если снова 0 - сохраняем дебаг, чтобы проверить, не забанили ли нас
            if len(items) == 0:
                with open("immowelt_debug_v2.html", "w", encoding="utf-8") as f:
                    f.write(html)

            for item in items:
                try:
                    # 1. Ссылка и заголовок теперь в одном <a>
                    link_tag = item.find("a", attrs={"data-testid": "card-mfe-covering-link-testid"})
                    if not link_tag:
                        # Fallback: ищем любую ссылку внутри
                        link_tag = item.find("a", href=True)

                    if not link_tag: continue

                    href = link_tag.get('href')
                    if not href.startswith("http"):
                        link = f"https://www.immowelt.de{href}"
                    else:
                        link = href

                    # Заголовок часто в атрибуте title самой ссылки или внутри h2
                    title = link_tag.get("title")
                    if not title:
                        h2 = item.find("h2")
                        title = h2.text.strip() if h2 else "Wohnung"

                    # 2. Цена
                    price = "Anfrage"
                    price_div = item.find("div", attrs={"data-testid": "cardmfe-price-testid"})
                    if price_div:
                        # Там обычно вложенный div с ценой
                        price_text = price_div.get_text(strip=True)
                        # Чистим цену (1.100 € -> 1100)
                        price = price_text.replace("€", "").replace("Kaltmiete", "").strip()

                    # 3. Площадь (ищем внутри Keyfacts)
                    area = "0"
                    facts_div = item.find("div", attrs={"data-testid": "cardmfe-keyfacts-testid"})
                    if facts_div:
                        # Текст внутри: "2 Zimmer · 55 m² · 2. Geschoss"
                        facts_text = facts_div.get_text(" ", strip=True)
                        parts = facts_text.split("·")
                        for part in parts:
                            if "m²" in part or "m2" in part:
                                area = part.replace("m²", "").replace("m2", "").strip()
                                break

                    listings.append({
                        'titel': title,
                        'preis': price,
                        'flaeche': area,
                        'link': link,
                        'quelle': 'Immowelt'
                    })

                except Exception as e:
                    # logger.error(f"Ошибка парсинга отдельной карточки: {e}")
                    continue

        except Exception as e:
            logger.error(f"❌ Immowelt Global Error: {e}")
            await browser_manager.force_restart()

        finally:
            # Чистим куки, чтобы следующий заход был "как новый"
            try:
                driver.delete_all_cookies()
                driver.execute_script("window.localStorage.clear();")
            except:
                pass

        return listings