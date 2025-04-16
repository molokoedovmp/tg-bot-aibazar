import telebot
from telebot import types
import requests
import time
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Константы
TOKEN = '8053040814:AAGUhF1URJGzyTpgtte9tDHuyla91e_VS7M'  # Замените на свой токен
MANAGER_ID = 7662108122  # ID менеджера
MANAGER_USERNAME = '@aibazaru'  # Username менеджера
CURRENCY_API_URL = 'https://www.cbr-xml-daily.ru/daily_json.js'  # API для получения курса валют
COMMISSION_HIDDEN = 750  # Скрытая комиссия в рублях
RATE_INCREASE = 5  # Увеличение курса доллара

# Инициализация бота
bot = telebot.TeleBot(TOKEN)

# Словарь для хранения данных пользователей
user_data = {}

# Функция для получения курса доллара с увеличением
def get_usd_rate():
    try:
        response = requests.get(CURRENCY_API_URL)
        data = response.json()
        # Добавляем увеличение к курсу
        return data['Valute']['USD']['Value'] + RATE_INCREASE
    except Exception as e:
        logger.error(f"Ошибка при получении курса валют: {e}")
        return 100 + RATE_INCREASE  # Значение по умолчанию, если API недоступен

# Главное меню
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn1 = types.KeyboardButton('Оплата подписки')
    btn2 = types.KeyboardButton('Создание сайтов')
    btn3 = types.KeyboardButton('Другие услуги')
    markup.add(btn1, btn2, btn3)
    
    bot.send_message(message.chat.id, 
                     f"Здравствуйте, {message.from_user.first_name}! Выберите услугу:", 
                     reply_markup=markup)

