# telegram_bot.py
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import logging
from forex_analyzer import ForexAnalyzer
from datetime import datetime
import time
import os


# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
API_TOKEN = '7599416122:AAGDRHl1FKVyGm9jNuYXO2Kg42g3MR_xCQc'  # ⚠️ ЗАМЕНИТЕ НА ВАШ ТОКЕН ⚠️

bot = telebot.TeleBot(API_TOKEN)

# Инициализация анализатора
analyzer = ForexAnalyzer()

# Создаем клавиатуру
def create_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    buttons = [
        KeyboardButton('📊 GBP/USD'),
        KeyboardButton('📈 EUR/USD'),
        KeyboardButton('💴 USD/JPY'),
        KeyboardButton('🦘 AUD/USD'),
        KeyboardButton('🏔️ USD/CHF'),
        KeyboardButton('🍁 USD/CAD'),
        KeyboardButton('🥝 NZD/USD'),
        KeyboardButton('🇪🇺 EUR/GBP'),
        KeyboardButton('🔄 Все пары'),
        KeyboardButton('❓ Помощь')
    ]
    
    keyboard.add(*buttons)
    return keyboard

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = """
🤖 *Forex Analyzer Pro Bot*

*Добро пожаловать!* Я помогу вам с анализом валютных пар.

*Основные команды:*
/start - Начало работы  
/gbpusd - Анализ GBP/USD
/eurusd - Анализ EUR/USD
/all - Все основные пары
/help - Помощь

*Или просто используйте кнопки ниже!*

*Что я умею:*
• Анализировать тренды
• Рассчитывать волатильность (ATR)
• Давать торговые рекомендации
• Обновлять данные в реальном времени

*Поддерживаемые пары:* GBP/USD, EUR/USD, USD/JPY, AUD/USD, USD/CAD, USD/CHF, NZD/USD, EUR/GBP
    """
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode='Markdown',
        reply_markup=create_main_keyboard()
    )

@bot.message_handler(commands=['gbpusd', 'eurusd', 'usdjpy', 'audusd', 'usdcad', 'usdchf', 'nzdusd', 'eurgbp'])
def handle_pair_command(message):
    command = message.text.replace('/', '').upper()
    pair_map = {
        'GBPUSD': 'GBPUSD',
        'EURUSD': 'EURUSD', 
        'USDJPY': 'USDJPY',
        'AUDUSD': 'AUDUSD',
        'USDCAD': 'USDCAD',
        'USDCHF': 'USDCHF',
        'NZDUSD': 'NZDUSD',
        'EURGBP': 'EURGBP'
    }
    
    pair_name = pair_map.get(command)
    if pair_name:
        send_analysis(message.chat.id, pair_name)
    else:
        bot.send_message(message.chat.id, "❌ Неизвестная команда")

@bot.message_handler(commands=['all'])
def handle_all_pairs(message):
    chat_id = message.chat.id
    pairs = analyzer.get_supported_pairs()
    
    bot.send_message(chat_id, "🔄 Анализирую все основные пары...")
    
    for pair in pairs[:4]:  # Ограничим 4 парами чтобы не перегружать
        try:
            send_analysis(chat_id, pair, silent=True)
            time.sleep(2)  # Увеличим паузу между запросами
        except Exception as e:
            logger.error(f"Ошибка анализа {pair}: {e}")
            bot.send_message(chat_id, f"❌ Ошибка анализа {pair}")
            continue

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    text = message.text
    chat_id = message.chat.id
    
    # Обработка кнопок
    pair_map = {
        '📊 GBP/USD': 'GBPUSD',
        '📈 EUR/USD': 'EURUSD',
        '💴 USD/JPY': 'USDJPY', 
        '🦘 AUD/USD': 'AUDUSD',
        '🏔️ USD/CHF': 'USDCHF',
        '🍁 USD/CAD': 'USDCAD',
        '🥝 NZD/USD': 'NZDUSD',
        '🇪🇺 EUR/GBP': 'EURGBP'
    }
    
    if text in pair_map:
        send_analysis(chat_id, pair_map[text])
    
    elif text == '🔄 Все пары':
        handle_all_pairs(message)
        
    elif text == '❓ Помощь':
        send_welcome(message)
        
    else:
        # Попробуем распознать текстовый ввод пары
        pair_name = text.upper().replace('/', '').replace(' ', '')
        if pair_name in analyzer.get_supported_pairs():
            send_analysis(chat_id, pair_name)
        else:
            bot.send_message(
                chat_id,
                "❌ Не понимаю запрос. Используйте кнопки или команды из /help",
                reply_markup=create_main_keyboard()
            )

