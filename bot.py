from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
import aiohttp
import os
import logging
import aiosqlite
from dotenv import load_dotenv
import nest_asyncio
import requests
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()
GREETING_MESSAGE = 'Привет! Введите название заведения или категорию.'
FOUND_PLACES_MESSAGE = 'Найдено {count} мест.'
NOT_FOUND_MESSAGE = 'Ничего не найдено.'

# Создание или подключение к базе данных
async def create_db():
    async with aiosqlite.connect('places.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS places (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                address TEXT,
                details TEXT
            )
        ''')
        await db.commit()

# Сохранение мест в базу данных
def save_places(places):
    conn = sqlite3.connect('places.db')
    cursor = conn.cursor()
    for place in places:
        name = place['properties']['name']
        address = place['properties'].get('address', 'Нет адреса')
        details = str(place['properties'])  # Сохраняем подробности о месте
        cursor.execute('INSERT OR REPLACE INTO places (name, address, details) VALUES (?, ?, ?)', (name, address, details))
    conn.commit()
    conn.close()

# Функция обновления базы данных раз в неделю
async def update_places():
    api_key = os.getenv('YANDEX_API_KEY')
    url = 'https://search-maps.yandex.ru/v1/?text=заведение&type=biz&lang=ru_RU&apikey={}'.format(api_key)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                places = await response.json()
                places = places.get('features', [])
        save_places(places)
        logging.info(f'Updated database with {len(places)} places.')
    except requests.RequestException as e:
        logging.error(f"An error occurred while updating places: {e}")

async def start(update: Update, context: CallbackContext) -> None:
    await context.bot.send_message(chat_id=update.effective_chat.id, text=GREETING_MESSAGE)

async def handle_message(update: Update, context: CallbackContext) -> None:
    query = update.message.text
    async with aiosqlite.connect('places.db') as conn:
        async with conn.execute('SELECT * FROM places WHERE name LIKE ? OR address LIKE ?', (f'%{query}%', f'%{query}%')) as cursor:
            places = await cursor.fetchall()

    if places:
        await update.message.reply_text(FOUND_PLACES_MESSAGE.format(count=len(places)))
    else:
        await update.message.reply_text(NOT_FOUND_MESSAGE)
async def setup_database():
    await create_db()  # Создание базы данных

async def setup_scheduler():
    # Запланированное обновление раз в неделю
    scheduler = AsyncIOScheduler()
    scheduler.add_job(update_places, 'interval', weeks=1)
    scheduler.start()

async def setup_application() -> Application:
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")
    application = Application.builder().token(token).build()
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return application

async def main():
    await setup_database()
    await setup_scheduler()
    application = await setup_application()
    await application.run_polling()
    await application.run_polling()

if __name__ == '__main__':
    nest_asyncio.apply()
    asyncio.run(main())