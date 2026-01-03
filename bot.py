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
from config import INCLUDE_SENDER_INFO, SENDER_FORMAT, DEFAULT_TOPIC_ID

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
SOURCE_CHAT_ID = os.getenv('SOURCE_CHAT_ID')
TARGET_CHAT_ID = os.getenv('TARGET_CHAT_ID')
TOPIC_ROUTING_STR = os.getenv('TOPIC_ROUTING', '')

# Парсинг маршрутизации префиксов к темам
TOPIC_ROUTING = {}
if TOPIC_ROUTING_STR:
    for route in TOPIC_ROUTING_STR.split(','):
        route = route.strip()
        if ':' in route:
            prefix, topic_id = route.split(':', 1)
            TOPIC_ROUTING[prefix.lower()] = int(topic_id)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает входящие сообщения и перенаправляет их при необходимости.
    """
    message = update.message

    if not message or not message.text:
        return

    # Проверяем, что сообщение из исходного чата
    if str(message.chat_id) != SOURCE_CHAT_ID:
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
            # Формируем список доступных префиксов
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


def main() -> None:
    """
    Запускает бота.
    """
    # Проверка наличия необходимых переменных окружения
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не установлен в .env файле")
    if not SOURCE_CHAT_ID:
        raise ValueError("SOURCE_CHAT_ID не установлен в .env файле")
    if not TARGET_CHAT_ID:
        raise ValueError("TARGET_CHAT_ID не установлен в .env файле")

    logger.info("Запуск бота...")
    logger.info(f"Исходный чат ID: {SOURCE_CHAT_ID}")
    logger.info(f"Целевой чат ID: {TARGET_CHAT_ID}")
    logger.info(f"Маршрутизация префиксов к темам: {TOPIC_ROUTING}")
    logger.info(f"Тема по умолчанию: {DEFAULT_TOPIC_ID}")

    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрация обработчиков
    # Фильтр для текстовых сообщений из групп и приватных чатов
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,  # Все текстовые сообщения (включая те, что начинаются с "/")
            handle_message
        )
    )

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
