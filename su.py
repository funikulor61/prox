from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from sudoku import Sudoku
import time

driver = webdriver.Chrome()

try:
    driver.get("https://absite.ru/sudoku/")
    time.sleep(3)

    rows = driver.find_element(By.XPATH, "//table").find_elements(By.TAG_NAME, "tr")
    grid, cells = [], []

    for row in rows:
        tds = row.find_elements(By.TAG_NAME, "td")
        if len(tds) != 9:
            pass
        row_values = []
        for t in tds:
            text_value = t.text.strip()
            if text_value.isdigit():
                row_values.append(int(text_value))
            else:
                row_values.append(0)
        grid.append(row_values)
        cells.append(tds)

    solution = Sudoku(3, 3, board=grid).solve().board

    for r in range(9):
        for c in range(9):
            if grid[r][c] == 0:
                cells[r][c].click()
                ActionChains(driver).send_keys(str(solution[r][c])).perform()

    driver.find_element(By.ID, "b_check").click()
    input()
finally:
    driver.quit()