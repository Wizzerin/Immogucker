import requests # Стандартная библиотека
from curl_cffi import requests as cffi_requests # Наша "стелс" библиотека

def test_standard():
    print("\n--- TEST 1: Standard Requests (Обычный запрос) ---")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get("https://www.wg-gesucht.de", headers=headers, timeout=10)
        print(f"✅ Статус: {r.status_code}")
        if r.status_code == 200:
            print("🎉 Обычный requests работает! Сайт доступен.")
        elif r.status_code == 403:
            print("🛡️ Нас заблокировали (403 Forbidden). Нужен стелс.")
    except Exception as e:
        print(f"❌ Ошибка обычного requests: {e}")

def test_cffi():
    print("\n--- TEST 2: curl_cffi (Стелс режим) ---")
    try:
        # Попробуем другую версию браузера (Safari вместо Chrome)
        r = cffi_requests.get(
            "https://www.wg-gesucht.de",
            impersonate="safari15_5",
            timeout=10
        )
        print(f"✅ Статус: {r.status_code}")
    except Exception as e:
        print(f"❌ Ошибка curl_cffi: {e}")

if __name__ == "__main__":
    test_standard()
    test_cffi()