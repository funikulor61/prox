from proxClass import Proksya
from pars_5element import Parser
# def main():
    # parser = Proksya(   'https://issaold.beltelecom.by/main.html',
    #                     'https://www.prepostseo.com/ru/image-to-text',
    #                     'funikulor67',
    #                     '12345678910'
    #                  )
    # parser.belRegistration()
def main():
    parser = Parser(
    'https://5element.by/catalog/1383-noutbuki'
    )
    parser.acceptCoockie()
    TOTAL_PAGES_TO_PARSE = int(input('Сколько страниц парсить : \n'))
    parser.openSite()
    for page_num in range(2, TOTAL_PAGES_TO_PARSE + 1):
        print(f"Переход на страницу {page_num}...")
        has_next = parser.nextPage()
        if not has_next:
            print("Страницы досрочно закончились.")
            break
        parser.openSite()
    parser.get_information()
    parser.save_to_csv()
if __name__ == "__main__":
    main()
