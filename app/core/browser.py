import asyncio
import logging
import time
import undetected_chromedriver as uc

logger = logging.getLogger(__name__)


class BrowserManager:
    def __init__(self):
        self.driver = None
        self.last_restart = 0
        self.restart_interval = 1800  # 30 минут
        self.lock = asyncio.Lock()

    def _start_driver(self):
        """Запускает новый экземпляр Chrome"""
        logger.info("🚀 Запуск браузера (Persistent Mode)...")
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--start-maximized")
        options.add_argument('--blink-settings=imagesEnabled=false')

        # [NEW] Стратегия EAGER: не ждать полной загрузки (картинок/стилей/рекламы)
        # Selenium вернет управление сразу, как только будет готов HTML.
        options.page_load_strategy = 'eager'

        self.driver = uc.Chrome(options=options, version_main=None)

        # Тайм-аут на загрузку страницы (если за 60 сек HTML не пришел - ошибка)
        self.driver.set_page_load_timeout(60)
        self.last_restart = time.time()

    async def get_driver(self):
        """Возвращает активный драйвер, перезапускает если нужно"""
        current_time = time.time()

        if self.driver is None or (current_time - self.last_restart > self.restart_interval):
            if self.driver:
                logger.info("⏰ Плановый перезапуск браузера (30 мин)...")
                try:
                    self.driver.quit()
                except:
                    pass

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._start_driver)

        return self.driver

    async def force_restart(self):
        """Экстренный сброс драйвера при ошибках"""
        logger.warning("🧨 Драйвер сломался! Сбрасываю состояние...")
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.driver = None

    async def close(self):
        """Закрывает браузер при выключении"""
        if self.driver:
            logger.info("🛑 Закрываю браузер...")
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None


browser_manager = BrowserManager()