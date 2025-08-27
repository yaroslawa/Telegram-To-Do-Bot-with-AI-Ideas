import os
from dotenv import load_dotenv
import telebot
from telebot import types
from datetime import datetime, timedelta
from openai import APIConnectionError, APIStatusError, OpenAI, RateLimitError



load_dotenv()

token = os.getenv("BOT_TOKEN")
llm_token = os.getenv("OPEN_ROUTER_API_TOKEN")
HELP = "" \
"/help - напечатать справку по программе.\n" \
"/add - добавить задачу в список.\n" \
"/show - напечатать все добавленные задачи.\n" \
"/random - получить случайную задачу на сегодня"
today = []
tomorrow = []
other = []
tmp_data = {}
todo = {"today": today, "tomorrow": tomorrow, "other": other}

bot = telebot.TeleBot(token)

@bot.message_handler(commands=["help"])
def help(message):
    bot.send_message(message.chat.id, HELP)

@bot.message_handler(commands=["add"])
def add(message):
    msg = bot.send_message(message.chat.id, "📅 Write date for a task.")
    bot.register_next_step_handler(msg, process_date)
    
def process_date(message):
    try:
        tmp_data[message.chat.id] = message.text.lower()

        #обработка даты на сегодня и завтра если ввели в формате дд.мм.гггг
        now = datetime.now()
        tomorrow_inp = now + timedelta(days=1)
        now = now.strftime("%d.%m.%Y")
        tomorrow_inp = tomorrow_inp.strftime("%d.%m.%Y")
        if tmp_data[message.chat.id] == now:
            tmp_data[message.chat.id] = "today"
        if tmp_data[message.chat.id] == tomorrow_inp:
            tmp_data[message.chat.id] = "tomorrow"
        
        if tmp_data[message.chat.id] not in todo:
            tmp_data[message.chat.id] = "other"
        msg = bot.send_message(message.chat.id, "✏️ Write your task.")
        bot.register_next_step_handler(msg, process_task)
    except Exception as e:
        bot.reply_to(message, "❌ Error! Please, try again /add")

def process_task(message):
    try:
        task = message.text
        if message.chat.id not in tmp_data:
            raise ValueError("Date information lost...")
        
        # добавление задачи в список 
        todo[tmp_data[message.chat.id]].append(task)
        
        bot.send_message(message.chat.id, "✅ Your task: \""+task+"\" was added to list.")
        del tmp_data[message.chat.id]
    except Exception as e:
        bot.reply_to(message, "Error! Please, try again /add")

@bot.message_handler(commands=["show"])
def show(message):
    try:
        response = "📋 Your tasks:\n"
        for date, tasks in todo.items():
            if tasks:
                response += f"<b>{date.capitalize()}:</b>"
                for i, task in enumerate(tasks, 1):
                    response += f"{i}. {task}\n"
            else:
                response += f"<b>\n{date.capitalize()}:</b> No tasks\n"
        bot.send_message(message.chat.id, response, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, "Error! Please, try again /show")
    
@bot.message_handler(commands=["random"])
def get_random(message):
    try:
        bot.send_chat_action(message.chat.id, "typing")

        client = OpenAI(
            base_url = "https://openrouter.ai/api/v1",
            api_key = llm_token,
        )
        
        completion = client.chat.completions.create(
            model="mistralai/mistral-7b-instruct:free",
            messages=[
                {
                    "role": "system",
                    "content": "You are a creative assistant that suggests fun activities."
                },
                {
                "role": "user",
                "content": "Generate only one random fun ativity for today. I need 5 words max. Without explanations. Without lists. Just one simple idea"
                }
            ],
            max_tokens=50,
        )
        idea = completion.choices[0].message.content.strip()

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        btn_yes = types.KeyboardButton("Yes")
        btn_no = types.KeyboardButton("No")
        markup.add(btn_yes, btn_no)

        bot.send_message(
            message.chat.id,
            f"🎲 <b>Try this today:</b>\n{idea}/n Add idea to the list?",
            parse_mode="HTML",
            reply_markup=markup
        )
        
    except APIConnectionError:
        bot.send_message(message.chat.id, "Error! Please check the connection.")
    except RateLimitError:
        bot.send_message(message.chat.id, "Error! Too many requests.")
    except APIStatusError as e:
        bot.send_message(message.chat.id, f"Error! API error: ({e.status_code})")
    except Exception as e:
        bot.send_message(message.chat.id, f"Error! Unknown error: {e}")
    except Exception as e:
        bot.reply_to(message, "Error! Please, try again /random")



bot.polling(none_stop=True)