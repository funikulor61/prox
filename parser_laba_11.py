from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import csv
from datetime import datetime, timedelta
from selenium.webdriver.common.keys import Keys
import datetime
import undetected_chromedriver as uc
import pickle
import os
import re
import requests

proxy = ['http://176.111.37.5:39811',
        'http://160.22.234.4:1111',
        'http://202.47.185.153:8090',
        'http://46.122.16.54:8080',
        'http://130.110.103.245:3128',
        'http://45.175.39.71:999',
        'http://94.43.164.242:8080',
        'http://103.185.43.242:8080',
        'http://185.191.239.248:3128',
        'http://80.225.250.95:8888',
        'http://152.67.191.232:6800',
        'http://112.211.84.86:8585',
        'http://4.144.146.21:80',
        'http://13.56.147.239:3128',
        'http://18.231.20.149:3128',
        'http://173.245.49.114:80',
        'http://45.131.7.234:80',
        'http://45.131.4.75:80',
        'http://45.131.210.64:80',
        'http://45.131.6.176:80',
        'http://173.245.49.38:80'
        'http://172.64.147.24:80',
        'http://185.238.228.120:80',
        ]

class euroLines:
    def __init__(self, link, go_from , go_to , year, month , day ):
        self.link = link
        self.driver = webdriver.Firefox() 
        self.driver.get(self.link)
        self.links_list = []
        self.go_from = go_from
        self.go_to = go_to
        self.date_list = []
        self.date_list_future = []
        self.end_date = datetime(year, month, day).date()
        self.current_date = datetime.today().date()

    def get_proxy():
        arr = {}
        r = requests.get("https://advanced.name/freeproxy/6adc585c6b0cf")
        new_text = r.text.splitlines()
        for item in new_text:
            new_arr = str(item).split(':')
            arr.update({new_arr[0]:new_arr[1]})
        return arr


    def generateDates(self):
        while self.current_date <= self.end_date:
            self.date_list.append(self.current_date.strftime('%Y-%m-%d'))
            self.current_date += timedelta(days=1)

        while self.current_date <= self.end_date:
            future_date = self.current_date + timedelta(days=7)
            self.date_list_future.append(future_date.strftime('%Y-%m-%d'))
            self.current_date += timedelta(days=1) 

        with open('dateList.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.date_list) + '\n')
        
        with open('dateListFuture.txt', 'w', encoding='utf-8') as f:
            f.write(''.join(self.date_list_future) + '\n')

    def enterDataFirstAddress(self, i):
        inputFrom = self.driver.find_element(By.ID , 'route-from')
        inputFrom.send_keys(self.go_from)
        inputFrom.send_keys(Keys.ENTER)

        inputTo = self.driver.find_element(By.ID , 'route-to')
        inputTo.send_keys(self.go_to)
        inputTo.send_keys(Keys.ENTER)

        departureDate = self.driver.find_element(By.ID , 'depart-date')
        departureDate.clear()
        departureDate.send_keys(self.date_list[i])

        inputReturn = self.driver.find_element(By.ID , 'ticket-backward-checkbox').click()
        returnDate = self.driver.find_element(By.ID , 'return-date')
        returnDate.clear()
        returnDate.send_keys(self.date_list_future[i])


        buttonFinder = WebDriverWait(self.driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'По номеру телефона')]"))
        )
        self.driver.execute_script("arguments[0].click();", buttonFinder)
        time.sleep(4)

    def enterDataSecondAddress(self, i):
        inputFrom = self.driver.find_element(By.ID , 'route-from')
        inputFrom.send_keys(self.go_from)
        inputFrom.send_keys(Keys.ENTER)

        inputTo = self.driver.find_element(By.ID , 'route-to')
        inputTo.send_keys(self.go_to)
        inputTo.send_keys(Keys.ARROW_DOWN)
        inputTo.send_keys(Keys.ENTER)

        departureDate = self.driver.find_element(By.ID , 'depart-date')
        departureDate.clear()
        departureDate.send_keys(self.date_list[i])

        inputReturn = self.driver.find_element(By.ID , 'ticket-backward-checkbox').click()
        returnDate = self.driver.find_element(By.ID , 'return-date')
        returnDate.clear()
        returnDate.send_keys(self.date_list_future[i])

    def takeTickets(self):
        