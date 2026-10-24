from datetime import datetime
from eurolines_scraper import EuroLines

# конфиг
LINK = "https://www.eurolines.lt/ru"
GO_FROM = "Минск"
GO_TO = "Вильнюс"
YEAR = datetime.today().year
MONTH = 12
DAY = 31


def main():
    print("=" * 50)
    print(" Eurolines Минск -> Вильнюс")
    print("=" * 50)
    print(f" сайт:    {LINK}")
    print(f" маршрут:  {GO_FROM} -> {GO_TO}")
    print(f" до:      {YEAR}-{MONTH:02d}-{DAY:02d}")
    print("=" * 50)

    scraper = EuroLines(
        link=LINK,
        go_from=GO_FROM,
        go_to=GO_TO,
        year=YEAR,
        month=MONTH,
        day=DAY,
    )
    scraper.run()

    print()
    print("Готово. Проверь:")
    print("  scraper.log           лог")
    print("  dateList.txt          даты")
    print("  download/eurolines_raw.csv")
    print("  download/eurolines_clean.csv")
    print("  download/prices.png   график")


if __name__ == "__main__":
    main()