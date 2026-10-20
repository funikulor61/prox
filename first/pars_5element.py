from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import csv

class Parser:
    def __init__(self, link):
        self.link = link
        self.driver = webdriver.Firefox() 
        self.driver.get(self.link)
        self.links_list = []

    def acceptCoockie(self):
            clickable_element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, 'popup-cookie__confirm'))
            )
            clickable_element.click()
            print("Куки успешно приняты.")
            time.sleep(1)

    def openSite(self):
        div_blocks = self.driver.find_elements(By.CLASS_NAME, "c-list__center")
        current_page_links = 0
        for div in div_blocks:
            link_element = div.find_element(By.XPATH, ".//a")
            href = link_element.get_attribute("href")
            if href and href not in self.links_list:
                self.links_list.append(href)
                current_page_links += 1
                print(f"Найдена ссылка: {href}")
        print(f"--- Всего собрано уникальных ссылок: {len(self.links_list)} ---")

    def nextPage(self):
            clickable_element = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CLASS_NAME, 'show-more'))
            )
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", clickable_element)
            time.sleep(1)
            clickable_element.click()
            print("Нажата кнопка 'Показать еще'. Загрузка следующей страницы...")
            time.sleep(4) 
            return True

    def get_information(self):
        # Создаем один общий словарь для всех ноутбуков
        self.all_notebooks_characteristics = {}

        for link in self.links_list:
            print(f"Парсим: {link}")
            self.driver.get(link + '#characteristics')
            time.sleep(3) # Даем странице 3 секунды, чтобы полностью загрузиться
            
            list_tables = []
            # Считаем, сколько всего таблиц на странице
            tables_count = len(self.driver.find_elements(By.CLASS_NAME, 'prod-tab-specifications__table'))
            
            # Вместо списка элементов перебираем их по номерам (индексам)
            for i in range(tables_count):
                fresh_tables = self.driver.find_elements(By.CLASS_NAME, 'prod-tab-specifications__table')
                list_tables.append(fresh_tables[i].text)
            self.all_notebooks_characteristics[link] = list_tables

    def save_to_csv(self, filename: str = 'notebooks_clean.csv') -> None:
        """
        Сохраняет характеристики всех ноутбуков в CSV-файл.
        Структура таблиц на сайте: строки идут парами (название -> значение).
        Строки без пары считаются заголовками секций и пропускаются.
        """
        parsed_notebooks = []
        all_features = set()

        # 1. Парсим каждый ноутбук: пары "название -> значение"
        for link, characteristics_list in self.all_notebooks_characteristics.items():
            notebook = {'Ссылка на товар': link}

            full_text = "\n".join(characteristics_list)
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]

            i = 0
            while i < len(lines) - 1:
                name, value = lines[i], lines[i + 1]
                # Эвристика: считаем строку значением, если она похожа на данные, а не на заголовок
                is_value = (
                    value in ('Да', 'Нет')
                    or len(value) > 100
                    or any(ch.isdigit() for ch in value)
                    or ',' in value
                    or ' ' in value
                )
                if is_value:
                    notebook[name] = value
                    all_features.add(name)
                    i += 2
                else:
                    i += 1  # заголовок секции, пропускаем

            parsed_notebooks.append(notebook)

        # 2. Формируем шапку: ссылка первой колонкой, остальные по алфавиту
        header = ['Ссылка на товар'] + sorted(all_features)

        # 3. Записываем в CSV (разделитель ';' для совместимости с Excel)
        with open(filename, mode='w', encoding='utf-8-sig', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=header, delimiter=';')
            writer.writeheader()
            for notebook in parsed_notebooks:
                writer.writerow({col: notebook.get(col, '-') for col in header})

        print(f"\nТаблица сохранена как {filename}!")
            