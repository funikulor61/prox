from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import csv
from selenium.webdriver.common.keys import Keys
import datetime
import undetected_chromedriver as uc
import pickle
import os
import re


MONTHS = {
    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6,
    'июля': 7, 'августа': 8, 'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12,
}

# ⭐ ОБХОД: путь к файлу с сохранёнными cookies
SESSION_FILE = r"D:\prox\atlasbus_session.pkl"


class parserAB:
    def __init__(self, link, name, surname, phone_number, from_where, where_to, data, departure_time=None):
        self.link = link
        options = uc.ChromeOptions()
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        import os
        profile_dir = os.path.join(os.path.expanduser("~"), "atlasbus_profile")
        self.driver = uc.Chrome(
            options=options,
            user_data_dir=profile_dir,
            version_main=156,
        )

        self.name = name
        self.surname = surname
        self.phone_number = phone_number
        self.from_where = from_where
        self.where_to = where_to
        self.date = data
        self.departure_time = departure_time  # ← НОВОЕ: например "15:00"

        self.logged_in = self.loadSession()

    # ------------------------------------------------------------------
    # СЕССИЯ: СОХРАНЕНИЕ / ЗАГРУЗКА
    # ------------------------------------------------------------------
    def saveSession(self):
        """Запустить ОДИН РАЗ вручную. Логинимся → сохраняем cookies."""
        self.driver.get("https://atlasbus.by/")
        self.acceptCoockie()
        self.enterProfile()
        # ⭐ ОБХОД: ждём пока вы вручную решите капчу + введёте SMS
        input("👉 Дождитесь SMS, введите код, завершите вход. Потом нажмите Enter...")
        # ⭐ ОБХОД: сериализуем все cookies в файл
        pickle.dump(self.driver.get_cookies(), open(SESSION_FILE, "wb"))
        print(f"✅ Cookies сохранены в {SESSION_FILE}")

    def loadSession(self):
        """Грузит cookies ДО открытия целевой страницы — капча не нужна."""
        if not os.path.exists(SESSION_FILE):
            print("⚠️ Файл сессии не найден — будет обычный вход")
            return False
        # ⭐ ОБХОД: открыть домен → поставить cookies → refresh
        # (cookies можно ставить только на уже открытом домене)
        self.driver.get("https://atlasbus.by/")
        for cookie in pickle.load(open(SESSION_FILE, "rb")):
            self.driver.add_cookie(cookie)
        self.driver.refresh()
        print("✅ Сессия восстановлена")
        return True

    # ------------------------------------------------------------------
    # ОСНОВНЫЕ МЕТОДЫ
    # ------------------------------------------------------------------
    def acceptCoockie(self):
        try:
            clickable_element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, 'cm__btn'))
            )
            clickable_element.click()
            print("Куки успешно приняты.")
            time.sleep(1)
        except TimeoutException:
            print("Элемент '.cm__btn' не найден, продолжаем выполнение кода...")

    def dateToIso(self):
        """'30 октября' -> '2026-10-30'"""
        day, month = self.date.split()
        m = MONTHS[month.lower()]
        today = datetime.date.today()
        d = datetime.date(today.year, m, int(day))
        if d < today:
            d = datetime.date(today.year + 1, m, int(day))
        time.sleep(3)
        return d.isoformat()

    def openBus(self):
        url = (f'https://atlasbus.by/Маршруты/{self.from_where}/{self.where_to}'
               f'?date={self.dateToIso()}&passengers=1')
        self.driver.get(url)
        self.acceptCoockie()
        time.sleep(3)

        # ⭐ ОБХОД: если сессия уже восстановлена — enterProfile не вызываем (капча не нужна)
        if not self.logged_in:
            self.enterProfile()

    def enterProfile(self):
        # ⭐ ОБХОД: проверяем, жива ли сессия (UC на Win иногда падает)
        try:
            _ = self.driver.current_url
        except Exception:
            print("⚠️ Сессия умерла, открываем заново...")
            self.driver.get("https://atlasbus.by/")
            time.sleep(5)

        # ⭐ ОБХОД: расширяем окно — иначе адаптивная вёрстка прячет кнопку входа
        self.driver.set_window_size(1920, 1080)
        time.sleep(5)  # ⭐ ОБХОД: увеличено с 3 до 5 сек — SPA рендерится дольше

        # ⭐ ОБХОД: 30 сек вместо 15 — больше времени на рендер SPA
        # ⭐ ОБХОД: contains(.,'Войти') через точку — ищет текст во всех потомках,
        #          а не только в прямых text-узлах (вложенность span>MuiButton-label)
        enter = WebDriverWait(self.driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Войти')]"))
        )
        # ⭐ ОБХОД: JS-клик обходит перекрытие cookie-баннером
        self.driver.execute_script("arguments[0].click();", enter)
        time.sleep(4)

        number = WebDriverWait(self.driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'По номеру телефона')]"))
        )
        self.driver.execute_script("arguments[0].click();", number)
        time.sleep(4)

        element = self.driver.find_element(
            By.CSS_SELECTOR, 'input[class~="MuiInputBase-input"][class~="MuiInput-input"]'
        )
        element.send_keys(Keys.CONTROL + "a")
        time.sleep(2)
        element.send_keys(Keys.BACK_SPACE)
        time.sleep(4)
        element.send_keys(self.phone_number)
        time.sleep(4)

        messageSMS = WebDriverWait(self.driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Войти по SMS')]"))
        )
        self.driver.execute_script("arguments[0].click();", messageSMS)
        time.sleep(4)


    def clickOrderAtTime(self):
        """Кликает 'Заказать' у рейса с точным временем отправления self.departure_time."""
        if not self.departure_time:
            print("⚠️ Время отправления не задано")
            return False

        buttons = self.driver.find_elements(By.XPATH, "//button[contains(.,'Заказать')]")
        print(f"Найдено 'Заказать': {len(buttons)} | ищем отправление {self.departure_time}")

        for i, btn in enumerate(buttons):
            try:
                # Поднимаемся к карточке рейса (MuiGrid-container)
                card = btn
                for _ in range(6):
                    card = card.find_element(By.XPATH, "..")
                    cls = card.get_attribute("class") or ""
                    if "MuiGrid-container" in cls:
                        break

                # Первый div с текстом HH:MM — это время отправления
                departure = None
                for d in card.find_elements(By.CSS_SELECTOR, "div"):
                    t = (d.text or "").strip()
                    if re.match(r"^\d{2}:\d{2}$", t):
                        departure = t
                        break

                if departure == self.departure_time:
                    print(f"  [{i}] {departure} → ✅ кликаем")
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'}); arguments[0].click();",
                        btn
                    )
                    return True
            except Exception as e:
                print(f"  [{i}] ошибка: {e}")

        print(f"❌ Рейс {self.departure_time} не найден")
        return False