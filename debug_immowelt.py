import time
import undetected_chromedriver as uc


def save_immowelt_html():
    print("🚀 Запускаю Chrome для Immowelt...")

    options = uc.ChromeOptions()
    # Важно: не используем headless режим, чтобы ты видел браузер и мог решить капчу руками, если она вылезет
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")

    driver = uc.Chrome(options=options)

    try:
        # Ссылка на поиск квартир в Кельне (можно заменить на любую другую)
        url = "https://www.immowelt.de/liste/koeln/wohnungen/mieten?d=true&sd=DESC&sf=RELEVANCE&sp=1"

        print(f"🔗 Перехожу на: {url}")
        driver.get(url)

        print("⏳ Жду 30 секунд...")
        print("❗ В это время САМ закрой баннер с куки или реши капчу, если она появится!")
        time.sleep(30)

        # Сохраняем HTML
        filename = "immowelt_snapshot.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(driver.page_source)

        print(f"✅ Готово! HTML сохранен в файл: {filename}")
        print("📂 Теперь отправь этот файл мне в чат.")

    except Exception as e:
        print(f"❌ Ошибка: {e}")

    finally:
        driver.quit()


if __name__ == "__main__":
    save_immowelt_html()