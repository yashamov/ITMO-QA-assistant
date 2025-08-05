from parser import fetch_all_programs

# Загружаем данные при запуске, чтобы не парсить при каждом вопросе
PROGRAM_DATA = fetch_all_programs()

def get_program_list():
    # Возвращает список доступных программ для выбора
    return list(PROGRAM_DATA.keys())

def get_program_data(slug):
    # Получить все данные по конкретной программе
    return PROGRAM_DATA.get(slug)

def pretty_program_names():
    # Для вывода человекочитаемых названий
    return {
        "ai": "Искусственный интеллект",
        "ai_product": "Управление ИИ-продуктами / AI Product"
    }
