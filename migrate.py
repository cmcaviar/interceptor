#!/usr/bin/env python3
"""
Модуль для управления миграциями базы данных с использованием yoyo.
"""

import os
import logging
from yoyo import read_migrations, get_backend
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')


def run_migrations():
    """Запускает все непримененные миграции."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL не установлен в .env файле")

    logger.info(f"Подключение к базе данных для миграций...")

    # Получаем backend для подключения к БД
    backend = get_backend(DATABASE_URL)

    # Читаем миграции из папки migrations
    migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
    migrations = read_migrations(migrations_dir)

    # Применяем миграции
    with backend.lock():
        to_apply = backend.to_apply(migrations)
        to_apply_list = list(to_apply)

        if to_apply_list:
            logger.info(f"Применение {len(to_apply_list)} миграции(й)...")
            backend.apply_migrations(to_apply_list)
            logger.info("✅ Все миграции успешно применены")
        else:
            logger.info("Миграций для применения не найдено")


if __name__ == '__main__':
    # Настройка логирования
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    run_migrations()
