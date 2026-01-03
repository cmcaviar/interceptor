#!/usr/bin/env python3
"""
Модуль админ-панели для управления ботом через Telegram.
"""

import logging
import os
import json
from datetime import datetime
from typing import Optional, Set
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
from database import Database

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
(
    MAIN_MENU,
    TOPICS_MENU,
    SOURCE_CHATS_MENU,
    ADD_TOPIC,
    EDIT_TOPIC,
    DELETE_TOPIC,
    ADD_SOURCE_CHAT,
    DELETE_SOURCE_CHAT,
    TOGGLE_SOURCE_CHAT,
    SET_TARGET_CHAT,
    WAITING_TOPIC_DATA,
    WAITING_TOPIC_PREFIX,
    WAITING_TOPIC_EDIT_PREFIX,
    WAITING_TOPIC_EDIT_DATA,
    WAITING_SOURCE_CHAT_DATA,
) = range(15)

# Глобальные переменные
db: Optional[Database] = None
ADMIN_IDS: Set[int] = set()
DEBUG_MODE: bool = False
DEBUG_FILE_PATH: str = "debug_updates.txt"


def init_admin(database: Database, admin_ids: Set[int]):
    """Инициализация админ-модуля."""
    global db, ADMIN_IDS
    db = database
    ADMIN_IDS = admin_ids
    logger.info(f"Админ-панель инициализирована. Админов: {len(ADMIN_IDS)}")


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором."""
    return user_id in ADMIN_IDS


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /start."""
    user = update.effective_user

    # Если админ - показываем админ-панель
    if is_admin(user.id):
        debug_button_text = "🔴 Выключить отладку" if DEBUG_MODE else "🟢 Включить отладку"
        keyboard = [
            [InlineKeyboardButton("📋 Управление топиками", callback_data="menu_topics")],
            [InlineKeyboardButton("💬 Управление исходными чатами", callback_data="menu_source_chats")],
            [InlineKeyboardButton("🎯 Установить целевой чат", callback_data="set_target_chat")],
            [InlineKeyboardButton("📊 Показать статистику", callback_data="show_stats")],
            [InlineKeyboardButton(debug_button_text, callback_data="toggle_debug")],
            [InlineKeyboardButton("❌ Закрыть", callback_data="close")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🔧 <b>Админ-панель</b>\n\n"
            "Выберите действие:",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

        return MAIN_MENU
    else:
        # Обычный пользователь
        await update.message.reply_text(
            "👋 Привет! Я бот для перенаправления сообщений.\n\n"
            "Отправьте сообщение в формате:\n"
            "<code>/префикс данные</code>\n\n"
            "Например: <code>/1 27.5</code>",
            parse_mode="HTML"
        )
        return ConversationHandler.END


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /admin - показывает главное меню."""
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("❌ У вас нет прав доступа к админ-панели.")
        return ConversationHandler.END

    debug_button_text = "🔴 Выключить отладку" if DEBUG_MODE else "🟢 Включить отладку"
    keyboard = [
        [InlineKeyboardButton("📋 Управление топиками", callback_data="menu_topics")],
        [InlineKeyboardButton("💬 Управление исходными чатами", callback_data="menu_source_chats")],
        [InlineKeyboardButton("🎯 Установить целевой чат", callback_data="set_target_chat")],
        [InlineKeyboardButton("📊 Показать статистику", callback_data="show_stats")],
        [InlineKeyboardButton(debug_button_text, callback_data="toggle_debug")],
        [InlineKeyboardButton("❌ Закрыть", callback_data="close")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🔧 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

    return MAIN_MENU


async def show_main_menu_after_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает главное меню после выполнения действия (без callback query)."""
    debug_button_text = "🔴 Выключить отладку" if DEBUG_MODE else "🟢 Включить отладку"
    keyboard = [
        [InlineKeyboardButton("📋 Управление топиками", callback_data="menu_topics")],
        [InlineKeyboardButton("💬 Управление исходными чатами", callback_data="menu_source_chats")],
        [InlineKeyboardButton("🎯 Установить целевой чат", callback_data="set_target_chat")],
        [InlineKeyboardButton("📊 Показать статистику", callback_data="show_stats")],
        [InlineKeyboardButton(debug_button_text, callback_data="toggle_debug")],
        [InlineKeyboardButton("❌ Закрыть", callback_data="close")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🔧 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

    return MAIN_MENU


async def show_topics_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает меню управления топиками."""
    global db

    query = update.callback_query
    await query.answer()

    if db is None:
        await query.edit_message_text("❌ База данных не инициализирована.")
        return ConversationHandler.END

    # Получаем список топиков
    topics = await db.get_topics()
    topic_names = await db.get_topic_names()

    text = "📋 <b>Управление топиками</b>\n\n"
    text += f"Всего топиков: {len(topics)}\n\n"

    if topics:
        text += "<b>Список топиков:</b>\n"
        for prefix in sorted(topics.keys()):
            name = topic_names.get(prefix, "—")
            topic_id = topics[prefix]
            text += f"/{prefix} → {name} (ID: {topic_id})\n"
    else:
        text += "Топики отсутствуют.\n"

    keyboard = [
        [InlineKeyboardButton("➕ Добавить топик", callback_data="add_topic")],
        [InlineKeyboardButton("✏️ Редактировать топик", callback_data="edit_topic")],
        [InlineKeyboardButton("🗑 Удалить топик", callback_data="delete_topic")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
    return TOPICS_MENU


async def show_topics_menu_after_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает меню топиков после выполнения действия (без callback query)."""
    global db

    if db is None:
        await update.message.reply_text("❌ База данных не инициализирована.")
        return ConversationHandler.END

    # Получаем список топиков
    topics = await db.get_topics()
    topic_names = await db.get_topic_names()

    text = "📋 <b>Управление топиками</b>\n\n"
    text += f"Всего топиков: {len(topics)}\n\n"

    if topics:
        text += "<b>Список топиков:</b>\n"
        for prefix in sorted(topics.keys()):
            name = topic_names.get(prefix, "—")
            topic_id = topics[prefix]
            text += f"/{prefix} → {name} (ID: {topic_id})\n"
    else:
        text += "Топики отсутствуют.\n"

    keyboard = [
        [InlineKeyboardButton("➕ Добавить топик", callback_data="add_topic")],
        [InlineKeyboardButton("✏️ Редактировать топик", callback_data="edit_topic")],
        [InlineKeyboardButton("🗑 Удалить топик", callback_data="delete_topic")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")
    return TOPICS_MENU


async def show_source_chats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает меню управления исходными чатами."""
    global db

    query = update.callback_query
    await query.answer()

    if db is None:
        await query.edit_message_text("❌ База данных не инициализирована.")
        return ConversationHandler.END

    # Получаем список чатов из БД
    async with db.pool.acquire() as conn:
        chats = await conn.fetch(
            "SELECT chat_id, name, is_active FROM source_chats ORDER BY name"
        )

    text = "💬 <b>Управление исходными чатами</b>\n\n"
    text += f"Всего чатов: {len(chats)}\n\n"

    if chats:
        text += "<b>Список чатов:</b>\n"
        for chat in chats:
            status = "✅" if chat['is_active'] else "❌"
            name = chat['name'] or "Без названия"
            text += f"{status} {name}: {chat['chat_id']}\n"
    else:
        text += "Исходные чаты отсутствуют.\n"

    keyboard = [
        [InlineKeyboardButton("➕ Добавить чат", callback_data="add_source_chat")],
        [InlineKeyboardButton("🔄 Вкл/Выкл чат", callback_data="toggle_source_chat")],
        [InlineKeyboardButton("🗑 Удалить чат", callback_data="delete_source_chat")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
    return SOURCE_CHATS_MENU


async def show_source_chats_menu_after_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает меню исходных чатов после выполнения действия (без callback query)."""
    global db

    if db is None:
        await update.message.reply_text("❌ База данных не инициализирована.")
        return ConversationHandler.END

    # Получаем список чатов из БД
    async with db.pool.acquire() as conn:
        chats = await conn.fetch(
            "SELECT chat_id, name, is_active FROM source_chats ORDER BY name"
        )

    text = "💬 <b>Управление исходными чатами</b>\n\n"
    text += f"Всего чатов: {len(chats)}\n\n"

    if chats:
        text += "<b>Список чатов:</b>\n"
        for chat in chats:
            status = "✅" if chat['is_active'] else "❌"
            name = chat['name'] or "Без названия"
            text += f"{status} {name}: {chat['chat_id']}\n"
    else:
        text += "Исходные чаты отсутствуют.\n"

    keyboard = [
        [InlineKeyboardButton("➕ Добавить чат", callback_data="add_source_chat")],
        [InlineKeyboardButton("🔄 Вкл/Выкл чат", callback_data="toggle_source_chat")],
        [InlineKeyboardButton("🗑 Удалить чат", callback_data="delete_source_chat")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")
    return SOURCE_CHATS_MENU


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает статистику."""
    global db

    query = update.callback_query
    await query.answer()

    if db is None:
        await query.edit_message_text("❌ База данных не инициализирована.")
        return ConversationHandler.END

    config = await db.get_all_config()
    topics = await db.get_topics()
    source_chats = await db.get_source_chats()

    target_chat_id = config.get('target_chat_id', 'Не установлен')

    text = "📊 <b>Статистика бота</b>\n\n"
    text += f"<b>Топиков:</b> {len(topics)}\n"
    text += f"<b>Исходных чатов (активных):</b> {len(source_chats)}\n"
    text += f"<b>Целевой чат:</b> {target_chat_id}\n"

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
    return MAIN_MENU


async def start_add_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса добавления топика."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "➕ <b>Добавление топика</b>\n\n"
        "Отправьте данные в формате:\n"
        "<code>префикс:название:topic_id</code>\n\n"
        "Пример: <code>1:Скай:289</code>\n\n"
        "Или отправьте /cancel для отмены.",
        parse_mode="HTML"
    )

    return WAITING_TOPIC_DATA


async def process_add_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка добавления топика."""
    global db

    text = update.message.text.strip()

    if ':' not in text or text.count(':') != 2:
        await update.message.reply_text(
            "❌ Неверный формат. Используйте:\n"
            "<code>префикс:название:topic_id</code>",
            parse_mode="HTML"
        )
        return WAITING_TOPIC_DATA

    try:
        prefix, name, topic_id_str = text.split(':', 2)
        topic_id = int(topic_id_str)

        if db is None:
            await update.message.reply_text("❌ База данных не инициализирована.")
            return ConversationHandler.END

        success = await db.add_topic(prefix.strip(), name.strip(), topic_id)

        if success:
            # Перезагружаем данные в боте
            import bot
            await bot.load_data_from_db()

            await update.message.reply_text(
                f"✅ Топик успешно добавлен!\n"
                f"/{prefix} → {name} (ID: {topic_id})"
            )
        else:
            await update.message.reply_text(
                f"❌ Топик с префиксом '{prefix}' уже существует."
            )
    except ValueError:
        await update.message.reply_text("❌ topic_id должен быть числом.")
        return WAITING_TOPIC_DATA
    except Exception as e:
        logger.error(f"Ошибка добавления топика: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ошибка: {e}")

    # Возвращаем в меню топиков
    return await show_topics_menu_after_action(update, context)


async def start_delete_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса удаления топика."""
    global db

    query = update.callback_query
    await query.answer()

    if db is None:
        await query.edit_message_text("❌ База данных не инициализирована.")
        return ConversationHandler.END

    topics = await db.get_topics()
    topic_names = await db.get_topic_names()

    if not topics:
        await query.edit_message_text("❌ Нет топиков для удаления.")
        return ConversationHandler.END

    text = "🗑 <b>Удаление топика</b>\n\n"
    text += "Отправьте префикс топика для удаления:\n\n"

    for prefix in sorted(topics.keys()):
        name = topic_names.get(prefix, "—")
        text += f"/{prefix} → {name}\n"

    text += "\nИли отправьте /cancel для отмены."

    await query.edit_message_text(text, parse_mode="HTML")
    return WAITING_TOPIC_PREFIX


async def process_delete_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка удаления топика."""
    global db

    prefix = update.message.text.strip().lstrip('/')

    if db is None:
        await update.message.reply_text("❌ База данных не инициализирована.")
        return ConversationHandler.END

    success = await db.delete_topic(prefix)

    if success:
        # Перезагружаем данные в боте
        import bot
        await bot.load_data_from_db()

        await update.message.reply_text(f"✅ Топик /{prefix} успешно удален.")
    else:
        await update.message.reply_text(f"❌ Топик /{prefix} не найден.")

    # Возвращаем в меню топиков
    return await show_topics_menu_after_action(update, context)


async def start_edit_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса редактирования топика."""
    global db

    query = update.callback_query
    await query.answer()

    if db is None:
        await query.edit_message_text("❌ База данных не инициализирована.")
        return ConversationHandler.END

    topics = await db.get_topics()
    topic_names = await db.get_topic_names()

    if not topics:
        await query.edit_message_text("❌ Нет топиков для редактирования.")
        return ConversationHandler.END

    text = "✏️ <b>Редактирование топика</b>\n\n"
    text += "Отправьте префикс топика, который хотите отредактировать:\n\n"

    for prefix in sorted(topics.keys()):
        name = topic_names.get(prefix, "—")
        topic_id = topics[prefix]
        text += f"/{prefix} → {name} (ID: {topic_id})\n"

    text += "\nИли отправьте /cancel для отмены."

    await query.edit_message_text(text, parse_mode="HTML")
    return WAITING_TOPIC_EDIT_PREFIX


async def process_edit_topic_prefix(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора префикса для редактирования."""
    global db

    prefix = update.message.text.strip().lstrip('/')

    if db is None:
        await update.message.reply_text("❌ База данных не инициализирована.")
        return ConversationHandler.END

    topics = await db.get_topics()
    topic_names = await db.get_topic_names()

    if prefix not in topics:
        await update.message.reply_text(f"❌ Топик /{prefix} не найден. Попробуйте снова или /cancel для отмены.")
        return WAITING_TOPIC_EDIT_PREFIX

    # Сохраняем префикс в context для следующего шага
    context.user_data['edit_prefix'] = prefix

    current_name = topic_names.get(prefix, "—")
    current_topic_id = topics[prefix]

    await update.message.reply_text(
        f"✏️ <b>Редактирование топика /{prefix}</b>\n\n"
        f"Текущие данные:\n"
        f"Название: {current_name}\n"
        f"Topic ID: {current_topic_id}\n\n"
        f"Отправьте новые данные в формате:\n"
        f"<code>название:topic_id</code>\n\n"
        f"Пример: <code>Новое название:456</code>\n\n"
        f"Или отправьте /cancel для отмены.",
        parse_mode="HTML"
    )

    return WAITING_TOPIC_EDIT_DATA


async def process_edit_topic_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка новых данных топика."""
    global db

    text = update.message.text.strip()
    prefix = context.user_data.get('edit_prefix')

    if not prefix:
        await update.message.reply_text("❌ Ошибка: префикс не найден. Начните заново.")
        return ConversationHandler.END

    if ':' not in text:
        await update.message.reply_text(
            "❌ Неверный формат. Используйте:\n"
            "<code>название:topic_id</code>",
            parse_mode="HTML"
        )
        return WAITING_TOPIC_EDIT_DATA

    try:
        name, topic_id_str = text.split(':', 1)
        topic_id = int(topic_id_str)

        if db is None:
            await update.message.reply_text("❌ База данных не инициализирована.")
            return ConversationHandler.END

        success = await db.update_topic(prefix, name.strip(), topic_id)

        if success:
            # Перезагружаем данные в боте
            import bot
            await bot.load_data_from_db()

            await update.message.reply_text(
                f"✅ Топик успешно обновлен!\n"
                f"/{prefix} → {name.strip()} (ID: {topic_id})"
            )
        else:
            await update.message.reply_text(f"❌ Топик /{prefix} не найден.")

        # Очищаем данные из context
        context.user_data.pop('edit_prefix', None)

    except ValueError:
        await update.message.reply_text("❌ topic_id должен быть числом.")
        return WAITING_TOPIC_EDIT_DATA
    except Exception as e:
        logger.error(f"Ошибка редактирования топика: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ошибка: {e}")
        context.user_data.pop('edit_prefix', None)

    # Возвращаем в меню топиков
    return await show_topics_menu_after_action(update, context)


async def start_add_source_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса добавления исходного чата."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "➕ <b>Добавление исходного чата</b>\n\n"
        "Отправьте данные в формате:\n"
        "<code>chat_id:название</code>\n\n"
        "Пример: <code>-1001234567890:Мой чат</code>\n\n"
        "Или отправьте /cancel для отмены.",
        parse_mode="HTML"
    )

    return WAITING_SOURCE_CHAT_DATA


async def process_add_source_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка добавления исходного чата."""
    global db

    text = update.message.text.strip()

    if ':' not in text:
        await update.message.reply_text(
            "❌ Неверный формат. Используйте:\n"
            "<code>chat_id:название</code>",
            parse_mode="HTML"
        )
        return WAITING_SOURCE_CHAT_DATA

    try:
        chat_id, name = text.split(':', 1)

        if db is None:
            await update.message.reply_text("❌ База данных не инициализирована.")
            return ConversationHandler.END

        success = await db.add_source_chat(chat_id.strip(), name.strip())

        if success:
            # Перезагружаем данные в боте
            import bot
            await bot.load_data_from_db()

            await update.message.reply_text(
                f"✅ Исходный чат успешно добавлен!\n"
                f"{name}: {chat_id}"
            )
        else:
            await update.message.reply_text(
                f"❌ Чат с ID '{chat_id}' уже существует."
            )
    except Exception as e:
        logger.error(f"Ошибка добавления чата: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ошибка: {e}")

    # Возвращаем в меню исходных чатов
    return await show_source_chats_menu_after_action(update, context)


async def start_delete_source_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса удаления исходного чата."""
    global db

    query = update.callback_query
    await query.answer()

    if db is None:
        await query.edit_message_text("❌ База данных не инициализирована.")
        return ConversationHandler.END

    async with db.pool.acquire() as conn:
        chats = await conn.fetch(
            "SELECT chat_id, name FROM source_chats ORDER BY name"
        )

    if not chats:
        await query.edit_message_text("❌ Нет чатов для удаления.")
        return ConversationHandler.END

    text = "🗑 <b>Удаление исходного чата</b>\n\n"
    text += "Отправьте chat_id для удаления:\n\n"

    for chat in chats:
        name = chat['name'] or "Без названия"
        text += f"{name}: <code>{chat['chat_id']}</code>\n"

    text += "\nИли отправьте /cancel для отмены."

    await query.edit_message_text(text, parse_mode="HTML")
    return DELETE_SOURCE_CHAT


async def process_delete_source_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка удаления исходного чата."""
    global db

    chat_id = update.message.text.strip()

    if db is None:
        await update.message.reply_text("❌ База данных не инициализирована.")
        return ConversationHandler.END

    async with db.pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM source_chats WHERE chat_id = $1", chat_id
        )

    success = result.split()[-1] == '1'

    if success:
        # Перезагружаем данные в боте
        import bot
        await bot.load_data_from_db()

        await update.message.reply_text(f"✅ Чат {chat_id} успешно удален.")
    else:
        await update.message.reply_text(f"❌ Чат {chat_id} не найден.")

    # Возвращаем в меню исходных чатов
    return await show_source_chats_menu_after_action(update, context)


async def start_set_target_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса установки целевого чата."""
    global db

    query = update.callback_query
    await query.answer()

    if db is None:
        await query.edit_message_text("❌ База данных не инициализирована.")
        return ConversationHandler.END

    config = await db.get_all_config()
    current_target = config.get('target_chat_id', 'Не установлен')

    await query.edit_message_text(
        f"🎯 <b>Установка целевого чата</b>\n\n"
        f"Текущий: <code>{current_target}</code>\n\n"
        f"Отправьте новый chat_id целевого чата\n"
        f"или /cancel для отмены.",
        parse_mode="HTML"
    )

    return SET_TARGET_CHAT


async def process_set_target_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка установки целевого чата."""
    global db

    chat_id = update.message.text.strip()

    if db is None:
        await update.message.reply_text("❌ База данных не инициализирована.")
        return ConversationHandler.END

    try:
        await db.set_config('target_chat_id', chat_id)

        # Перезагружаем данные в боте
        import bot
        await bot.load_data_from_db()

        await update.message.reply_text(
            f"✅ Целевой чат успешно установлен: {chat_id}"
        )
    except Exception as e:
        logger.error(f"Ошибка установки целевого чата: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ошибка: {e}")

    # Возвращаем в главное меню
    return await show_main_menu_after_action(update, context)


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Возврат в главное меню."""
    query = update.callback_query
    await query.answer()

    debug_button_text = "🔴 Выключить отладку" if DEBUG_MODE else "🟢 Включить отладку"
    keyboard = [
        [InlineKeyboardButton("📋 Управление топиками", callback_data="menu_topics")],
        [InlineKeyboardButton("💬 Управление исходными чатами", callback_data="menu_source_chats")],
        [InlineKeyboardButton("🎯 Установить целевой чат", callback_data="set_target_chat")],
        [InlineKeyboardButton("📊 Показать статистику", callback_data="show_stats")],
        [InlineKeyboardButton(debug_button_text, callback_data="toggle_debug")],
        [InlineKeyboardButton("❌ Закрыть", callback_data="close")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "🔧 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

    return MAIN_MENU


async def close_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Закрытие меню."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ Админ-панель закрыта.")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена операции."""
    await update.message.reply_text("❌ Операция отменена.")
    return ConversationHandler.END


async def handle_unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик неизвестных команд для админов."""
    user = update.effective_user

    # Проверяем, является ли пользователь админом
    if not is_admin(user.id):
        return ConversationHandler.END

    # Показываем админ-панель
    debug_button_text = "🔴 Выключить отладку" if DEBUG_MODE else "🟢 Включить отладку"
    keyboard = [
        [InlineKeyboardButton("📋 Управление топиками", callback_data="menu_topics")],
        [InlineKeyboardButton("💬 Управление исходными чатами", callback_data="menu_source_chats")],
        [InlineKeyboardButton("🎯 Установить целевой чат", callback_data="set_target_chat")],
        [InlineKeyboardButton("📊 Показать статистику", callback_data="show_stats")],
        [InlineKeyboardButton(debug_button_text, callback_data="toggle_debug")],
        [InlineKeyboardButton("❌ Закрыть", callback_data="close")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🔧 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

    return MAIN_MENU


def log_update_to_file(update: Update) -> None:
    """Логирует информацию об update в файл."""
    global DEBUG_MODE, DEBUG_FILE_PATH

    if not DEBUG_MODE:
        return

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Формируем данные для записи
        log_data = {
            "timestamp": timestamp,
            "update_id": update.update_id,
        }

        # Информация о сообщении
        if update.message:
            msg = update.message
            log_data["message"] = {
                "message_id": msg.message_id,
                "chat_id": msg.chat.id,
                "chat_type": msg.chat.type,
                "chat_title": msg.chat.title,
                "message_thread_id": msg.message_thread_id,
                "from_user_id": msg.from_user.id if msg.from_user else None,
                "from_user_name": msg.from_user.full_name if msg.from_user else None,
                "from_user_username": msg.from_user.username if msg.from_user else None,
                "text": msg.text,
                "date": msg.date.isoformat() if msg.date else None,
            }

        # Информация о callback query
        if update.callback_query:
            cq = update.callback_query
            log_data["callback_query"] = {
                "id": cq.id,
                "data": cq.data,
                "chat_id": cq.message.chat.id if cq.message else None,
                "from_user_id": cq.from_user.id if cq.from_user else None,
            }

        # Записываем в файл
        with open(DEBUG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(json.dumps(log_data, ensure_ascii=False, indent=2))
            f.write(f"\n{'='*80}\n")

        logger.info(f"Update {update.update_id} залогирован в {DEBUG_FILE_PATH}")

    except Exception as e:
        logger.error(f"Ошибка при логировании update: {e}", exc_info=True)


async def toggle_debug_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Включает или выключает режим отладки."""
    global DEBUG_MODE, DEBUG_FILE_PATH

    query = update.callback_query
    await query.answer()

    user = update.effective_user

    if DEBUG_MODE:
        # Выключаем дебаг-режим и отправляем файл
        DEBUG_MODE = False

        # Проверяем, существует ли файл
        if os.path.exists(DEBUG_FILE_PATH):
            # Отправляем файл пользователю
            try:
                with open(DEBUG_FILE_PATH, "rb") as f:
                    await context.bot.send_document(
                        chat_id=user.id,
                        document=f,
                        filename=f"debug_updates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        caption="📋 Лог отладки обновлений"
                    )

                # Удаляем файл после отправки
                os.remove(DEBUG_FILE_PATH)
                logger.info(f"Дебаг-режим выключен, файл отправлен пользователю {user.id}")

                await query.edit_message_text(
                    "✅ <b>Режим отладки выключен</b>\n\n"
                    "Файл с логами отправлен вам в личные сообщения.",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке файла: {e}", exc_info=True)
                await query.edit_message_text(
                    f"❌ Ошибка при отправке файла: {e}\n\n"
                    f"Файл сохранен в: {DEBUG_FILE_PATH}",
                    parse_mode="HTML"
                )
        else:
            await query.edit_message_text(
                "⚠️ <b>Режим отладки выключен</b>\n\n"
                "Файл логов не найден (возможно, не было обновлений).",
                parse_mode="HTML"
            )
    else:
        # Включаем дебаг-режим
        DEBUG_MODE = True

        # Создаем новый файл с заголовком
        with open(DEBUG_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(f"DEBUG LOG - Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        logger.info(f"Дебаг-режим включен пользователем {user.id}")

        await query.edit_message_text(
            "✅ <b>Режим отладки включен</b>\n\n"
            f"Все обновления будут записываться в файл.\n"
            f"Для остановки нажмите кнопку еще раз.",
            parse_mode="HTML"
        )

    # Возвращаемся в главное меню через 2 секунды
    import asyncio
    await asyncio.sleep(2)
    return await back_to_main(update, context)


def get_admin_conversation_handler():
    """Возвращает ConversationHandler для админ-панели."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command),
            CommandHandler("admin", admin_command)
        ],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(show_topics_menu, pattern="^menu_topics$"),
                CallbackQueryHandler(show_source_chats_menu, pattern="^menu_source_chats$"),
                CallbackQueryHandler(start_set_target_chat, pattern="^set_target_chat$"),
                CallbackQueryHandler(show_stats, pattern="^show_stats$"),
                CallbackQueryHandler(toggle_debug_mode, pattern="^toggle_debug$"),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
                CallbackQueryHandler(close_menu, pattern="^close$"),
            ],
            TOPICS_MENU: [
                CallbackQueryHandler(start_add_topic, pattern="^add_topic$"),
                CallbackQueryHandler(start_edit_topic, pattern="^edit_topic$"),
                CallbackQueryHandler(start_delete_topic, pattern="^delete_topic$"),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
            ],
            SOURCE_CHATS_MENU: [
                CallbackQueryHandler(start_add_source_chat, pattern="^add_source_chat$"),
                CallbackQueryHandler(start_delete_source_chat, pattern="^delete_source_chat$"),
                CallbackQueryHandler(back_to_main, pattern="^back_to_main$"),
            ],
            WAITING_TOPIC_DATA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_add_topic),
                CommandHandler("cancel", cancel),
            ],
            WAITING_TOPIC_PREFIX: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_delete_topic),
                CommandHandler("cancel", cancel),
            ],
            WAITING_TOPIC_EDIT_PREFIX: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_edit_topic_prefix),
                CommandHandler("cancel", cancel),
            ],
            WAITING_TOPIC_EDIT_DATA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_edit_topic_data),
                CommandHandler("cancel", cancel),
            ],
            WAITING_SOURCE_CHAT_DATA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_add_source_chat),
                CommandHandler("cancel", cancel),
            ],
            DELETE_SOURCE_CHAT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_delete_source_chat),
                CommandHandler("cancel", cancel),
            ],
            SET_TARGET_CHAT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_set_target_chat),
                CommandHandler("cancel", cancel),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.COMMAND, handle_unknown_command),
        ],
    )
