#!/usr/bin/env python3
"""
Telegram бот для перенаправления сообщений между чатами.
Перехватывает сообщения, начинающиеся с "/" и отправляет их в разные темы чата.
"""

import os
import logging
import re
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
)
from database import Database
import admin
from admin import init_admin, get_admin_conversation_handler
from migrate import run_migrations

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
ADMIN_IDS_STR = os.getenv('ADMIN_IDS', '')

# Парсинг ID администраторов
ADMIN_IDS = set()
if ADMIN_IDS_STR:
    for admin_id in ADMIN_IDS_STR.split(','):
        admin_id = admin_id.strip()
        if admin_id.isdigit():
            ADMIN_IDS.add(int(admin_id))

# Глобальный объект базы данных
db: Database = None

# Кэш данных из БД (обновляется при старте и по необходимости)
TOPIC_ROUTING = {}
TOPIC_NAMES = {}
SOURCE_CHATS = set()
TARGET_CHAT_ID = None
INCLUDE_SENDER_INFO = True
SENDER_FORMAT = "{message}\nОтправил: {sender_name} ({sender_username})"
DEFAULT_TOPIC_ID = None


async def load_data_from_db():
    """Загружает данные из базы данных в кэш."""
    global TOPIC_ROUTING, TOPIC_NAMES, SOURCE_CHATS, TARGET_CHAT_ID
    global INCLUDE_SENDER_INFO, SENDER_FORMAT, db

    if db is None:
        logger.error("База данных не инициализирована!")
        return

    logger.info("Загрузка данных из базы данных...")

    # Загрузка топиков
    TOPIC_ROUTING = await db.get_topics()
    TOPIC_NAMES = await db.get_topic_names()

    # Загрузка исходных чатов
    SOURCE_CHATS = await db.get_source_chats()

    # Загрузка конфигурации
    config = await db.get_all_config()
    TARGET_CHAT_ID = config.get('target_chat_id')
    INCLUDE_SENDER_INFO = config.get('include_sender_info', 'true').lower() == 'true'
    SENDER_FORMAT = config.get('sender_format', SENDER_FORMAT)

    logger.info(f"Загружено топиков: {len(TOPIC_ROUTING)}")
    logger.info(f"Загружено исходных чатов: {len(SOURCE_CHATS)}")
    logger.info(f"Целевой чат: {TARGET_CHAT_ID}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает входящие сообщения и перенаправляет их при необходимости.
    """
    # Логируем update если включен дебаг-режим
    admin.log_update_to_file(update)

    message = update.message

    if not message or not message.text:
        return

    # Проверяем, что сообщение из одного из исходных чатов
    if str(message.chat_id) not in SOURCE_CHATS:
        return

    # Проверяем, что сообщение начинается с "/"
    if not message.text.startswith('/'):
        return

    try:
        # Парсим сообщение: /prefix остальное сообщение
        # Пример: "/sky 27.5" -> prefix="sky", content="27.5"
        match = re.match(r'^/(\w+)\s*(.*)$', message.text)

        if not match:
            logger.warning(f"Не удалось распарсить сообщение: {message.text}")
            return

        prefix = match.group(1).lower()
        content = match.group(2).strip()

        # Проверяем, известен ли префикс
        if prefix not in TOPIC_ROUTING:
            # Формируем список доступных префиксов с названиями (если есть)
            if TOPIC_NAMES:
                # Показываем маппинг: цифра → название
                available_list = []
                for p in sorted(TOPIC_ROUTING.keys()):
                    name = TOPIC_NAMES.get(p, p)
                    available_list.append(f"/{p} → {name}")
                response_text = "Такой темы нет, список доступных:\n" + "\n".join(available_list)
            else:
                # Простой список префиксов
                available_prefixes = ', '.join([f'/{p}' for p in sorted(TOPIC_ROUTING.keys())])
                response_text = f"Такой темы нет, список доступных: {available_prefixes}"

            # Отправляем ответ в исходный чат
            await context.bot.send_message(
                chat_id=message.chat_id,
                text=response_text,
                reply_to_message_id=message.message_id
            )

            logger.info(f"Получен неизвестный префикс '{prefix}', отправлен список доступных")
            return

        # Определяем тему для отправки
        topic_id = TOPIC_ROUTING.get(prefix, DEFAULT_TOPIC_ID)

        # Получаем информацию об отправителе
        sender_name = "Неизвестный"
        sender_username = None
        sender_id = None

        if message.from_user:
            sender_name = message.from_user.full_name or "Неизвестный"
            sender_username = f"@{message.from_user.username}" if message.from_user.username else None
            sender_id = message.from_user.id

        # Формируем текст для отправки
        if INCLUDE_SENDER_INFO:
            forwarded_text = SENDER_FORMAT.format(
                sender_name=sender_name,
                sender_username=sender_username or "нет username",
                sender_id=sender_id or "неизвестен",
                message=content
            )
        else:
            forwarded_text = content

        # Отправляем сообщение в целевой чат с указанием темы
        kwargs = {
            'chat_id': TARGET_CHAT_ID,
            'text': forwarded_text
        }

        if topic_id is not None:
            kwargs['message_thread_id'] = topic_id

        await context.bot.send_message(**kwargs)

        topic_info = f"тему {topic_id}" if topic_id else "основной чат"
        logger.info(
            f"Перенаправлено сообщение с префиксом '{prefix}' в {topic_info}: "
            f"{content[:50]}... (от {sender_name})"
        )

    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}", exc_info=True)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает ошибки.
    """
    logger.error(f"Произошла ошибка: {context.error}")


async def post_init(application: Application) -> None:
    """Инициализация после создания приложения."""
    global db

    # Запуск миграций
    logger.info("Запуск миграций базы данных...")
    try:
        run_migrations()
    except Exception as e:
        logger.error(f"Ошибка при выполнении миграций: {e}", exc_info=True)
        raise

    # Подключение к базе данных
    db = Database(DATABASE_URL)
    await db.connect()

    # Инициализация админ-панели
    init_admin(db, ADMIN_IDS)

    # Загрузка данных из БД
    await load_data_from_db()


async def post_shutdown(application: Application) -> None:
    """Очистка ресурсов при завершении."""
    if db:
        await db.close()


def main() -> None:
    """
    Запускает бота.
    """
    # Проверка наличия необходимых переменных окружения
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не установлен в .env файле")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL не установлен в .env файле")

    logger.info("Запуск бота...")

    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрация функций инициализации и завершения
    application.post_init = post_init
    application.post_shutdown = post_shutdown

    # Регистрация админ-обработчиков
    application.add_handler(get_admin_conversation_handler())

    # Регистрация обработчиков
    # Фильтр для текстовых сообщений из групп и приватных чатов
#

    # Также обрабатываем команды отдельно
    application.add_handler(
        MessageHandler(
            filters.COMMAND,
            handle_message
        )
    )

    # Регистрация обработчика ошибок
    application.add_error_handler(error_handler)

    # Запуск бота
    logger.info("Бот запущен и ожидает сообщения...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
