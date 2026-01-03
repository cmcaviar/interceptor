"""
Начальная схема базы данных
"""

from yoyo import step

__depends__ = {}

steps = [
    step(
        # Создание таблицы topics
        """
        CREATE TABLE IF NOT EXISTS topics (
            id SERIAL PRIMARY KEY,
            prefix VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            topic_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Rollback
        "DROP TABLE IF EXISTS topics"
    ),
    step(
        # Создание таблицы source_chats
        """
        CREATE TABLE IF NOT EXISTS source_chats (
            id SERIAL PRIMARY KEY,
            chat_id VARCHAR(100) UNIQUE NOT NULL,
            name VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Rollback
        "DROP TABLE IF EXISTS source_chats"
    ),
    step(
        # Создание таблицы bot_config
        """
        CREATE TABLE IF NOT EXISTS bot_config (
            id SERIAL PRIMARY KEY,
            key VARCHAR(100) UNIQUE NOT NULL,
            value TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Rollback
        "DROP TABLE IF EXISTS bot_config"
    ),
    step(
        # Создание индексов
        """
        CREATE INDEX IF NOT EXISTS idx_topics_prefix ON topics(prefix);
        CREATE INDEX IF NOT EXISTS idx_source_chats_chat_id ON source_chats(chat_id);
        CREATE INDEX IF NOT EXISTS idx_source_chats_active ON source_chats(is_active)
        """,
        # Rollback
        """
        DROP INDEX IF EXISTS idx_topics_prefix;
        DROP INDEX IF EXISTS idx_source_chats_chat_id;
        DROP INDEX IF EXISTS idx_source_chats_active
        """
    ),
    step(
        # Вставка начальной конфигурации
        """
        INSERT INTO bot_config (key, value, description) VALUES
            ('target_chat_id', '', 'ID целевого чата для перенаправления сообщений'),
            ('include_sender_info', 'true', 'Добавлять ли информацию об отправителе'),
            ('sender_format', '{message}\nОтправил: {sender_name} ({sender_username})', 'Формат сообщения с информацией об отправителе')
        ON CONFLICT (key) DO NOTHING
        """,
        # Rollback
        """
        DELETE FROM bot_config
        WHERE key IN ('target_chat_id', 'include_sender_info', 'sender_format')
        """
    )
]
