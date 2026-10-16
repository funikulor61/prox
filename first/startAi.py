from proxFromAi import Proksya
import time
import random

if __name__ == "__main__":
    p = Proksya(bel_link="https://issaold.beltelecom.by/main.html",
                solve_captcha="https://...", login="...", password="...")

    while True:                                  # цикл вместо рекурсии
        p.changeIdentity()                       # 1. новые данные личности
        if p.checkIdentity():                    # 2. проверили их
            p.belRegistration()                  # 3. работаем В ТОЙ ЖЕ ЛИЧНОСТИ
        else:
            print("⛔ Личность не встала — пропуск раунда")
        time.sleep(random.randint(1, 6))