import os
from dotenv import load_dotenv
import telebot
import time
import json
import random
from telebot import types
from datetime import datetime
from db import *
from db import list_characters, get_character_by_id, get_user_character
from db import get_character_by_id
from ai_client import chat_once, OpenRouterError
from db import init_db

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
        bar = '█' * count
        response += f"{day}: {bar} {count}\n"
    
    bot.reply_to(message, response)

@bot.message_handler(commands=["models"])
def cmd_models(message: types.Message) -> None:
    items = list_models()
    if not items:
        bot.reply_to(message, "Список моделей пуст.")
        return
    lines = ["Доступные модели:"]
    for m in items:
        star = "★" if m["active"] else " "
        lines.append(f"{star} {m['id']}. {m['lable']}  [{m['key']}]")
    lines.append("\nАктивировать: /model <ID>")
    bot.reply_to(message, "\n".join(lines))

@bot.message_handler(commands=["model"])
def cmd_model(message: types.Message) -> None:
    arg = message.text.replace('/model', '', 1).strip()
    if not arg:
        active = get_active_model()
        bot.reply_to(message, f"Текущая активная модель: {active['lable']} {active['key']}\n(список: /model <ID> или /models)")
        return
    if not arg.isdigit():
        bot.reply_to(message, "Использование: /model <ID из /models>")
        return
    try:
        active = set_active_model(int(arg))
        bot.reply_to(message, f"Активная модель переключена: {active['lable']} {active['key']}")
    except ValueError:
        bot.reply_to(message, "Неизвестный ID модели. Сначала /models.")

@bot.message_handler(commands=["characters"])
def cmd_characters(message: types.Message) -> None:
    user_id = message.from_user.id
    items = list_characters()
    if not items:
        bot.reply_to(message, "Каталог персонажей пуст.")
        return

    try:
        current = get_user_character(user_id)["id"]
    except Exception:
        current = None

    lines = ["Доступные персонажи:"]
    for p in items:
        star = "*" if current is not None and p["id"] == current else ""
        lines.append(f"{star} {p['id']}. {p['name']}")
    lines.append("\nВыбор: /character <ID>")
    bot.reply_to(message, "\n".join(lines))

@bot.message_handler(commands=["character"])
def cmd_character(message: types.Message) -> None:
    user_id = message.from_user.id
    arg = message.text.replace("/character", "", 1).strip()
    
    if not arg:
        p = get_user_character(user_id)
        bot.reply_to(message, f"Текущий персонаж: {p['name']} \n(Сменить: /characters, затем /character <ID>)")
        return
    
    if not arg.isdigit():
        bot.reply_to(message, "Использование: /character <ID из /characters>")
        return
    
    try:
        p = set_user_character(user_id, int(arg))
        bot.reply_to(message, f"Персонаж установлен: {p['name']}")
    except ValueError:
        bot.reply_to(message, "Неизвестный ID персонажа. Сначала /characters.")

@bot.message_handler(commands=["sofia"])
def cmd_sofia(message: types.Message):
    text = "Привет! 😊 Я София — твой виртуальный помощник. Чем могу помочь?"
    bot.reply_to(message, text)

@bot.message_handler(commands=["whoami"])
def cmd_whoami(message: types.Message) -> None:
    """
    Показать активную модель и активного персонажа
    """
    try:
        # Получаем модель
        model = get_active_model()
        model_text = f"Модель: {model['lable']} ({model['key']})"
        
        # Получаем персонажа
        character = get_user_character(message.from_user.id)
        character_text = f"Персонаж: {character['name']}"
        
        bot.reply_to(message, f"{model_text}\n{character_text}")
    except Exception as e:
        bot.reply_to(message, f"Ошибка при получении данных: {str(e)}")

def _build_messages_for_character(character: dict, user_text: str) -> list[dict]:
    system = (
        f"Ты отвечаешь строго в образе персонажа: {character['name']}.\n"
        f"{character['prompt']}\n"
        "Правила:\n"
        "1) Всегда держи стиль и манеру речи выбранного персонажа.\n"
        "2) Технические ответы давай корректно и по пунктам.\n"
        "3) Не раскрывай, что ты 'играешь роль'.\n"
    )
    
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_text},
    ]

@bot.message_handler(commands=["ask_random"])
def cmd_ask_random(message: types.Message) -> None:
    q = message.text.replace("/ask_random", "", 1).strip()
    if not q:
        bot.reply_to(message, text="Использование: /ask_random <вопрос>")
        return

    q = q[:600]

    items = list_characters()
    if not items:
        bot.reply_to(message, text="Каталог персонажей пуст.")
        return

    chosen = random.choice(items)
    character = get_character_by_id(chosen["id"])

    msgs = _build_messages_for_character(character, q)
    model_key = get_active_model()["key"]

    try:
        text, ms = chat_once(
            msgs, 
            model=model_key, 
            temperature=0.2, 
            max_tokens=400
        )
        out = (text or "").strip()[:4000]
        bot.reply_to(
            message, 
            text=f"{out}\n\n⏱ {ms} мс; 🧠 модель: {model_key}; 🎭 как: {character['name']}"
        )

    except OpenRouterError as e:
        bot.reply_to(message, text=f"Ошибка: {e}")

    except Exception:
        bot.reply_to(message, text="Непредвиденная ошибка.")

