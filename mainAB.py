from adeptToAB import parserAB
import time


def main():
    parser = parserAB(
        link='https://atlasbus.by/',
        name='Иван',
        surname='Иванов',
        phone_number='+375291234567',
        from_where='Минск',
        where_to='Витебск',
        data='24 октября',
        departure_time='15:00',    # ← НОВОЕ: точное время
    )

    try:
        if not parser.logged_in:
            parser.saveSession()
            parser.logged_in = True

        parser.openBus()
        time.sleep(3)

        # ⬇️ Новый шаг: найти рейс на 15:00 и кликнуть "Заказать"
        parser.clickOrderAtTime()

        input("Enter для закрытия...")
    finally:
        try:
            parser.driver.quit()
        except Exception:
            pass


if __name__ == '__main__':
    main()