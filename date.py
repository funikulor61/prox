from datetime import datetime, timedelta

# Укажите вашу конечную дату в формате (Год, Месяц, День)
end_date = datetime(2026, 12, 31).date()
# Берем ТЕКУЩУЮ дату БЕЗ часов и минут (строго 00:00:00)
current_date = datetime.today().date()  

date_list = []


while current_date <= end_date:
    date_list.append(current_date.strftime('%Y-%m-%d'))
    current_date += timedelta(days=1)


while current_date <= end_date:
    # Прибавляем 7 дней к текущей дате при записи в список
    shifted_date = current_date + timedelta(days=7)
    date_list.append(shifted_date.strftime('%Y-%m-%d'))
    # Сам цикл продолжает идти по порядку (+1 день)
    current_date += timedelta(days=1) 


with open('output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(date_list) + '\n')
# Вывод первых 5 дат для проверки
print(date_list[:5]) 
