from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from src.database.db_client import DatabaseClient

class AbstractHandler(ABC):
    _next_handler: Optional['AbstractHandler'] = None

    def set_next(self, handler: 'AbstractHandler') -> 'AbstractHandler':
        self._next_handler = handler
        return handler

    @abstractmethod
    def handle(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    def _pass_to_next(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        if self._next_handler:
            return self._next_handler.handle(transaction_data)
        return {"approved": True, "reason": "Одобрено"}


class BlacklistHandler(AbstractHandler):
    def __init__(self, db: DatabaseClient):
        self.db = db

    def handle(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        card_hash = transaction_data.get("card_hash")
        telegram_id = str(transaction_data.get("telegram_id"))

        if card_hash and self.db.is_blacklisted("card", card_hash):
            return {"approved": False, "reason": "Карта находится в черном списке."}

        if telegram_id and self.db.is_blacklisted("user", telegram_id):
            return {"approved": False, "reason": "Пользователь находится в черном списке."}

        return self._pass_to_next(transaction_data)


class LimitHandler(AbstractHandler):
    def __init__(self, limit: float = 50000.0):
        self.limit = limit

    def handle(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        amount = transaction_data.get("amount", 0.0)
        if amount > self.limit:
            return {"approved": False, "reason": f"Превышен разовый лимит ({amount} > {self.limit})."}
        return self._pass_to_next(transaction_data)


class FrequencyHandler(AbstractHandler):
    def __init__(self, db: DatabaseClient, window_size: int = 60, max_count: int = 3):
        self.db = db
        self.window_size = window_size
        self.max_count = max_count

    def handle(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        card_hash = transaction_data.get("card_hash")
        if not card_hash:
            return self._pass_to_next(transaction_data)

        recent_count = self.db.get_recent_transactions_count(card_hash, self.window_size)
        if recent_count >= self.max_count:
            return {
                "approved": False, 
                "reason": f"Аномальная частота запросов: {recent_count + 1} транзакций за {self.window_size} сек."
            }

        return self._pass_to_next(transaction_data)


class GraphHandler(AbstractHandler):
    def __init__(self, db: DatabaseClient, threshold: int = 5):
        self.db = db
        self.threshold = threshold

    def handle(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        card_hash = transaction_data.get("card_hash")
        if not card_hash:
            return self._pass_to_next(transaction_data)

        unique_users = self.db.get_unique_users_count_for_card(card_hash)
        if unique_users > self.threshold:
            return {
                "approved": False, 
                "reason": f"Карта скомпрометирована (привязана к {unique_users} уникальным аккаунтам)."
            }

        return self._pass_to_next(transaction_data)
