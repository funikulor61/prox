from PIL import Image, ImageEnhance
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import os
import random
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options







PROXIES = [
    '178.121.120.196'
]
UA_TEMPLATE = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36")
CHROME_VERS = ["126", "130", "131", "132"]


class Proksya:
    def __init__(self, bel_link, solve_captcha, login, password):
        self.bel_link = bel_link
        self.solve_captcha = solve_captcha
        self.login = login
        self.password = password
        # ---------- ЛИЧНОСТЬ ЖИВЁТ ЗДЕСЬ, В ДАННЫХ ----------
        self.current_ua = None
        self.current_proxy = None
        os.makedirs("first/screens", exist_ok=True)

    # ---------- ЕДИНСТВЕННОЕ МЕСТО СОЗДАНИЯ БРАУЗЕРА ----------
    def _build_driver(self):
        """Каждый браузер рождается С ТЕКУЩЕЙ личностью. Других браузеров нет."""
        options = Options()
        if self.current_ua:
            options.add_argument(f"--user-agent={self.current_ua}")
        if self.current_proxy:
            options.add_argument(f"--proxy-server={self.current_proxy}")  # БЕЗ пробелов!
        return webdriver.Chrome(options=options)

    # ---------- СМЕНА ЛИЧНОСТИ = ОБНОВЛЕНИЕ ДАННЫХ ----------
    def changeIdentity(self):
        self.current_ua = UA_TEMPLATE.format(ver=random.choice(CHROME_VERS))
        self.current_proxy = random.choice(PROXIES)

    # ---------- ПРОВЕРКА (той же личностью!) ----------
    def checkIdentity(self):
        driver = self._build_driver()          # та же фабрика — та же личность
        try:
            driver.get("http://api.ipify.org?format=json")   # http — фри-прокси его умеют
            time.sleep(3)
            ip_seen = driver.find_element("tag name", "body").text
            site_ua = driver.execute_script("return navigator.userAgent;")

            proxy_ip = self.current_proxy.split("//")[-1].split(":")[0]
            ua_ok = (site_ua == self.current_ua)
            ip_ok = (proxy_ip in ip_seen)      # IP выхода = IP прокси?

            if not ua_ok: print(f"🚫 UA не применился: {site_ua[:60]}")
            if not ip_ok: print(f"🚫 Прокси не работает, сайт видел: {ip_seen}")
            return ua_ok and ip_ok
        finally:
            driver.quit()

    # ---------- РАБОТА (теперь ТОЖЕ с личностью) ----------
    def belRegistration(self):
        driver = self._build_driver()          # ← вот оно: больше не голый Chrome()
        try:
            driver.get(self.bel_link)
            # ...логин, пароль, капча, клик — без изменений...
        finally:
            driver.quit()