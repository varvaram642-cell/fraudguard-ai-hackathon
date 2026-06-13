import os
import logging
import telebot
from telebot import types
from typing import Dict, Any

from src.database.db_client import DatabaseClient
from src.core.engine import FraudEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FraudGuardBot")

class FraudGuardBot:
    def __init__(self, token: str, engine: FraudEngine):
        self.bot = telebot.TeleBot(token)
        self.engine = engine
        self.user_states: Dict[int, Dict[str, Any]] = {}
        self._register_handlers()

    def _register_handlers(self):
        self.bot.register_message_handler(self.send_welcome, commands=['start', 'help'])
        self.bot.register_message_handler(self.handle_report_command, commands=['report'])
        self.bot.register_callback_query_handler(self.handle_callbacks, func=lambda call: True)

    def send_welcome(self, message: types.Message):
        welcome_text = (
            "🛡️ **Добро пожаловать в FraudGuard AI!**\n\n"
            "Я интеллектуальный бот-помощник для детекции мошеннических транзакций.\n\n"
            "📌 **Доступные команды:**\n"
            "• `/report @username` — пожаловаться на пользователя\n"
            "• `/start` — главное меню\n\n"
            "Выберите нужное действие ниже:"
        )
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_check = types.InlineKeyboardButton("🔍 Проверить транзакцию", callback_data="check_tx")
        btn_info = types.InlineKeyboardButton("ℹ️ О системе антифрода", callback_data="system_info")
        markup.add(btn_check, btn_info)
        
        self.bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=markup)

    def handle_report_command(self, message: types.Message):
        args = message.text.split()
        if len(args) < 2:
            self.bot.reply_to(message, "❌ Укажите username. Пример: `/report @ivan`", parse_mode="Markdown")
            return
        
        username = args[1].lstrip("@")
        transaction_data = {
            "amount": 10000.0,
            "card_hash": f"card_{username}",
            "telegram_id": message.from_user.id
        }
        
        self.bot.reply_to(message, f"🔍 Проверяю пользователя @{username}...")
        
        try:
            result = self.engine.check_transaction(transaction_data)
            if result["approved"]:
                self.bot.send_message(message.chat.id, f"✅ Жалоба на @{username} проверена. Подозрительной активности не обнаружено.")
            else:
                self.bot.send_message(message.chat.id, f"🚨 **Жалоба подтверждена!**\n⚠️ @{username} идентифицирован как фрод.\nПричина: {result['reason']}")
        except Exception as e:
            logger.error(f"Ошибка проверки: {e}")
            self.bot.send_message(message.chat.id, "❌ Произошла ошибка при проверке жалобы.")

    def handle_callbacks(self, call: types.CallbackQuery):
        if call.data == "check_tx":
            self.bot.answer_callback_query(call.id)
            msg = self.bot.send_message(call.message.chat.id, "💰 Введите сумму транзакции (число):")
            self.bot.register_next_step_handler(msg, self.process_amount_step)
        elif call.data == "system_info":
            self.bot.answer_callback_query(call.id)
            info_text = (
                "⚙️ **Как работает защита:**\n"
                "1. **Анализ лимитов:** Блокировка разовых переводов выше нормы.\n"
                "2. **Скользящее окно:** Отслеживание аномально частых транзакций.\n"
                "3. **Графовый анализ:** Выявление связей карты с множеством аккаунтов.\n"
                "4. **Черный список:** Глобальная блокировка карт и пользователей."
            )
            self.bot.send_message(call.message.chat.id, info_text, parse_mode="Markdown")

    def process_amount_step(self, message: types.Message):
        try:
            amount = float(message.text)
            self.user_states[message.chat.id] = {"amount": amount}
            msg = self.bot.send_message(message.chat.id, "💳 Введите хэш карты (например: card_123):")
            self.bot.register_next_step_handler(msg, self.process_card_step)
        except ValueError:
            msg = self.bot.send_message(message.chat.id, "❌ Ошибка: Введите числовое значение суммы!")
            self.bot.register_next_step_handler(msg, self.process_amount_step)

    def process_card_step(self, message: types.Message):
        card_hash = message.text.strip() if message.text else ""
        if not card_hash:
            msg = self.bot.send_message(message.chat.id, "❌ Карта не может быть пустой. Попробуйте еще раз:")
            self.bot.register_next_step_handler(msg, self.process_card_step)
            return
        
        if message.chat.id not in self.user_states:
            self.bot.send_message(message.chat.id, "❌ Время сессии истекло. Начните сначала: /start")
            return
        
        self.user_states[message.chat.id]["card_hash"] = card_hash
        self.user_states[message.chat.id]["telegram_id"] = message.from_user.id
        self.execute_fraud_check(message.chat.id)

    def execute_fraud_check(self, chat_id: int):
        data = self.user_states.get(chat_id)
        if not data:
            self.bot.send_message(chat_id, "❌ Ошибка сессии. Начните сначала: /start")
            return
        
        self.bot.send_message(chat_id, "🔄 Запущен скоринг транзакции в системе безопасности...")
        
        try:
            result = self.engine.check_transaction(data)
            if result["approved"]:
                response = f"✅ **ТРАНЗАКЦИЯ ОДОБРЕНА**\n\n💵 Сумма: {data['amount']:.2f} руб.\n💳 Карта: {data['card_hash']}\n🛡️ Безопасность: Угроз не обнаружено."
            else:
                response = f"🚨 **ВНИМАНИЕ: ОБНАРУЖЕН ФРОД!**\n\n💵 Сумма: {data['amount']:.2f} руб.\n💳 Карта: {data['card_hash']}\n⚠️ Причина блокировки: {result['reason']}"
            
            self.bot.send_message(chat_id, response, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка скоринга: {e}")
            self.bot.send_message(chat_id, "❌ Не удалось завершить проверку.")
        finally:
            self.user_states.pop(chat_id, None)

    def run(self):
        logger.info("Бот FraudGuard AI запущен.")
        self.bot.infinity_polling()


if __name__ == "__main__":
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8886674211:AAFVinbilsy8L36OPTBrPwn_TltEGpZxPlc")
    
    db = DatabaseClient()
    db.initialize_schema()
    
    engine = FraudEngine(db=db)
    bot = FraudGuardBot(token=BOT_TOKEN, engine=engine)
    bot.run()
