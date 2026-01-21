import asyncio
import logging
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from app.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class ImmoscoutProvider(BaseProvider):
    async def fetch_listings(self, url: str, driver: Any = None) -> List[Dict]:
        if not driver:
            logger.error("❌ ImmoScout требует драйвер!")
            return []

        logger.info(f"🤖 [ImmoScout] Работаю в открытом окне...")
        listings = []

        try:
            # Работаем с драйвером в executor'е, чтобы не блокировать бота
            loop = asyncio.get_event_loop()

            def interact():
                driver.get(url)
                return driver.page_source

            # Переход по ссылке
            html = await loop.run_in_executor(None, interact)

            logger.info("⏳ Жду 5 сек (рендеринг)...")
            await asyncio.sleep(5)

            # === ЗАКРЫТИЕ БАННЕРА ===
            try:
                driver.execute_script("""
                let host = document.querySelector('#usercentrics-root');
                if (host) {
                    let btn = host.shadowRoot.querySelector('button[data-testid="uc-accept-all-button"]');
                    if (btn) btn.click();
                }
                """)
            except:
                pass

            # Скролл
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            await asyncio.sleep(2)

            # Обновляем HTML после скриптов
            html = driver.page_source
            soup = BeautifulSoup(html, 'lxml')

            # --- Логика парсинга (БЕЗ ИЗМЕНЕНИЙ) ---
            # 1. Чистка мусора
            for noise in soup.find_all(attrs={"data-testid": "SurroundingSuburbs"}): noise.decompose()
            for noise in soup.find_all("section", class_="surrounding-suburbs"): noise.decompose()

            # 2. Поиск контейнера
            main_list = soup.find("div", id="result-list-content") or soup
            items = main_list.find_all("div", attrs={"data-obid": True})

            if not items:
                items = main_list.find_all("li", class_="result-list__listing")

            logger.info(f"🔎 ImmoScout: Найдено {len(items)} объектов")

            for item in items:
                try:
                    data_id = item.get("data-obid") or item.get("data-id")
                    if not data_id: continue
                    link = f"https://www.immoscout24.de/expose/{data_id}"

                    # Реклама
                    all_links = item.find_all("a", href=True)
                    is_external_ad = False
                    for a_tag in all_links:
                        href = a_tag['href']
                        if "immobilienscout24.de" not in href and not href.startswith("/"):
                            is_external_ad = True
                            break
                    if is_external_ad: continue

                    title_tag = item.find("h2", attrs={"data-testid": "headline"}) or item.find("h5")
                    title = title_tag.text.strip() if title_tag else "Wohnung"

                    price = "Anfrage"
                    area = "-"
                    dds = item.find_all("dd")
                    for dd in dds:
                        text = dd.text.strip()
                        if "€" in text:
                            price = text.replace("€", "").split(",")[0]
                        elif "m²" in text or "m2" in text:
                            area = text.replace("m²", "").split(",")[0]

                    listings.append(
                        {'titel': title, 'preis': price, 'flaeche': area, 'link': link, 'quelle': 'ImmoScout24'})
                except:
                    continue

        except Exception as e:
            logger.error(f"❌ ImmoScout Error: {e}")

        finally:
            # === ВАЖНО: ЧИСТИМ КУКИ ДЛЯ СЛЕДУЮЩЕГО ЗАПРОСА ===
            try:
                driver.delete_all_cookies()
                driver.execute_script("window.localStorage.clear();")
                driver.execute_script("window.sessionStorage.clear();")
                logger.info("🧹 Куки ImmoScout очищены.")
            except:
                pass

        return listings