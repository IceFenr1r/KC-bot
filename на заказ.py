import logging
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters
)

# Настройка логгирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Словари для хранения данных
active_timers = {}  # {(chat_id, thread_id): (start_time, user_id)}
user_nicknames = {}  # {(chat_id, user_id): nickname}
username_to_id = {}  # {(chat_id, username): user_id}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    if not update.message or not update.message.text:
        return
        
    message = update.message
    user_text = message.text.lower().strip()
    user = message.from_user
    chat_id = message.chat_id
    thread_id = message.message_thread_id or 0
    chat_key = (chat_id, thread_id)
    
    # Обновляем информацию о пользователе
    if user.username:
        username_key = (chat_id, user.username.lower())
        if username_key not in username_to_id or username_to_id[username_key] != user.id:
            username_to_id[username_key] = user.id
            logger.info(f"Updated user mapping: @{user.username} -> {user.id}")
    
    logger.info(f"Received message: '{message.text}' from user_id: {user.id}")
    
    # Обработка команд "встал", "стал"
    if user_text in ["встал", "стал", "+"]:
        # Останавливаем предыдущий таймер
        if chat_key in active_timers:
            prev_start_time, prev_user_id = active_timers[chat_key]
            elapsed = datetime.now() - prev_start_time
            mins, secs = divmod(elapsed.total_seconds(), 60)
            prev_user_nick = get_user_nickname(chat_id, prev_user_id)
            await message.reply_text(
                f"Номер стоял у {prev_user_nick}: {int(mins)} минут {int(secs)} секунд",
                message_thread_id=thread_id
            )
            del active_timers[chat_key]
        
        # Запускаем новый таймер
        active_timers[chat_key] = (datetime.now(), user.id)
        user_nick = get_user_nickname(chat_id, user.id)
        await message.reply_text(
            f"Номер у {user_nick} стал",
            message_thread_id=thread_id
        )
        
    # Обработка команд "слёт", "слет"
    elif user_text in ["слёт", "слет", "-", "слетел"]:
        if chat_key in active_timers:
            start_time, timer_user_id = active_timers[chat_key]
            elapsed = datetime.now() - start_time
            mins, secs = divmod(elapsed.total_seconds(), 60)
            user_nick = get_user_nickname(chat_id, timer_user_id)
            await message.reply_text(
                f"Номер стоял у {user_nick} (слёт): {int(mins)} минут {int(secs)} секунд",
                message_thread_id=thread_id
            )
            del active_timers[chat_key]
        else:
            await message.reply_text(
                "Таймер не запущен",
                message_thread_id=thread_id
            )
            
    # Обработка команд "статус", "status"
    elif user_text in ["статус"]:
        if chat_key in active_timers:
            start_time, timer_user_id = active_timers[chat_key]
            elapsed = datetime.now() - start_time
            mins, secs = divmod(elapsed.total_seconds(), 60)
            user_nick = get_user_nickname(chat_id, timer_user_id)
            await message.reply_text(
                f"Таймер работает у {user_nick}: {int(mins)} минут {int(secs)} секунд",
                message_thread_id=thread_id
            )
        else:
            await message.reply_text(
                "Таймер не запущен",
                message_thread_id=thread_id
            )

async def set_user_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /user для установки кличек"""
    if not update.message:
        return
        
    message = update.message
    chat_id = message.chat_id
    thread_id = message.message_thread_id or 0
    
    logger.info(f"Received /user command: '{message.text}' from user_id: {message.from_user.id}")
    
    # Проверка формата команды
    if not context.args or len(context.args) < 2:
        await message.reply_text(
            "Используйте: /user @username кличка\nПример: /user @test_user Орел",
            message_thread_id=thread_id
        )
        return
    
    # Извлекаем username (удаляем @ если есть)
    username = context.args[0].lstrip('@').lower()
    nickname = ' '.join(context.args[1:])
    
    # Сохраняем кличку
    user_key = (chat_id, username)
    if user_key in username_to_id:
        user_id = username_to_id[user_key]
        user_nicknames[(chat_id, user_id)] = nickname
        logger.info(f"Nickname set for user_id {user_id} (@{username}): {nickname}")
        await message.reply_text(
            f"Кличка для @{username} установлена: {nickname}",
            message_thread_id=thread_id
        )
    else:
        logger.warning(f"User @{username} not found in mapping")
        await message.reply_text(
            f"Пользователь @{username} не найден. Он должен был хотя бы раз написать в чат.",
            message_thread_id=thread_id
        )

def get_user_nickname(chat_id: int, user_id: int) -> str:
    """Получает кличку пользователя по ID"""
    key = (chat_id, user_id)
    if key in user_nicknames:
        return user_nicknames[key]
    
    # Попробуем найти по username
    for (c_id, username), u_id in username_to_id.items():
        if c_id == chat_id and u_id == user_id:
            # Вернем username если кличка не найдена
            return f"@{username}"
    
    # Если ничего не найдено, вернем часть ID
    return f"игрок {str(user_id)[-4:]}"

def main() -> None:
    """Запуск бота"""
    application = Application.builder().token("6426361341:AAFThWhDPqWWkZbEBexE3bM5elMBTG9aEZk").build()
    
    # Обработчики
    application.add_handler(CommandHandler("user", set_user_nick))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запуск бота
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()