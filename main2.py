import os
from dotenv import load_dotenv
import telebot
import time
import json
from datetime import datetime

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("В .env файле нет TOKEN")

bot = telebot.TeleBot(TOKEN)

# Загрузка заметок из файла
def load_notes():
    global notes, note_counter
    try:
        with open('notes.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            notes = data.get('notes', {})
            # Конвертируем ключи обратно в int (json сохраняет как str)
            notes = {int(k): v for k, v in notes.items()}
            note_counter = data.get('counter', 1)
    except FileNotFoundError:
        notes = {}
        note_counter = 1

# Сохранение заметок в файл
def save_notes():
    with open('notes.json', 'w', encoding='utf-8') as f:
        json.dump({
            'notes': notes,
            'counter': note_counter
        }, f, ensure_ascii=False, indent=2)

# Загружаем заметки при старте
load_notes()

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Я бот для заметок. Используй /help для списка команд.")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    help_text = """
Доступные команды:
/note_add <текст> - Добавить заметку
/note_list - Показать все заметки
/note_find <запрос> - Найти заметку
/note_edit <id> <новый текст> - Изменить заметку
/note_del <id> - Удалить заметку
/note_count - Показать количество заметок
"""
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['note_add'])
def note_add(message):
    global note_counter
    text = message.text.replace('/note_add', '').strip()
    if not text:
        bot.reply_to(message, "Ошибка: Укажите текст заметки.")
        return
    notes[note_counter] = text
    save_notes()  # Сохраняем после добавления
    bot.reply_to(message, f"Заметка #{note_counter} добавлена: {text}")
    note_counter += 1

@bot.message_handler(commands=['note_list'])
def note_list(message):
    if not notes:
        bot.reply_to(message, "Заметок пока нет.")
        return
    response = "Список заметок:\n" + "\n".join([f"{id}: {text}" for id, text in notes.items()])
    bot.reply_to(message, response)

@bot.message_handler(commands=['note_find'])
def note_find(message):
    query = message.text.replace('/note_find', '').strip()
    if not query:
        bot.reply_to(message, "Ошибка: Укажите поисковый запрос.")
        return
    found = {id: text for id, text in notes.items() if query in text}
    if not found:
        bot.reply_to(message, "Заметки не найдены.")
        return
    response = "Найденные заметки:\n" + "\n".join([f"{id}: {text}" for id, text in found.items()])
    bot.reply_to(message, response)

@bot.message_handler(commands=['note_edit'])
def note_edit(message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "Ошибка: Используйте /note_edit <id> <новый текст>")
        return
    try:
        note_id = int(parts[1])
        new_text = parts[2]
    except ValueError:
        bot.reply_to(message, "Ошибка: ID должен быть числом.")
        return
    if note_id not in notes:
        bot.reply_to(message, f"Ошибка: Заметка #{note_id} не найдена.")
        return
    notes[note_id] = new_text
    save_notes()  # Сохраняем после изменения
    bot.reply_to(message, f"Заметка #{note_id} изменена на: {new_text}")

@bot.message_handler(commands=['note_del'])
def note_del(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Ошибка: Укажите ID заметки для удаления.")
        return
    try:
        note_id = int(parts[1])
    except ValueError:
        bot.reply_to(message, "Ошибка: ID должен быть числом.")
        return
    if note_id not in notes:
        bot.reply_to(message, f"Ошибка: Заметка #{note_id} не найдена.")
        return
    del notes[note_id]
    save_notes()  # Сохраняем после удаления
    bot.reply_to(message, f"Заметка #{note_id} удалена.")

@bot.message_handler(commands=['note_count'])
def note_count(message):
    count = len(notes)
    if count == 0:
        bot.reply_to(message, "У вас пока нет заметок.")
    elif count == 1:
        bot.reply_to(message, "У вас 1 заметка.")
    elif 2 <= count <= 4:
        bot.reply_to(message, f"У вас {count} заметки.")
    else:
        bot.reply_to(message, f"У вас {count} заметок.")

  
       
@bot.message_handler(commands=['note_export'])
def note_export(message):
    if not notes:
        bot.reply_to(message, "Нет заметок для экспорта.")
        return
    
    # Создаем имя файла с временной меткой
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"notes_{timestamp}.txt"
    
    try:
        # Записываем заметки в файл
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Экспорт заметок от {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Всего заметок: {len(notes)}\n")
            f.write("=" * 50 + "\n\n")
            
            for note_id, text in sorted(notes.items()):
                f.write(f"Заметка #{note_id}:\n")
                f.write(f"{text}\n")
                f.write("-" * 30 + "\n")
        
        # Отправляем файл пользователю
        with open(filename, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="Ваши заметки экспортированы в файл.")
        
        # Удаляем временный файл
        os.remove(filename)
        
    except Exception as e:
        bot.reply_to(message, f"Ошибка при экспорте: {str(e)}")






@bot.message_handler(commands=['note_stats'])
def note_stats(message):
    # Здесь будет логика сбора статистики
    # и создание ASCII-гистограммы
    
    stats = {
        'Пн': 5,
        'Вт': 8, 
        'Ср': 3,
        'Чт': 12,
        'Пт': 7,
        'Сб': 2,
        'Вс': 4
    }
    
    response = "Активность по заметкам:\n"
    for day, count in stats.items():
        bar = '█' * count  # Создаем строку из символов
        response += f"{day}: {bar} {count}\n"
    
    bot.reply_to(message, response)

    
if __name__ == "__main__":
    print("Бот запускается...")
    bot.infinity_polling(skip_pending=True)