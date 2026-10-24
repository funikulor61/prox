from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import csv
import os
import re
import logging
import random
from datetime import datetime, timedelta

# прокси
proxy = [
    "http://4.144.146.21:80",
    "http://160.22.234.4:1111",
    "http://202.47.185.153:8090",
    "http://46.122.16.54:8080",
    "http://130.110.103.245:3128",
    "http://45.175.39.71:999",
    "http://94.43.164.242:8080",
    "http://103.185.43.242:8080",
    "http://185.191.239.248:3128",
    "http://80.225.250.95:8888",
    "http://152.67.191.232:6800",
    "http://112.211.84.86:8585",
    "http://4.144.146.21:80",
    "http://13.56.147.239:3128",
    "http://18.231.20.149:3128",
    "http://173.245.49.114:80",
    "http://45.131.7.234:80",
    "http://45.131.4.75:80",
    "http://45.131.210.64:80",
    "http://45.131.6.176:80",
    "http://173.245.49.38:80",
    "http://172.64.147.24:80",
    "http://185.238.228.120:80",
]

# юзер агенты
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2) AppleWebKit/605.1.15 Version/17.2 Mobile Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]

# лог
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger("eurolines")


def timer(func):
    """декоратор лог: функция - время выполнения"""
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        log.info(f"CALL {func.__name__}")
        res = func(*args, **kwargs)
        log.info(f"DONE {func.__name__} {time.perf_counter()-start:.3f}s")
        return res
    return wrapper


