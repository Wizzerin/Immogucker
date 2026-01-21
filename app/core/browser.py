import asyncio
import logging
import time
import undetected_chromedriver as uc

logger = logging.getLogger(__name__)


class BrowserManager:
    def __init__(self):
        self.driver = None
        self.last_restart = 0
        self.restart_interval = 1800  # 30 минут в секундах
        self.lock = asyncio.Lock()  # Глобальный замок

    def _start_driver(self):
        """Запускает новый экземпляр Chrome"""
        logger.info("🚀 Запуск браузера (Persistent Mode)...")
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--start-maximized")
        # Отключаем картинки для скорости
        options.add_argument('--blink-settings=imagesEnabled=false')

        self.driver = uc.Chrome(options=options, version_main=None)
        self.driver.set_page_load_timeout(60)
        self.last_restart = time.time()

    async def get_driver(self):
        """Возвращает активный драйвер, перезапускает если нужно"""
        current_time = time.time()

        # Если драйвера нет или прошло 30 минут -> перезапуск
        if self.driver is None or (current_time - self.last_restart > self.restart_interval):
            if self.driver:
                logger.info("⏰ Время жизни браузера истекло (30 мин). Перезапуск...")
                try:
                    self.driver.quit()
                except:
                    pass

            # Запускаем в отдельном потоке, чтобы не блокировать бота
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._start_driver)

        return self.driver

    async def close(self):
        """Закрывает браузер при выключении бота"""
        if self.driver:
            logger.info("🛑 Закрываю браузер...")
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None


# Создаем глобальный экземпляр
browser_manager = BrowserManager()