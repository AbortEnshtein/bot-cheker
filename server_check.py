import telebot
from telebot import apihelper
import requests
import threading
import time
from datetime import datetime

# ================= НАСТРОЙКИ (ЗАМЕНИТЕ ЭТИ ДАННЫЕ) =================
# 1. Токен вашего бота от @BotFather
BOT_TOKEN = '7173016637:AAELUMRIH8xAseFbmeXGgW5sDBxett9JFXQ'
# 2. Ваш личный Telegram ID, который вы только что узнали у @userinfobot
ADMIN_ID = 1697336986  # <-- ВСТАВЬТЕ СВОЙ ID СЮДА
# 3. Адреса ваших серверов
BACKEND_URL = "http://5.188.24.149:3000/"
FRONTEND_URL = "http://5.188.24.149:8000/"
# 4. Как часто проверять сервер (в секундах)
CHECK_INTERVAL = 300
# ================================================================

# ================= НАСТРОЙКИ ПРОКСИ ДЛЯ UBUNTU =================
# Раскомментируйте нужную строку ниже:

# Вариант 1: Если у вас уже настроен и запущен Tor (например, через torsocks)
apihelper.proxy = {'https': 'socks5h://5.188.24.149:9050'}

# Вариант 2: Если вы используете публичный прокси или свой
# apihelper.proxy = {'https': 'socks5://user:password@ваш_прокси_хост:ваш_прокси_порт'}

# Вариант 3: Если прокси не нужен (просто оставить как есть)
# apihelper.proxy = {}
# ================================================================

# Увеличиваем таймауты на всякий случай (для Tor это критически важно)
apihelper.CONNECT_TIMEOUT = 60
apihelper.READ_TIMEOUT = 60

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

# Словарь для хранения статусов серверов (чтобы не спамить каждую проверку)
server_status = {
    'backend': {'last_status': True, 'last_failure_notified': False},
    'frontend': {'last_status': True, 'last_failure_notified': False}
}

# Функция проверки доступности сервера
def check_server(url, server_name):
    try:
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now()}] Ошибка проверки {server_name}: {e}")
        return False

# Функция отправки уведомления админу
def send_alert(server_name, url, is_down):
    if is_down:
        text = f"🚨 **СЕРВЕР ОТКЛЮЧЕН!**\n\n📡 Сервер: {server_name}\n🔗 Ссылка: {url}\n⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    else:
        text = f"✅ **СЕРВЕР ВОССТАНОВЛЕН!**\n\n📡 Сервер: {server_name}\n🔗 Ссылка: {url}\n⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    try:
        bot.send_message(ADMIN_ID, text, parse_mode='Markdown')
    except Exception as e:
        print(f"Ошибка отправки сообщения админу: {e}")

# Основной цикл мониторинга
def monitoring_loop():
    while True:
        # Проверка бэкенда
        backend_is_up = check_server(BACKEND_URL, "Backend")
        if backend_is_up != server_status['backend']['last_status']:
            if not backend_is_up:
                send_alert("Backend", BACKEND_URL, True)
                server_status['backend']['last_failure_notified'] = True
            elif server_status['backend']['last_failure_notified']:
                send_alert("Backend", BACKEND_URL, False)
                server_status['backend']['last_failure_notified'] = False
            server_status['backend']['last_status'] = backend_is_up
        elif not backend_is_up and not server_status['backend']['last_failure_notified']:
            send_alert("Backend", BACKEND_URL, True)
            server_status['backend']['last_failure_notified'] = True

        # Проверка фронтенда (аналогично)
        frontend_is_up = check_server(FRONTEND_URL, "Frontend")
        if frontend_is_up != server_status['frontend']['last_status']:
            if not frontend_is_up:
                send_alert("Frontend", FRONTEND_URL, True)
                server_status['frontend']['last_failure_notified'] = True
            elif server_status['frontend']['last_failure_notified']:
                send_alert("Frontend", FRONTEND_URL, False)
                server_status['frontend']['last_failure_notified'] = False
            server_status['frontend']['last_status'] = frontend_is_up
        elif not frontend_is_up and not server_status['frontend']['last_failure_notified']:
            send_alert("Frontend", FRONTEND_URL, True)
            server_status['frontend']['last_failure_notified'] = True

        time.sleep(CHECK_INTERVAL)

# --- Команды бота (вам не нужно их менять) ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🤖 Привет! Я бот для мониторинга сервера.\n\nДоступные команды:\n/id - показать мой Telegram ID\n/status - проверить статус серверов сейчас")

@bot.message_handler(commands=['id'])
def send_id(message):
    user_id = message.from_user.id
    bot.reply_to(message, f"🆔 Ваш Telegram ID: `{user_id}`", parse_mode='Markdown')

@bot.message_handler(commands=['status'])
def check_status_now(message):
    bot.reply_to(message, "🔄 Проверяю статус серверов...")
    backend_status = check_server(BACKEND_URL, "Backend")
    frontend_status = check_server(FRONTEND_URL, "Frontend")
    response = f"📊 **Статус серверов:**\n\nBackend: {'✅ Доступен' if backend_status else '❌ Недоступен'}\nFrontend: {'✅ Доступен' if frontend_status else '❌ Недоступен'}"
    bot.reply_to(message, response, parse_mode='Markdown')

# --- Запуск бота ---
def start_bot():
    monitor_thread = threading.Thread(target=monitoring_loop, daemon=True)
    monitor_thread.start()
    print("🤖 Бот запущен и начал мониторинг...")
    print(f"👤 Уведомления будут отправляться админу с ID: {ADMIN_ID}")
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен.")

if __name__ == "__main__":
    start_bot()