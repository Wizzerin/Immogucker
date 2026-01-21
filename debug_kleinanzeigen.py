import time
import undetected_chromedriver as uc


def save_kleinanzeigen_html():
    print("🚀 Запускаю Chrome для Kleinanzeigen...")

    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")

    driver = uc.Chrome(options=options)

    try:
        # Ссылка на поиск квартир в Кельне (для примера)
        url = "https://www.kleinanzeigen.de/s-wohnung-mieten/koeln/c203l375"

        print(f"🔗 Перехожу на: {url}")
        driver.get(url)

        print("⏳ Жду 30 секунд...")
        print("❗ Если вылезет окно с куки — нажми 'Zustimmen' или 'Akzeptieren'.")
        print("❗ Если вылезет капча — реши её вручную.")

        time.sleep(30)

        # Сохраняем HTML
        filename = "kleinanzeigen_snapshot.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(driver.page_source)

        print(f"✅ Готово! HTML сохранен в файл: {filename}")
        print("📂 Отправь этот файл мне в чат.")

    except Exception as e:
        print(f"❌ Ошибка: {e}")

    finally:
        driver.quit()


if __name__ == "__main__":
    save_kleinanzeigen_html()