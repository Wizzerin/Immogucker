import asyncio
import logging
from typing import List, Dict
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from app.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class ImmoscoutProvider(BaseProvider):
    async def fetch_listings(self, url: str) -> List[Dict]:
        logger.info(f"🤖 [ImmoScout] Запуск браузера...")

        options = uc.ChromeOptions()
        # options.add_argument("--headless=new")  # Пока выключено для тестов

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--start-maximized")
        # Включаем картинки, чтобы сайт грузился естественнее
        # options.add_argument("--blink-settings=imagesEnabled=false")

        driver = None
        listings = []

        try:
            loop = asyncio.get_event_loop()

            def run_browser():
                d = uc.Chrome(options=options, version_main=None)
                d.set_page_load_timeout(45)
                d.get(url)
                return d

            driver = await loop.run_in_executor(None, run_browser)

            # === ЦИКЛ ОЖИДАНИЯ БАННЕРА (Smart Wait) ===
            logger.info("🍪 Начинаю охоту на баннер (макс 20 сек)...")

            cookie_clicked = False

            # Пытаемся 20 раз с паузой 1 сек (итого 20 сек ожидания)
            for attempt in range(20):
                try:
                    # Скрипт ищет кнопку и кликает
                    cookie_script = """
                    try {
                        let root = document.querySelector('#usercentrics-root');
                        if (!root) return "NO_ROOT";
                        let shadow = root.shadowRoot;
                        if (!shadow) return "NO_SHADOW";

                        let buttons = shadow.querySelectorAll('button');
                        for (let btn of buttons) {
                            let txt = btn.innerText.toLowerCase();
                            // Ищем любые вариации "Принять"
                            if (txt.includes('alles') || txt.includes('alle') || txt.includes('accept') || txt.includes('zustimmen')) {
                                btn.click();
                                return "CLICKED: " + txt;
                            }
                        }
                        return "WAITING";
                    } catch (e) { return "ERR"; }
                    """
                    result = driver.execute_script(cookie_script)

                    if "CLICKED" in result:
                        logger.info(f"✅ Куки приняты: {result}")
                        cookie_clicked = True
                        await asyncio.sleep(2)  # Пауза на исчезновение анимации
                        break

                    # Если не нашли - ждем секунду и пробуем снова
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.warning(f"⚠️ Ошибка в цикле куки: {e}")
                    await asyncio.sleep(1)

            if not cookie_clicked:
                logger.warning("⚠️ Баннер так и не появился или мы его не нашли. Пробуем парсить так.")

            # === СКРОЛЛИНГ ===
            # Медленный скролл для имитации чтения (подгружает ленивый контент)
            logger.info("📜 Скроллю страницу...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.3);")
            await asyncio.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.6);")
            await asyncio.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            await asyncio.sleep(1)

            # === ПАРСИНГ ===
            html = driver.page_source
            soup = BeautifulSoup(html, 'lxml')

            # Поиск объявлений
            items = soup.find_all("li", class_="result-list__listing")
            if not items:
                items = soup.find_all("article", attrs={"data-item": "result"})

            logger.info(f"🔎 Найдено {len(items)} элементов")

            for item in items:
                try:
                    data_id = item.get("data-id")
                    if not data_id: continue

                    clean_link = f"https://www.immoscout24.de/expose/{data_id}"
                    price = "Anfrage"
                    area = "-"
                    title = "Wohnung"

                    # Парсинг (пробуем разные варианты верстки)
                    dl = item.find("dl", class_="grid-item")
                    criteria = dl.find_all("dd") if dl else item.find_all("dd")

                    if len(criteria) >= 1: price = criteria[0].text.strip().replace("€", "")
                    if len(criteria) >= 2: area = criteria[1].text.strip().replace("m²", "")

                    t_tag = item.find("h5")
                    if t_tag: title = t_tag.text.strip()

                    listings.append({
                        'titel': title, 'preis': price, 'flaeche': area,
                        'link': clean_link, 'quelle': 'ImmoScout24'
                    })
                except:
                    continue

        except Exception as e:
            logger.error(f"❌ ImmoScout Error: {e}")

        finally:
            if driver:
                # driver.quit() # Раскомментируй для продакшена
                logger.info("🚪 Браузер ждет закрытия (debug).")

        return listings