class EuroLines:
    def __init__(self, link, go_from, go_to, year, month, day):
        self.link = link
        self.driver = None
        self.go_from = go_from
        self.go_to = go_to
        self.date_list = []
        self.date_list_future = []
        self.end_date = datetime(year, month, day).date()
        self.current_date = datetime.today().date()
        if self.end_date < self.current_date:
            self.end_date = datetime(self.current_date.year, 12, 31).date()
        self.results = []
        self.proxy_idx = 0
        self.ua_idx = 0
        self.req_counter = 0

    def cur_proxy(self):
        return proxy[self.proxy_idx]

    def cur_ua(self):
        return user_agents[self.ua_idx]

    def rotate(self):
        """каждые 3 запроса меняем прокси и юзер агент"""
        self.req_counter += 1
        if self.req_counter > 1 and (self.req_counter - 1) % 3 == 0:
            self.proxy_idx = (self.proxy_idx + 1) % len(proxy)
            self.ua_idx = (self.ua_idx + 1) % len(user_agents)
            log.info(f"ROTATE -> {self.cur_proxy()}")

    @timer
    def generate_dates(self):
        """даты от сегодня до конца года, обратно +7 дней"""
        d = self.current_date
        while d <= self.end_date:
            self.date_list.append(d.strftime("%Y-%m-%d"))
            self.date_list_future.append((d + timedelta(days=7)).strftime("%Y-%m-%d"))
            d += timedelta(days=1)
        open("dateList.txt", "w", encoding="utf-8").write("\n".join(self.date_list))
        open("dateListFuture.txt", "w", encoding="utf-8").write("\n".join(self.date_list_future))
        log.info(f"дат {len(self.date_list)}")

    @timer
    def create_driver(self):
        opts = Options()
        opts.set_preference("general.useragent.override", self.cur_ua())
        m = re.match(r"http://([^:]+):(\d+)", self.cur_proxy())
        host, port = m.group(1), m.group(2)
        opts.set_preference("network.proxy.type", 1)
        opts.set_preference("network.proxy.http", host)
        opts.set_preference("network.proxy.http_port", int(port))
        opts.set_preference("network.proxy.ssl", host)
        opts.set_preference("network.proxy.ssl_port", int(port))
        opts.set_preference("dom.webdriver.enabled", False)
        self.driver = webdriver.Firefox(options=opts)
        self.driver.implicitly_wait(5)
        self.driver.set_page_load_timeout(30)

    @timer
    def open_site(self):
        self.rotate()
        self.driver.get(self.link)
        # сайт React — ждём подольше, пока отрендерится поле "Поеду из"
        WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.ID, "route-from")))
        time.sleep(random.uniform(2.0, 4.0))
        # закрываем cookie баннер (мешает кликать)
        self._close_cookies()

    def _close_cookies(self):
        """закрываем баннер согласия с куками"""
        for sel in [(By.XPATH, "//button[contains(.,'Я согласен')]"),
                    (By.XPATH, "//button[contains(.,'согласен')]"),
                    (By.XPATH, "//button[contains(.,'Accept')]"),
                    (By.CSS_SELECTOR, "#onetrust-accept-btn-handler")]:
            try:
                btn = self.driver.find_element(*sel)
                self.driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.5)
                log.info("cookie баннер закрыт")
                return
            except NoSuchElementException:
                continue

    @timer
    def fill_form(self, i):
        # Откуда — клик, очистка через Ctrl+A+Delete, ввод, выбор из выпадашки
        inp = self.driver.find_element(By.ID, "route-from")
        inp.click()
        inp.send_keys(Keys.CONTROL, "a")
        inp.send_keys(Keys.BACKSPACE)
        inp.send_keys(self.go_from)
        time.sleep(1)
        self._pick_suggestion("route-from", self.go_from)

        # Куда
        inp = self.driver.find_element(By.ID, "route-to")
        inp.click()
        inp.send_keys(Keys.CONTROL, "a")
        inp.send_keys(Keys.BACKSPACE)
        inp.send_keys(self.go_to)
        time.sleep(1)
        self._pick_suggestion("route-to", self.go_to)

        # дата туда (HTML5 date input — меняем value через JS с native setter)
        self._set_date("depart-date", self.date_list[i])
        time.sleep(0.5)

        # галочка "Приобрету обратный билет"
        cb = self.driver.find_element(By.ID, "ticket-backward-checkbox")
        if not cb.is_selected():
            self.driver.execute_script("arguments[0].click();", cb)
            time.sleep(1)

        # дата обратно — поле появляется только после чекбокса
        self._set_date("return-date", self.date_list_future[i])
        time.sleep(0.5)

    def _pick_suggestion(self, field_id, text):
        """выбираем пункт в выпадашке react-autosuggest по тексту"""
        # suggestion-ы имеют класс react-autosuggest__suggestion
        try:
            items = WebDriverWait(self.driver, 8).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, ".react-autosuggest__suggestion")))
            for it in items:
                if text.lower() in it.text.lower():
                    self.driver.execute_script("arguments[0].click();", it)
                    time.sleep(0.5)
                    return
            # не нашли по тексту — кликаем первый
            if items:
                self.driver.execute_script("arguments[0].click();", items[0])
                time.sleep(0.5)
        except TimeoutException:
            # выпадашки не появилась — жмём Enter
            log.warning(f"выпадашка для {field_id} не появилась, жмём Enter")
            self.driver.find_element(By.ID, field_id).send_keys(Keys.ENTER)
            time.sleep(0.5)

    def _set_date(self, field_id, date_str):
        """HTML5 date input — меняем value через JS и триггерим события"""
        # date_str в формате YYYY-MM-DD
        script = """
        var el = document.getElementById(arguments[0]);
        if (!el) return false;
        var setter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value').set;
        setter.call(el, arguments[1]);
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
        return true;
        """
        self.driver.execute_script(script, field_id, date_str)

    @timer
    def submit(self):
        for sel in [(By.ID, "submit"),
                    (By.XPATH, "//button[contains(.,'Искать поездку')]"),
                    (By.XPATH, "//button[contains(.,'Искать')]"),
                    (By.XPATH, "//button[contains(.,'Поиск')]")]:
            try:
                btn = self.driver.find_element(*sel)
                self.driver.execute_script("arguments[0].click();", btn)
                log.info(f"клик поиск по {sel}")
                return
            except NoSuchElementException:
                continue
        # запасной — Enter в поле даты
        self.driver.find_element(By.ID, "return-date").send_keys(Keys.ENTER)

    @timer
    def wait_results(self):
        for sel in [".ride-item", ".trip-item", ".result-item",
                    "[class*='ride']", "[class*='trip']",
                    "[class*='RideItem']", "[class*='Trip']",
                    "div[class*='ticket']", "div[class*='route']"]:
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
                time.sleep(1)
                return True
            except TimeoutException:
                continue
        # пробуем сохранить HTML для отладки
        log.warning("результаты не появились — сохраняю page.html")
        open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "page.html"),
             "w", encoding="utf-8").write(self.driver.page_source)
        return False

    @timer
    def parse_routes(self, depart_date, return_date):
        """парсим, оставляем только Минск-Вильнюс"""
        out, back = [], []
        blocks = self.driver.find_elements(
            By.CSS_SELECTOR,
            ".ride-item, .trip-item, .result-item, [class*='ride'], [class*='trip']")

        for b in blocks:
            text = b.text or ""
            if not text.strip():
                continue
            line = " ".join(text.split())

            # цена
            pm = re.search(r"(\d+[.,]?\d*)\s*(€|EUR|руб|BYN)", text)
            price = pm.group(1).replace(",", ".") if pm else ""

            # время
            times = re.findall(r"\b(\d{1,2}:\d{2})\b", text)
            dt = times[0] if len(times) >= 1 else ""
            at = times[1] if len(times) >= 2 else ""

            # позиции Минск и Вильнюс в строке
            pos_m = line.lower().find("минск")
            if pos_m == -1:
                pos_m = line.lower().find("minsk")
            pos_v = line.lower().find("вильнюс")
            if pos_v == -1:
                pos_v = line.lower().find("vilnius")

            if pos_m != -1 and pos_v != -1 and pos_m < pos_v:
                out.append({"date": depart_date, "time": dt, "arrive": at, "price": price})
            elif pos_v != -1 and pos_m != -1 and pos_v < pos_m:
                back.append({"date": return_date, "time": dt, "arrive": at, "price": price})

        # соединяем туда+обратно
        for k in range(min(len(out), len(back))):
            self.results.append({
                "depart_date": out[k]["date"],
                "depart_time": out[k]["time"],
                "arrive_time": out[k]["arrive"],
                "price_out": out[k]["price"],
                "route_out": "Минск -> Вильнюс",
                "return_date": back[k]["date"],
                "depart_time_ret": back[k]["time"],
                "arrive_time_ret": back[k]["arrive"],
                "price_ret": back[k]["price"],
                "route_ret": "Вильнюс -> Минск",
            })
        if not back and out:
            for o in out:
                self.results.append({
                    "depart_date": o["date"], "depart_time": o["time"],
                    "arrive_time": o["arrive"], "price_out": o["price"],
                    "route_out": "Минск -> Вильнюс",
                    "return_date": "", "depart_time_ret": "",
                    "arrive_time_ret": "", "price_ret": "", "route_ret": "",
                })
        log.info(f"туда {len(out)} обратно {len(back)}")

    @timer
    def save_csv(self, data, fname):
        if not data:
            return
        fields = ["depart_date", "depart_time", "arrive_time", "price_out", "route_out",
                  "return_date", "depart_time_ret", "arrive_time_ret", "price_ret", "route_ret"]
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in data:
                w.writerow(r)
        log.info(f"csv {path} ({len(data)})")

    @timer
    def cleanup(self, data):
        """убираем дубликаты и пустые, нормализуем цены"""
        seen = set()
        res = []
        for r in data:
            if not r["depart_date"] and not r["return_date"]:
                continue
            key = (r["depart_date"], r["depart_time"], r["return_date"], r["depart_time_ret"])
            if key in seen:
                continue
            seen.add(key)
            for f in ("price_out", "price_ret"):
                v = str(r.get(f, "")).replace(",", ".").replace(" ", "")
                try:
                    r[f] = float(v) if v else ""
                except ValueError:
                    r[f] = ""
            res.append(r)
        log.info(f"было {len(data)} стало {len(res)}")
        return res

    @timer
    def make_plot(self, data, fname):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        dates, po, pr = [], [], []
        for r in data:
            d = datetime.strptime(r["depart_date"], "%Y-%m-%d").date()
            dates.append(d)
            po.append(float(r["price_out"]) if r["price_out"] not in ("", None) else None)
            pr.append(float(r["price_ret"]) if r["price_ret"] not in ("", None) else None)
        if not dates:
            return

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(dates, po, "o-", label="туда", color="blue")
        ax.plot(dates, pr, "s--", label="обратно", color="red")
        ax.set_xlabel("Дата")
        ax.set_ylabel("EUR")
        ax.set_title("Цены Eurolines Минск <-> Вильнюс")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
        fig.autofmt_xdate()
        ax.grid(True, alpha=0.3)
        ax.legend()
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
        fig.savefig(path, dpi=130, bbox_inches="tight")
        plt.close(fig)
        log.info(f"график {path}")

    @timer
    def run(self):
        self.generate_dates()
        if not self.date_list:
            log.error("нет дат")
            return
        self.create_driver()
        self.open_site()

        for i in range(len(self.date_list)):
            log.info(f"=== {i+1}/{len(self.date_list)}: {self.date_list[i]} -> {self.date_list_future[i]} ===")
            # каждые 3 запроса меняем прокси + UA
            if i > 0 and i % 3 == 0:
                log.info("ротация прокси+UA")
                self.driver.quit()
                self.proxy_idx = (self.proxy_idx + 1) % len(proxy)
                self.ua_idx = (self.ua_idx + 1) % len(user_agents)
                self.create_driver()
                self.open_site()

            self.fill_form(i)
            self.submit()
            time.sleep(random.uniform(2.0, 4.0))
            self.rotate()
            self.wait_results()
            time.sleep(random.uniform(2.0, 4.0))
            self.parse_routes(self.date_list[i], self.date_list_future[i])
            time.sleep(random.uniform(2.0, 4.0))

        self.driver.quit()

        cleaned = self.cleanup(self.results)

        out_dir = os.path.dirname(os.path.abspath(__file__))
        dl = os.path.abspath(os.path.join(out_dir, "..", "download"))
        if not os.path.isdir(dl):
            dl = out_dir

        self.save_csv(self.results, os.path.relpath(os.path.join(dl, "eurolines_raw.csv"), out_dir))
        self.save_csv(cleaned, os.path.relpath(os.path.join(dl, "eurolines_clean.csv"), out_dir))
        self.make_plot(cleaned, os.path.join(dl, "prices.png"))
        log.info(f"готово {len(cleaned)} строк")
