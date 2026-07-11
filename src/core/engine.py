import logging
from typing import Any, Dict
from src.database.db_client import DatabaseClient
from src.core.checkers import BlacklistHandler, LimitHandler, FrequencyHandler, GraphHandler, AIChecker
from src.core.ai_processor import KodikAIProcessor

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
        
        # Добавляем AI-чеккер
        ai_processor = KodikAIProcessor()
        ai_handler = AIChecker(ai_processor)

        # Собираем цепочку: Blacklist → Limit → Frequency → Graph → AI
        blacklist_handler.set_next(limit_handler).set_next(frequency_handler).set_next(graph_handler).set_next(ai_handler)
        
        self.entry_point = blacklist_handler

    def check_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        # Проверка структуры входящих данных
        if not transaction_data or not isinstance(transaction_data, dict):
            return {"approved": False, "reason": "Нет данных транзакции или неверный формат"}
        
        # Прогон по цепочке валидаторов
        result = self.entry_point.handle(transaction_data)
        
        # Сохранение в БД отключено для демо-версии (база не требуется)
        
        return result
