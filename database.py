#!/usr/bin/env python3
"""
Модуль для работы с базой данных PostgreSQL.
"""

import asyncpg
import logging
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с PostgreSQL базой данных."""

    def __init__(self, dsn: str):
        """
        Инициализация подключения к базе данных.

        Args:
            dsn: Database connection string (e.g., 'postgresql://user:pass@host:port/dbname')
        """
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Создает пул подключений к базе данных."""
        try:
            self.pool = await asyncpg.create_pool(
                self.dsn,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info("Успешно подключено к базе данных")
        except Exception as e:
            logger.error(f"Ошибка подключения к базе данных: {e}")
            raise

    async def close(self):
        """Закрывает пул подключений."""
        if self.pool:
            await self.pool.close()
            logger.info("Подключение к базе данных закрыто")

    async def get_topics(self) -> Dict[str, int]:
        """
        Получает маппинг префиксов к topic_id.

        Returns:
            Словарь {prefix: topic_id}
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT prefix, topic_id FROM topics ORDER BY prefix ASC")
            return {row['prefix'].lower(): row['topic_id'] for row in rows}

    async def get_topic_names(self) -> Dict[str, str]:
        """
        Получает маппинг префиксов к названиям чатов.

        Returns:
            Словарь {prefix: name}
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT prefix, name FROM topics")
            return {row['prefix'].lower(): row['name'] for row in rows}

    async def get_source_chats(self) -> Set[str]:
        """
        Получает список активных исходных чатов.

        Returns:
            Множество chat_id активных чатов
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT chat_id FROM source_chats WHERE is_active = TRUE"
            )
            return {row['chat_id'] for row in rows}

    async def get_config(self, key: str) -> Optional[str]:
        """
        Получает значение конфигурации по ключу.

        Args:
            key: Ключ конфигурации

        Returns:
            Значение конфигурации или None
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT value FROM bot_config WHERE key = $1", key
            )
            return row['value'] if row else None

    async def get_all_config(self) -> Dict[str, str]:
        """
        Получает всю конфигурацию бота.

        Returns:
            Словарь {key: value}
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT key, value FROM bot_config")
            return {row['key']: row['value'] for row in rows}

    async def add_topic(self, prefix: str, name: str, topic_id: int) -> bool:
        """
        Добавляет новый топик.

        Args:
            prefix: Префикс команды
            name: Название чата/темы
            topic_id: ID темы в Telegram

        Returns:
            True если успешно, False если префикс уже существует
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO topics (prefix, name, topic_id)
                    VALUES ($1, $2, $3)
                    """,
                    prefix, name, topic_id
                )
                logger.info(f"Добавлен топик: {prefix} -> {name} (topic_id: {topic_id})")
                return True
        except asyncpg.UniqueViolationError:
            logger.warning(f"Топик с префиксом '{prefix}' уже существует")
            return False

    async def update_topic(self, prefix: str, name: Optional[str] = None,
                          topic_id: Optional[int] = None) -> bool:
        """
        Обновляет существующий топик.

        Args:
            prefix: Префикс команды
            name: Новое название (опционально)
            topic_id: Новый ID темы (опционально)

        Returns:
            True если успешно обновлено
        """
        updates = []
        params = []
        param_count = 1

        if name is not None:
            updates.append(f"name = ${param_count}")
            params.append(name)
            param_count += 1

        if topic_id is not None:
            updates.append(f"topic_id = ${param_count}")
            params.append(topic_id)
            param_count += 1

        if not updates:
            return False

        updates.append(f"updated_at = CURRENT_TIMESTAMP")
        params.append(prefix)

        query = f"UPDATE topics SET {', '.join(updates)} WHERE prefix = ${param_count}"

        async with self.pool.acquire() as conn:
            result = await conn.execute(query, *params)
            updated = result.split()[-1] == '1'
            if updated:
                logger.info(f"Обновлен топик: {prefix}")
            return updated

    async def delete_topic(self, prefix: str) -> bool:
        """
        Удаляет топик.

        Args:
            prefix: Префикс команды

        Returns:
            True если успешно удалено
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM topics WHERE prefix = $1", prefix
            )
            deleted = result.split()[-1] == '1'
            if deleted:
                logger.info(f"Удален топик: {prefix}")
            return deleted

    async def add_source_chat(self, chat_id: str, name: Optional[str] = None) -> bool:
        """
        Добавляет исходный чат.

        Args:
            chat_id: ID чата в Telegram
            name: Название чата (опционально)

        Returns:
            True если успешно
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO source_chats (chat_id, name)
                    VALUES ($1, $2)
                    """,
                    chat_id, name
                )
                logger.info(f"Добавлен исходный чат: {chat_id} ({name})")
                return True
        except asyncpg.UniqueViolationError:
            logger.warning(f"Чат с ID '{chat_id}' уже существует")
            return False

    async def toggle_source_chat(self, chat_id: str, is_active: bool) -> bool:
        """
        Активирует или деактивирует исходный чат.

        Args:
            chat_id: ID чата
            is_active: Активен или нет

        Returns:
            True если успешно обновлено
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE source_chats
                SET is_active = $1, updated_at = CURRENT_TIMESTAMP
                WHERE chat_id = $2
                """,
                is_active, chat_id
            )
            updated = result.split()[-1] == '1'
            if updated:
                status = "активирован" if is_active else "деактивирован"
                logger.info(f"Чат {chat_id} {status}")
            return updated

    async def set_config(self, key: str, value: str, description: Optional[str] = None) -> None:
        """
        Устанавливает значение конфигурации.

        Args:
            key: Ключ конфигурации
            value: Значение
            description: Описание (опционально)
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO bot_config (key, value, description)
                VALUES ($1, $2, $3)
                ON CONFLICT (key)
                DO UPDATE SET value = $2, description = COALESCE($3, bot_config.description),
                              updated_at = CURRENT_TIMESTAMP
                """,
                key, value, description
            )
            logger.info(f"Установлена конфигурация: {key} = {value}")