def send_analysis(chat_id, pair_name, silent=False):
    """Отправка анализа конкретной пары + график"""
    if not silent:
        bot.send_chat_action(chat_id, 'typing')

    try:
        logger.info(f"Запрос анализа для {pair_name}")
        results = analyzer.analyze_pair(pair_name)

        if results is None or not isinstance(results, dict):
            bot.send_message(chat_id, f"❌ Не удалось получить данные для {pair_name}")
            return

        message = format_analysis_message(results)
        chart_path = results.get("chart")

        # 📊 ЕСЛИ ЕСТЬ ГРАФИК — ОТПРАВЛЯЕМ ФОТО
        if chart_path and os.path.exists(chart_path):
            with open(chart_path, "rb") as photo:
                bot.send_photo(
                    chat_id,
                    photo,
                    caption=message,
                    parse_mode='HTML',
                    reply_markup=create_main_keyboard() if not silent else None
                )

            # 🧹 удаляем файл после отправки
            os.remove(chart_path)

        # 📝 ИНАЧЕ — ТОЛЬКО ТЕКСТ
        else:
            bot.send_message(
                chat_id,
                message,
                parse_mode='HTML',
                reply_markup=create_main_keyboard() if not silent else None
            )

        logger.info(f"Анализ отправлен для {pair_name}")

    except Exception as e:
        logger.error(f"Ошибка отправки анализа: {e}")
        bot.send_message(
            chat_id,
            f"❌ Произошла ошибка при анализе {pair_name}. Попробуйте позже.",
            reply_markup=create_main_keyboard()
        )

def format_analysis_message(results):
    """Форматирование сообщения с анализом"""
    try:
        pair = results.get('pair', 'N/A')
        price = results.get('current_price', 0)
        atr = results.get('daily_atr', 0)
        trend = results.get('trend', 'N/A')
        volatility = results.get('volatility', 'N/A')
        recommendation = results.get('recommendation', 'N/A')
        timestamp = results.get('timestamp', 'N/A')
        is_demo = results.get('is_demo', False)
        
        # Эмодзи для тренда
        trend_emoji = "📈" if "восходящий" in str(trend).lower() else "📉" if "нисходящий" in str(trend).lower() else "➡️"
        
        demo_notice = "🟡 <b>ДЕМО-ДАННЫЕ</b>\n" if is_demo else ""
        
        message = f"""
{demo_notice}<b>{trend_emoji} {pair} Анализ</b>

💰 <b>Текущая цена:</b> <code>{float(price):.5f}</code>
📊 <b>Дневной ATR:</b> <code>{float(atr)}</code> пипсов
🎯 <b>Тренд:</b> {trend}
🌪️ <b>Волатильность:</b> {volatility}

💡 <b>Рекомендации:</b>
{recommendation}

⏰ <i>Обновлено: {timestamp}</i>

<code>-------------------------</code>
⚠️ <i>Не является инвестиционной рекомендацией</i>
        """
        
        return message
        
    except Exception as e:
        logger.error(f"Ошибка форматирования сообщения: {e}")
        return f"❌ Ошибка формирования отчета для {results.get('pair', 'unknown')}"

if __name__ == '__main__':
    print("🤖 Forex Analyzer Bot запущен...")
    print("⏰ Бот готов к работе!")
    print("📍 Используйте /start для начала")
    print("🔧 Проверяем подключение...")
    
    try:
        # Тестируем анализ одной пары при запуске
        test_result = analyzer.analyze_pair('GBPUSD')
        if test_result and isinstance(test_result, dict):
            print("✅ Анализатор работает корректно")
            print(f"   Тестовый результат: {test_result.get('pair')} - {test_result.get('current_price')}")
        else:
            print("⚠️ Анализатор использует демо-данные")
            
        bot.polling(none_stop=True, interval=0)
    except Exception as e:
        logger.error(f"Ошибка бота: {e}")
        print(f"❌ Критическая ошибка: {e}")
        time.sleep(15)