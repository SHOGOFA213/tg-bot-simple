import os
from dotenv import load_dotenv
import telebot
load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
 raise RuntimeError(" .env =5F TOKEN")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
 bot.reply_to(message, "@<25F! / F2>= ?5@2O= 1>F! 0?<H< /help")
@bot.message_handler(commands=['help'])
def help_cmd(message):
 bot.reply_to(message, "/start 4 =0G0FP\n/help 4 ?><>IP")

@bot.message_handler(commands=['hello'])
def hello(message):
    bot.reply_to(message, "Привет! Я твой бот 😊")


@bot.message_handler(commands=['about'])
def about(message):
    bot.reply_to(
        message,
        "🤖 Бот: tg-bot-simple\n"
        "Автор: Shogofa Abdullahi\n"
        "Версия: 1.0\n"
        "Назначение: учебный проект"
    )


@bot.message_handler(commands=['ping'])
def ping(message):
    bot.reply_to(message, "pong 🏓")


if __name__ == "__main__":
 bot.infinity_polling(skip_pending=True)



