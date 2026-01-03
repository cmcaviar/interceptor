-- Схема базы данных для Telegram Message Interceptor Bot

-- Таблица с информацией о топиках/темах
CREATE TABLE IF NOT EXISTS topics (
    id SERIAL PRIMARY KEY,
    prefix VARCHAR(50) UNIQUE NOT NULL,  -- Префикс команды (например, "1", "sky", "скай")
    name VARCHAR(255) NOT NULL,           -- Название чата/темы
    topic_id INTEGER NOT NULL,            -- message_thread_id в Telegram
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица с информацией об исходных чатах
CREATE TABLE IF NOT EXISTS source_chats (
    id SERIAL PRIMARY KEY,
    chat_id VARCHAR(100) UNIQUE NOT NULL,  -- ID чата в Telegram
    name VARCHAR(255),                     -- Название чата (опционально)
    is_active BOOLEAN DEFAULT TRUE,        -- Активен ли чат
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица с конфигурацией бота
CREATE TABLE IF NOT EXISTS bot_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_topics_prefix ON topics(prefix);
CREATE INDEX IF NOT EXISTS idx_source_chats_chat_id ON source_chats(chat_id);
CREATE INDEX IF NOT EXISTS idx_source_chats_active ON source_chats(is_active);

-- Вставка начальной конфигурации
INSERT INTO bot_config (key, value, description) VALUES
    ('target_chat_id', '-1003286030222', 'ID целевого чата для перенаправления сообщений'),
    ('include_sender_info', 'true', 'Добавлять ли информацию об отправителе'),
    ('sender_format', '{message}\nОтправил: {sender_name} ({sender_username})', 'Формат сообщения с информацией об отправителе')
ON CONFLICT (key) DO NOTHING;

-- Примеры данных (закомментированы, раскомментируйте и отредактируйте по необходимости)
-- INSERT INTO topics (prefix, name, topic_id) VALUES
--     ('1', 'Михаил', 287),
--     ('2', 'Траст', 290),
--     ('3', 'Веган', 295),
--     ('4', 'Эверест', 2898),
--     ('5', 'Скай', 289);

-- INSERT INTO source_chats (chat_id, name) VALUES
--     ('-1003698440205', 'Trust'),
--     ('-1002833859726', 'Sky'),
--     ('-1003121441569', 'Vegan');
