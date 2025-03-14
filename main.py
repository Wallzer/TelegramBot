import os
import asyncio
import datetime
import requests
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram import Router
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiohttp import web
from datab import init_db, add_user, increment_command_count, get_user_stats, get_all_users
import pyktok as pyk

# Получаем токен из переменных окружения или вставляем напрямую (не рекомендуется)
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))

bot = Bot(token=TOKEN)
router = Router()

# Главное меню с кнопками
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🐱 Кот"), KeyboardButton(text="🐶 Собака")],
        [KeyboardButton(text="📈 Статистика")],
        [KeyboardButton(text="🎥 Скачать TikTok")],
        [KeyboardButton(text="☁️ Погода")],
        [KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True
)

#состояния для работы с командами, требующими ввода от пользователя
class DownloadState(StatesGroup):
    waiting_for_link = State()

class WeatherState(StatesGroup):
    waiting_for_place = State()

# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    await add_user(message.from_user.id)
    await message.answer(
        "Привет! Выбери действие на клавиатуре ниже 👇",
        reply_markup=main_menu
    )

# Обработчик кнопки "❓ Помощь"
@router.message(lambda message: message.text == "❓ Помощь")
async def help_handler(message: types.Message):
    help_text = (
        "Привет! Вот доступные действия:\n"
        "🐱 Кот - получишь случайное фото кота\n"
        "🐶 Собака - получишь случайное фото собаки\n"
        "📈 Статистика - покажу, сколько раз ты использовал бота\n"
        "🎥 Скачать TikTok - скачает видео по ссылке\n"
        "☁️ Погода - узнаешь погоду в городе\n"
    )
    await message.answer(help_text, reply_markup=main_menu)

# Обработчик кнопки "📈 Статистика"
@router.message(lambda message: message.text == "📈 Статистика")
async def stats_handler(message: Message):
    count = await get_user_stats(message.from_user.id)
    await message.answer(f"Ты использовал команды {count} раз!", reply_markup=main_menu)

# Функция для получения изображения кота
async def cat_img(message: types.Message):
    response = requests.get("https://api.thecatapi.com/v1/images/search")
    if response.status_code == 200:
        data = response.json()
        image_url = data[0]['url']
        await message.answer_photo(image_url)
    else:
        await message.answer("Не удалось получить изображение кошки!")

# Обработчик кнопки "🐱 Кот"
@router.message(lambda message: message.text == "🐱 Кот")
async def cat_handler(message: types.Message):
    await message.answer("meow 😺", reply_markup=main_menu)
    await cat_img(message)
    await increment_command_count(message.from_user.id)

# Функция для получения изображения собаки
async def dog_img(message: types.Message):
    response = requests.get("https://api.thedogapi.com/v1/images/search")
    if response.status_code == 200:
        data = response.json()
        image_url = data[0]['url']
        await message.answer_photo(image_url)
    else:
        await message.answer("Не удалось получить изображение собаки!")

# Обработчик кнопки "🐶 Собака"
@router.message(lambda message: message.text == "🐶 Собака")
async def dog_handler(message: types.Message):
    await message.answer("woof-woof 🐶", reply_markup=main_menu)
    await dog_img(message)
    await increment_command_count(message.from_user.id)

# Обработчик кнопки "🎥 Скачать TikTok"
@router.message(lambda message: message.text == "🎥 Скачать TikTok")
async def download_handler(message: Message, state: FSMContext):
    await message.answer("Введи ссылку ниже 📎", reply_markup=main_menu)
    await state.set_state(DownloadState.waiting_for_link)

VIDEO_FOLDER = "."  # Папка для видеофайлов

async def wait_for_video(link):
    # Пример обработки названия файла, возможно потребуется корректировка под твой алгоритм
    link = link.replace("/", "_")
    link = link[24:10]  # Проверь этот кусок логики
    while True:
        for file in os.listdir(VIDEO_FOLDER):
            if file.endswith(".mp4") and file.startswith(link):
                return file
        await asyncio.sleep(1)

@router.message(DownloadState.waiting_for_link)
async def download(message: types.Message, state: FSMContext):
    await increment_command_count(message.from_user.id)
    link = message.text.strip()
    await message.answer("⏳ Жди...", reply_markup=main_menu)
    try:
        pyk.save_tiktok(link, True, "data.csv")
    except Exception:
        await message.answer("❌ Ошибка при скачивании видео.", reply_markup=main_menu)
        await state.clear()
        return
    try:
        video_file = await wait_for_video(link)
        video_path = os.path.join(VIDEO_FOLDER, video_file)
        video = FSInputFile(video_path)
        await message.answer_video(video, caption="🎥 Вот твое видео!", reply_markup=main_menu)
        os.remove(video_path)
    except Exception:
        await message.answer("❌ Ошибка при отправке видео.", reply_markup=main_menu)
    await state.clear()

# Обработчик кнопки "☁️ Погода"
@router.message(lambda message: message.text == "☁️ Погода")
async def weather_handler(message: Message, state: FSMContext):
    await message.answer("Введи название города 🌍", reply_markup=main_menu)
    await state.set_state(WeatherState.waiting_for_place)

# Словарь с эмодзи для погоды
WEATHER_EMOJIS = {
    "ясно": "☀️",
    "облачно": "☁️",
    "переменная облачность": "⛅",
    "дождь": "🌧️",
    "снег": "❄️",
    "гроза": "⛈️",
    "туман": "🌫️",
    "морось": "🌦️",
    "пасмурно": "☁️",
    "снегопад": "🌨️",
}

@router.message(WeatherState.waiting_for_place)
async def get_weather(message: Message, state: FSMContext):
    API_KEY = os.getenv("WEATHER_API_KEY", "YOUR_OPENWEATHER_API_KEY")
    CITY = message.text.strip()
    url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric&lang=ru"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                temperature = data['main']['temp']
                description = data['weather'][0]['description'].capitalize()
                emoji = WEATHER_EMOJIS.get(description.lower(), "🌍")
                await message.answer(f"{temperature}°C {description}{emoji}", reply_markup=main_menu)
            else:
                await message.answer("Ошибка получения данных о погоде. Проверь название города.", reply_markup=main_menu)
    await state.clear()

# Обработчик команды для рассылки от админа
@router.message(Command("adminspam"))
async def admin_spam(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет доступа к этой команде!")
        return

    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        await message.answer("Использование: /adminspam текст для рассылки")
        return
    broadcast_text = parts[1]
    users = await get_all_users()
    sent_count = 0
    for user_id in users:
        try:
            await bot.send_message(user_id, broadcast_text)
            sent_count += 1
        except Exception as e:
            print(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
    await message.answer(f"Сообщение отправлено {sent_count} пользователям!")


async def handle(request):
    return web.Response(text="Привет, мир!")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Web-сервер запущен на порту {port}")

# Основная функция запуска бота
async def main():
    await init_db()
    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    # Запускаем веб-сервер (важно для Replit)
    asyncio.create_task(start_webserver())

    # Запускаем polling бота
    await dispatcher.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
