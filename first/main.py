from proxClass import Proksya

def main():
    parser = Proksya(   'https://issaold.beltelecom.by/main.html',
                        'https://www.prepostseo.com/ru/image-to-text',
                        'funikulor67',
                        '12345678910'
                     )
    parser.belRegistration()

if __name__ == "__main__":
    main()
