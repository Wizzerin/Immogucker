import random
from curl_cffi import requests

class ProxyManager:
    def __init__(self, proxy_list: list):
        self.proxies = proxy_list

    def get_random_proxy(self):
        if not self.proxies:
            return None
        return random.choice(self.proxies)

    async def secure_get(self, url):
        proxy = self.get_random_proxy()

        # Имитируем реальный браузер (TLS Fingerprint)
        response = requests.get(
            url,
            impersonate="chrome110",
            proxies={"http": proxy, "https": proxy} if proxy else None,
            timeout=10,
        )
        return response