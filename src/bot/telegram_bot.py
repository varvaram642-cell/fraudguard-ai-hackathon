import os
import logging
from typing import Dict, Any, Optional
import telebot
from telebot import types

from src.database.db_client import DatabaseClient
from src.core.engine import FraudEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("FraudGuardBot")

class FraudGuardBot:
    def __init__(self, token: str, engine: FraudEngine):
        self.bot: telebot.TeleBot = telebot.TeleBot(token)
        self.engine: FraudEngine = engine
        self.user_states: Dict[int, Dict[str, Any]] = {}
        self._register_handlers()

    def _register_handlers(self) -> None:
        self.bot.register_message_handler(self.send_welcome, commands=['start', 'help'])
        self.bot.register_message_handler(self.handle_report_command, commands=['report'])
        self.bot.register_callback_query_handler(self.handle_callbacks, func=lambda call: True)

    def send_welcome(self, message: types.Message) -> None:
        welcome_text = (
            "🛡️ Добро пожаловать в FraudGuard AI!\n\n"
            "Я интеллектуальный бот-помощник для детекции мошеннических транзакций.\n\n"
            "Доступные команды:\n"
            "/report @username — пожаловаться на пользователя\n"
            "/start — главное меню\n\n"
            "Выберите нужное действие ниже:"
        )
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_check = types.InlineKeyboardButton("Проверить транзакцию", callback_data="check_tx")
        btn_info = types.InlineKeyboardButton("О системе антифрода", callback_data="system_info")
        markup.add(btn_check, btn_info)
        
        self.bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

    def handle_report_command(self, message: types.Message) -> None:
        args = message.text.split()
        if len(args) < 2:
            self.bot.reply_to(message, "Укажите username. Пример: /report @ivan")
            return
        
        username = args[1].lstrip("@")
        transaction_data = {
            "amount": 10000.0,
            "card_hash": f"card_{username}_report",
            "telegram_id": message.from_user.id
        }
        
        self.bot.reply_to(message, f"Проверяю пользователя @{username} в реестре угроз...")
        
        try:
            result = self.engine.check_transaction(transaction_data)
            if result["approved"]:
                self.bot.send_message(
                    message.chat.id,
                    f"Жалоба на @{username} проверена. Подозрительной активности не обнаружено."
                )
            else:
                self.bot.send_message(
                    message.chat.id,
                    f"Жалоба подтверждена! @{username} идентифицирован как фрод.\n"
                    f"Причина: {result['reason']}. Действия заблокированы."
                )
        except Exception as e:
            logger.error(f"Ошибка проверки жалобы для {username}: {e}", exc_info=True)
            self.bot.send_message(message.chat.id, "Произошла внутренняя ошибка при проверке жалобы.")

    def handle_callbacks(self, call: types.CallbackQuery) -> None:
        if call.data == "check_tx":
            self.bot.answer_callback_query(call.id)
            msg = self.bot.send_message(call.message.chat.id, "Шаг 1/2: Введите сумму транзакции (число):")
            self.bot.register_next_step_handler(msg, self.process_amount_step)
            
        elif call.data == "system_info":
            self.bot.answer_callback_query(call.id)
            info_text = (
                "Как работает защита:\n"
                "1. Анализ лимитов: Блокировка разовых переводов выше нормы.\n"
                "2. Скользящее окно: Отслеживание аномально частых транзакций.\n"
                "3. Графовый анализ: Выявление связей карты с множеством аккаунтов.\n"
                "4. Черный список: Глобальная блокировка карт и пользователей."
            )
            self.bot.send_message(call.message.chat.id, info_text)

    def process_amount_step(self, message: types.Message) -> None:
        try:
            amount = float(message.text)
            self.user_states[message.chat.id] = {"amount": amount}
            msg = self.bot.send_message(message.chat.id, "Шаг 2/2: Введите хэш карты (например: card_123):")
            self.bot.register_next_step_handler(msg, self.process_card_step)
        except ValueError:
            msg = self.bot.send_message(message.chat.id, "Ошибка: Введите числовое значение суммы!")
            self.bot.register_next_step_handler(msg, self.process_amount_step)

    def process_card_step(self, message: types.Message) -> None:
        card_hash = message.text.strip() if message.text else ""
        if not card_hash:
            msg = self.bot.send_message(message.chat.id, "Карта не может быть пустой. Попробуйте еще раз:")
            self.bot.register_next_step_handler(msg, self.process_card_step)
            return
        
        if message.chat.id not in self.user_states:
            self.bot.send_message(message.chat.id, "Время сессии истекло. Начните сначала: /start")
            return
        
        self.user_states[message.chat.id]["card_hash"] = card_hash
        self.user_states[message.chat.id]["telegram_id"] = message.from_user.id
        self.execute_fraud_check(message.chat.id)

    def execute_fraud_check(self, chat_id: int) -> None:
        data = self.user_states.get(chat_id)
        if not data:
            self.bot.send_message(chat_id, "Ошибка сессии. Начните сначала: /start")
            return
        
        self.bot.send_message(chat_id, "Запущен скоринг транзакции в системе безопасности...")
        
        try:
            result = self.engine.check_transaction(data)
            if result["approved"]:
                response = (
                    f"ТРАНЗАКЦИЯ ОДОБРЕНА\n\n"
                    f"Сумма: {data['amount']:.2f} руб.\n"
                    f"Карта: {data['card_hash']}\n"
                    "Безопасность: Угроз не обнаружено."
                )
            else:
                response = (
                    f"ВНИМАНИЕ: ОБНАРУЖЕН ФРОД!\n\n"
                    f"Сумма: {data['amount']:.2f} руб.\n"
                    f"Карта: {data['card_hash']}\n"
                    f"Причина блокировки: {result['reason']}"
                )
            
            self.bot.send_message(chat_id, response)
        except Exception as e:
            logger.error(f"Ошибка скоринга транзакции для чата {chat_id}: {e}", exc_info=True)
            self.bot.send_message(chat_id, "Не удалось завершить проверку из-за внутренней ошибки сервера.")
        finally:
            self.user_states.pop(chat_id, None)

    def run(self) -> None:
        logger.info("Бот FraudGuard AI запущен. Ожидаю сообщений...")
        self.bot.infinity_polling()


if __name__ == "__main__":
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8886674211:AAFVinbilsy8L36OPTBrPwn_TltEGpZxPlc")
    
    db = DatabaseClient()
    logger.info("DatabaseClient инициализирован (демо-режим, БД не используется)")
    
    engine = FraudEngine(db=db)
    bot_app = FraudGuardBot(token=BOT_TOKEN, engine=engine)
    bot_app.run()
