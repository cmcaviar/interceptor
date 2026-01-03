#!/usr/bin/env python3
"""
Вспомогательный скрипт для получения ID темы (message_thread_id).
Запустите этот скрипт и ответьте на сообщение в нужной теме,
чтобы узнать её ID.
"""

import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')


async def print_topic_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выводит информацию о теме."""
    message = update.message
    if message:
        chat = message.chat
        user = message.from_user
        topic_id = message.message_thread_id

        logger.info("=" * 50)
        logger.info(f"Chat ID: {chat.id}")
        logger.info(f"Chat Type: {chat.type}")
        logger.info(f"Chat Title: {chat.title if chat.title else 'N/A'}")
        logger.info(f"Topic/Thread ID: {topic_id if topic_id else 'N/A (основной чат)'}")
        logger.info(f"User ID: {user.id if user else 'N/A'}")
        logger.info(f"User Name: {user.full_name if user else 'N/A'}")
        logger.info(f"Message: {message.text}")
        logger.info("=" * 50)

        response_text = (
            f"Chat ID: `{chat.id}`\n"
            f"Chat Type: {chat.type}\n"
        )

        if topic_id:
            response_text += f"Topic ID: `{topic_id}`\n"
        else:
            response_text += "Topic ID: N/A (это основной чат или группа без тем)\n"

        response_text += f"Your ID: `{user.id if user else 'N/A'}`"

        await message.reply_text(response_text, parse_mode='Markdown')


def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не установлен в .env файле")

    logger.info("Бот запущен. Отправьте сообщение в нужную тему для получения её ID")

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL, print_topic_info))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