# Обработчик текстовых сообщений
@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    text = message.text
    
    # Инициализация данных пользователя, если их еще нет
    if chat_id not in user_data:
        user_data[chat_id] = {'state': None}
    
    # Обработка главного меню
    if text == 'Оплата подписки':
        user_data[chat_id]['state'] = 'subscription_service'
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        services = ['Claude', 'Lovable', 'OpenAI', 'v0.dev', 'Cursor', 'Другое']
        buttons = [types.KeyboardButton(service) for service in services]
        markup.add(*buttons)
        markup.add(types.KeyboardButton('Отмена'))
        bot.send_message(chat_id, "Какой сервис вы хотите оплатить?", reply_markup=markup)
    
    elif text == 'Создание сайтов':
        user_data[chat_id]['state'] = 'website_type'
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        website_types = [
            'Сайт-визитка/лендинг без БД',
            'Сайт-магазин с каталогом и БД',
            'Сайт-магазин с каталогом, БД и оплатой через ЮKassa',
            'Что-то другое'
        ]
        buttons = [types.KeyboardButton(website_type) for website_type in website_types]
        markup.add(*buttons)
        markup.add(types.KeyboardButton('Отмена'))
        bot.send_message(chat_id, "Выберите тип сайта:", reply_markup=markup)
    
    elif text == 'Другие услуги':
        user_data[chat_id]['state'] = 'other_services'
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        back_btn = types.KeyboardButton('Вернуться в главное меню')
        markup.add(back_btn)
        bot.send_message(chat_id, 
                         f"Для обсуждения других услуг, пожалуйста, свяжитесь с менеджером: {MANAGER_USERNAME}", 
                         reply_markup=markup)
        
        # Отправляем уведомление менеджеру
        bot.send_message(MANAGER_ID, 
                         f"Пользователь {message.from_user.first_name} (@{message.from_user.username}) интересуется другими услугами.")
    
    # Обработка состояний для оплаты подписки
    elif user_data[chat_id]['state'] == 'subscription_service':
        if text == 'Отмена':
            start(message)
            return
        
        user_data[chat_id]['service'] = text
        user_data[chat_id]['state'] = 'subscription_amount'
        
        # Предлагаем стандартные суммы
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        btn1 = types.KeyboardButton('20')
        btn2 = types.KeyboardButton('50')
        btn3 = types.KeyboardButton('Другая сумма')
        btn4 = types.KeyboardButton('Отмена')
        markup.add(btn1, btn2)
        markup.add(btn3, btn4)
        
        bot.send_message(chat_id, 
                         f"Вы выбрали: {text}\nВыберите стоимость подписки в долларах или укажите другую сумму:", 
                         reply_markup=markup)
    
    elif user_data[chat_id]['state'] == 'subscription_amount':
        if text == 'Отмена':
            start(message)
            return
        
        if text == 'Другая сумма':
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            markup.add(types.KeyboardButton('Отмена'))
            bot.send_message(chat_id, "Введите сумму в долларах (только число):", reply_markup=markup)
            return
        
        try:
            # Пробуем преобразовать текст в число
            amount_usd = float(text)
            usd_rate = get_usd_rate()  # Уже включает увеличение на 5 рублей
            amount_rub = amount_usd * usd_rate + COMMISSION_HIDDEN  # Добавляем скрытую комиссию
            
            user_data[chat_id]['amount_usd'] = amount_usd
            user_data[chat_id]['amount_rub'] = amount_rub
            user_data[chat_id]['usd_rate'] = usd_rate
            user_data[chat_id]['state'] = 'confirm_payment'
            
            # Формируем чек без указания комиссии
            receipt = f"ЧЕК №{int(time.time())}\n"
            receipt += f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            receipt += f"Услуга: Оплата подписки {user_data[chat_id]['service']}\n"
            receipt += f"Стоимость: ${amount_usd:.2f}\n"
            receipt += f"Курс USD: {usd_rate:.2f} руб.\n"
            receipt += f"Итого к оплате: {amount_rub:.2f} руб."
            
            user_data[chat_id]['receipt'] = receipt
            
            # Отправляем чек менеджеру
            user_info = f"Новый запрос на оплату подписки от пользователя {message.from_user.first_name}"
            if message.from_user.username:
                user_info += f" (@{message.from_user.username})"
            bot.send_message(MANAGER_ID, f"{user_info}\n\n{receipt}")
            
            # Создаем инструкцию для пользователя
            instruction = f"Пожалуйста, при общении с менеджером, скопируйте и отправьте ему следующий чек:\n\n{receipt}"
            
            # Создаем кнопки
            markup = types.InlineKeyboardMarkup(row_width=1)
            copy_btn = types.InlineKeyboardButton("Скопировать чек", callback_data="copy_receipt")
            contact_btn = types.InlineKeyboardButton("Связаться с менеджером", 
                                                   url=f"https://t.me/{MANAGER_USERNAME.replace('@', '')}")
            cancel_btn = types.InlineKeyboardButton("Отмена", callback_data="cancel")
            markup.add(copy_btn, contact_btn, cancel_btn)
            
            bot.send_message(chat_id, instruction, reply_markup=markup)
            
        except ValueError:
            bot.send_message(chat_id, "Пожалуйста, введите корректное число.")
    
    # Обработка состояний для создания сайтов
    elif user_data[chat_id]['state'] == 'website_type':
        if text == 'Отмена':
            start(message)
            return
        
        user_data[chat_id]['website_type'] = text
        
        # Формируем запрос
        request = f"ЗАПРОС НА СОЗДАНИЕ САЙТА\n"
        request += f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        request += f"Тип сайта: {text}\n"
        request += f"От пользователя: {message.from_user.first_name}"
        if message.from_user.username:
            request += f" (@{message.from_user.username})"
        
        user_data[chat_id]['request'] = request
        
        # Отправляем запрос менеджеру
        bot.send_message(MANAGER_ID, request)
        
        # Создаем инструкцию для пользователя
        instruction = f"Пожалуйста, при общении с менеджером, скопируйте и отправьте ему следующий запрос:\n\n{request}"
        
        # Создаем кнопки
        markup = types.InlineKeyboardMarkup(row_width=1)
        copy_btn = types.InlineKeyboardButton("Скопировать запрос", callback_data="copy_request")
        contact_btn = types.InlineKeyboardButton("Связаться с менеджером", 
                                               url=f"https://t.me/{MANAGER_USERNAME.replace('@', '')}")
        cancel_btn = types.InlineKeyboardButton("Отмена", callback_data="cancel")
        markup.add(copy_btn, contact_btn, cancel_btn)
        
        bot.send_message(chat_id, instruction, reply_markup=markup)
    
    # Обработка отмены и возврата в главное меню
    elif text == 'Отмена' or text == 'Вернуться в главное меню':
        start(message)

# Обработчик callback-запросов
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    
    if call.data == "cancel":
        bot.delete_message(chat_id, call.message.message_id)
        bot.send_message(chat_id, "Операция отменена. Возвращаемся в главное меню.")
        start(call.message)
    
    elif call.data == "copy_receipt":
        if chat_id in user_data and 'receipt' in user_data[chat_id]:
            # Отправляем чек отдельным сообщением для удобного копирования
            bot.send_message(chat_id, user_data[chat_id]['receipt'])
            bot.answer_callback_query(call.id, "Чек отправлен отдельным сообщением для копирования")
        else:
            bot.answer_callback_query(call.id, "Чек не найден")
    
    elif call.data == "copy_request":
        if chat_id in user_data and 'request' in user_data[chat_id]:
            # Отправляем запрос отдельным сообщением для удобного копирования
            bot.send_message(chat_id, user_data[chat_id]['request'])
            bot.answer_callback_query(call.id, "Запрос отправлен отдельным сообщением для копирования")
        else:
            bot.answer_callback_query(call.id, "Запрос не найден")
    
    # Убираем уведомление о нажатии кнопки
    else:
        bot.answer_callback_query(call.id)

# Запуск бота с обработкой ошибок
if __name__ == '__main__':
    print("Бот запущен...")
    
    # Бесконечный цикл с обработкой ошибок
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=30)
        except telebot.apihelper.ApiException as e:
            logger.error(f"ApiException: {e}")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            time.sleep(10)

