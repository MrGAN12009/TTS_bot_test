from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, FSInputFile
import requests
import os
import time
import asyncio
from moviepy.audio.io.AudioFileClip import AudioFileClip

# Инициализация бота
BOT_TOKEN = "5480073812:AAFAJeBEU8VEyrBqRLRznD_dzhDxI82-ju0"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

# Константы для API
TTS_API_URL = ""
AUTH_TOKEN = ""

# Функция для отправки текста в TTS API и получения аудиофайла в MP3 формате
def generate_tts_audio(text, voice="echo"):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {AUTH_TOKEN}'
    }

    input_data = {
        "input": text,
        "voice": voice
    }

    response = requests.post(TTS_API_URL, json=input_data, headers=headers)

    if response.status_code == 200:
        task_info = response.json()
        task_id = task_info.get("request_id")
        if not task_id:
            raise ValueError("Не удалось получить task_id")
        print(f"Задача отправлена, task_id: {task_id}")

        status_url = f"https://api.gen-api.ru/api/v1/request/get/{task_id}"
        while True:
            status_response = requests.get(status_url, headers=headers)
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data.get("status")
                if status == "success":
                    return status_data.get("result")
                elif status == "failed":
                    raise ValueError(f"Ошибка выполнения задачи: {status_data.get('error_message')}")
                else:
                    print("Задача в процессе выполнения, ожидаем...")
            else:
                raise ValueError(f"Ошибка при проверке статуса: {status_response.status_code}")
            time.sleep(5)
    else:
        raise ValueError(f"Ошибка API: {response.status_code}, {response.text}")

# Функция для конвертации MP3 в OGG с помощью moviepy
def convert_mp3_to_ogg(input_path, output_path):
    with AudioFileClip(input_path) as audio:
        audio.write_audiofile(output_path, codec="libvorbis")

# Обработчик команды /start
@router.message(F.text == "/start")
async def start_command(message: Message):
    await message.answer("Привет! Отправь мне текст, и я превращу его в голосовое сообщение.")

# Обработчик текстовых сообщений
@router.message(F.text)
async def send_voice_message(message: Message):
    try:
        # Генерация аудио через API
        audio_url = generate_tts_audio(message.text)

        # Проверяем, что аудио URL — это строка
        if isinstance(audio_url, list):
            audio_url = audio_url[0]

        # Скачивание аудиофайла
        mp3_path = "audio_output/output_audio.mp3"
        ogg_path = "audio_output/output_voice.ogg"
        os.makedirs("audio_output", exist_ok=True)
        response = requests.get(audio_url)
        if response.status_code == 200:
            with open(mp3_path, "wb") as f:
                f.write(response.content)

            # Конвертация MP3 в OGG
            convert_mp3_to_ogg(mp3_path, ogg_path)

            # Отправка голосового сообщения в Telegram
            voice = FSInputFile(ogg_path)
            await message.answer_voice(voice)

            # Удаление временных файлов
            os.remove(mp3_path)
            os.remove(ogg_path)
        else:
            raise ValueError(f"Ошибка загрузки аудиофайла: {response.status_code}")
    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}")

# Основная функция для запуска бота
async def main():
    dp.include_router(router)  # Подключаем маршрутизатор к диспетчеру
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
