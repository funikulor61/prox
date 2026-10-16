from PIL import Image, ImageEnhance
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import os
import random
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options




class Proksya():
    def __init__(self, bel_link, solve_captcha, login , password):
        self.bel_link = bel_link
        self.solve_captcha = solve_captcha
        self.login = login
        self.password = password

    

    def changeImage(self):
        photo_capcha = Image.open('first/screens/capcha.png')

        if photo_capcha.mode != "RGB":
            photo_capcha = photo_capcha.convert("RGB")
    
        brightness_factor = 1.2
        enhancer_b = ImageEnhance.Brightness(photo_capcha)
        bright_img = enhancer_b.enhance(brightness_factor)
    
        contrast_factor = 1.5
        enhancer_c = ImageEnhance.Contrast(bright_img)
        clear_capcha = enhancer_c.enhance(contrast_factor)
    
        clear_capcha = clear_capcha.convert('1')
        clear_capcha.save("first/screens/clear_capcha.png")
        os.remove('first/screens/capcha.png')



    def getCapchaText(self):
        driver = webdriver.Chrome()
        try:
            driver.get(self.solve_captcha)

            file_input = driver.find_element(By.ID, "uploadFile")
            file_input.send_keys(os.path.abspath("first/screens/clear_capcha.png"))
            time.sleep(random.uniform(1.0, 5.0))

            driver.find_element(By.CSS_SELECTOR, 'div[style="pointer-events: auto;"]').click()
            time.sleep(10)

            result = driver.find_element(By.ID, "result__text0").text
            return result
        finally:
            driver.quit() 

    def belRegistration(self):
        options = self.changeCountry()
        driver = webdriver.Chrome(options=options)
        driver.get(self.bel_link)
        

        login_input = driver.find_element(By.ID, 'oper_user')
        login_input.clear()
        login_input.send_keys(self.login)
        time.sleep(random.uniform(1.0 , 5.0))

        password_input = driver.find_element(By.NAME, 'passwd')
        password_input.clear()
        password_input.send_keys(self.password)
        time.sleep(random.uniform(1.0 , 5.0))

        photo_capcha = driver.find_element(By.ID , 'capcher')
        photo_capcha.screenshot('first/screens/capcha.png')

        self.changeImage()
        captcha_text = self.getCapchaText()

        enter_capcha = driver.find_element(By.ID, 'cap_field')
        enter_capcha.send_keys(captcha_text)
        time.sleep(random.uniform(1.0 , 5.0))

        enter_button = driver.find_element(By.XPATH, "//input[@type='submit']")
        enter_button.click()
        driver.quit()
        

    def changeCountry(self):
        rep = random.randint(10, 100)
        options = Options()
        user_agent = f'Mozilla/5.0 (Windows NT {rep}0.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36'
        options.add_argument(f'--user-agent={user_agent}')
        proxykk = '178.124.195.80:8080'
        options.add_argument(f'--proxy-server={proxykk}')
        driver = webdriver.Chrome(options=options)
        driver.get('https://whatmyuseragent.com/')
        ua_from_site = driver.find_element(By.ID , 'ua')
        if ua_from_site.text == user_agent :
            pass
        else:
            print('НЕ ПОМЕНЯЛОСЬ , УБЕГАЙ')
        input('жми кнопку лубую')
        driver.quit()
        return options
        

    def __del__(self):
        print('Finishhh')

