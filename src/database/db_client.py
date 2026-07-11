import logging

logger = logging.getLogger("DatabaseClient")

class DatabaseClient:
    def __init__(self):
        logger.info("DatabaseClient запущен в демо-режиме (без подключения к БД)")
        self.conn = None

    def is_blacklisted(self, entity_type: str, value: str) -> bool:
        return False

    def get_recent_transactions_count(self, card_hash: str, window_seconds: int) -> int:
        return 0

    def get_unique_users_count_for_card(self, card_hash: str) -> int:
        return 1

    def save_transaction(self, tx_data, is_approved, reason):
        pass

    def close(self):
        pass