def _setup_bot_commands() -> None:
    cmds = [
        types.BotCommand(command="start", description="Приветствие и помощь"),
        types.BotCommand(command="note_add", description="Добавить заметку"),
        types.BotCommand(command="note_list", description="Список заметок"),
        types.BotCommand(command="note_find", description="Поиск заметок"),
        types.BotCommand(command="note_edit", description="Изменить заметку"),
        types.BotCommand(command="note_del", description="Удалить заметку"),
        types.BotCommand(command="note_count", description="Сколько заметок"),
        types.BotCommand(command="note_export", description="Экспорт заметок в .txt"),
        types.BotCommand(command="note_stats", description="Статистика по датам"),
        types.BotCommand(command="model", description="Установить активную модель"),
        types.BotCommand(command="models", description="Получить список моделей"),
        types.BotCommand(command="ask", description="Задать вопрос модели"),
        types.BotCommand(command="ask_model", description="Задать вопрос конкретной модели"),  # ← НОВАЯ КОМАНДА
        types.BotCommand(command="ask_random", description="Задать вопрос случайной модели"),
        types.BotCommand(command="character", description="Установить активного персонажа"),
        types.BotCommand(command="characters", description="Получить список персонажей"),
        types.BotCommand(command="whoami", description="Получить активную модель и активного персонажа"),
        types.BotCommand(command="sofia", description="Поговорить с персонажем София"),
    ]

    bot.set_my_commands(cmds)

@bot.message_handler(commands=["start", "help"])
def cmd_start(message: types.Message) -> None:
    text = (
        "Привет! Это заметочник на SQLite.\n\n"
        "Команды:\n"
        "/note_add <текст>\n"
        "/note_list [N]\n"
        "/note_find <подстрока>\n"
        "/note_edit <id> <текст>\n"
        "/note_del <id>\n"
        "/note_count\n"
        "/note_export\n"
        "/note_stats [days]\n"
        "/models\n"
        "/model <id>\n"
        "/ask <вопрос>\n"
        "/ask_model <ID> <вопрос>\n"  # ← ДОБАВИТЬ ЭТУ СТРОКУ
        "/ask_random <вопрос>\n"
        "/characters\n"
        "/character <id>\n"
        "/whoami\n"
    )
    bot.reply_to(message, text)


#homework 2
@bot.message_handler(commands=["ask_model"])
def cmd_ask_model(message: types.Message) -> None:
    """
    Задать вопрос конкретной модели по ID без смены активной модели
    """
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "Использование: /ask_model <ID_модели> <вопрос>\nПример: /ask_model 2 Привет! Как дела?")
        return
    
    try:
        model_id = int(parts[1])
        question = parts[2].strip()
    except ValueError:
        bot.reply_to(message, "Ошибка: ID модели должен быть числом")
        return
    
    if not question:
        bot.reply_to(message, "Ошибка: Введите вопрос")
        return

    # Получаем все модели
    all_models = list_models()
    target_model = None
    
    for model in all_models:
        if model["id"] == model_id:
            target_model = model
            break
    
    if not target_model:
        bot.reply_to(message, f"Ошибка: Модель с ID {model_id} не найдена. Используйте /models для списка моделей")
        return

    try:
        # Упрощенный запрос без персонажей
        messages = [
            {"role": "system", "content": "Ты полезный помощник. Отвечай кратко и по делу."},
            {"role": "user", "content": question}
        ]
        
        # Используем выбранную модель
        model_key = target_model["key"]
        
        text, ms = chat_once(
            messages, 
            model=model_key, 
            temperature=0.2, 
            max_tokens=400
        )
        
        # Получаем текущую активную модель для проверки
        current_model = get_active_model()
        
        out = (text or "").strip()[:4000]
        bot.reply_to(
            message, 
            text=f"{out}\n\n⏱ {ms} мс\n🧠 использована модель: {target_model['lable']}\n⭐ активная модель: {current_model['lable']}"
        )

    except OpenRouterError as e:
        bot.reply_to(message, text=f"Ошибка: {e}")
    except Exception as e:
        bot.reply_to(message, text=f"Ошибка: {str(e)}")
if __name__ == "__main__":
    init_db()
    _setup_bot_commands()
    print("Бот запускается...")
    bot.infinity_polling(skip_pending=True)