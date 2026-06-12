import logging
from typing import Any, Dict
from src.database.db_client import DatabaseClient
from src.core.checkers import BlacklistHandler, LimitHandler, FrequencyHandler, GraphHandler

logger = logging.getLogger("FraudEngine")

class FraudEngine:
    def __init__(self, db: DatabaseClient, limit: float = 50000.0, 
                 window_size: int = 60, max_count: int = 3, graph_threshold: int = 5):
        self.db = db
        
        # Сборка цепочки обязанностей (Chain of Responsibility)
        blacklist_handler = BlacklistHandler(db=self.db)
        limit_handler = LimitHandler(limit=limit)
        frequency_handler = FrequencyHandler(db=self.db, window_size=window_size, max_count=max_count)
        graph_handler = GraphHandler(db=self.db, threshold=graph_threshold)

        blacklist_handler.set_next(limit_handler).set_next(frequency_handler).set_next(graph_handler)
        
        self.entry_point = blacklist_handler

    def check_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        # Проверка структуры входящих данных
        if not transaction_data or not isinstance(transaction_data, dict):
            return {"approved": False, "reason": "Нет данных транзакции или неверный формат"}
        
        # Прогон по цепочке валидаторов
        result = self.entry_point.handle(transaction_data)
        
        # Безопасное логирование транзакции в PostgreSQL
        try:
            self.db.save_transaction(
                tx_data=transaction_data,
                is_approved=result["approved"],
                reason=result["reason"]
            )
        except Exception as e:
            logger.error(f"Критическая ошибка сохранения транзакции в БД: {e}", exc_info=True)
        
        return result
