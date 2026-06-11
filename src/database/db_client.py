import os
import logging
import psycopg2
from typing import Dict, Any, Optional, Set

logger = logging.getLogger("DatabaseClient")

class DatabaseClient:
    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or os.getenv(
            "DATABASE_URL", 
            "postgresql://postgres:postgres@localhost:5432/fraud_guard"
        )
        self.conn = None
        self._connect()

    def _connect(self) -> None:
        try:
            self.conn = psycopg2.connect(self.dsn)
            self.conn.autocommit = True
            logger.info("Успешное подключение к PostgreSQL.")
        except Exception as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            raise e

    def initialize_schema(self) -> None:
        from .models import CREATE_TABLES_SQL
        with self.conn.cursor() as cursor:
            cursor.execute(CREATE_TABLES_SQL)
            logger.info("Схема БД успешно инициализирована.")

    def is_blacklisted(self, entity_type: str, value: str) -> bool:
        query = """
            SELECT EXISTS(
                SELECT 1 FROM blacklisted_entities 
                WHERE entity_type = %s AND entity_value = %s
            );
        """
        with self.conn.cursor() as cursor:
            cursor.execute(query, (entity_type, value))
            return cursor.fetchone()[0]

    def get_recent_transactions_count(self, card_hash: str, window_seconds: int) -> int:
        query = """
            SELECT COUNT(*) FROM transactions
            WHERE card_hash = %s 
              AND created_at >= NOW() - (%s * INTERVAL '1 second')
              AND is_approved = TRUE;
        """
        with self.conn.cursor() as cursor:
            cursor.execute(query, (card_hash, window_seconds))
            return cursor.fetchone()[0]

    def get_unique_users_count_for_card(self, card_hash: str) -> int:
        query = """
            SELECT COUNT(DISTINCT telegram_id) FROM transactions
            WHERE card_hash = %s;
        """
        with self.conn.cursor() as cursor:
            cursor.execute(query, (card_hash,))
            return cursor.fetchone()[0]

    def get_linked_users_by_card(self, card_hash: str) -> Set[int]:
        query = """
            SELECT DISTINCT telegram_id FROM transactions
            WHERE card_hash = %s;
        """
        with self.conn.cursor() as cursor:
            cursor.execute(query, (card_hash,))
            return {row[0] for row in cursor.fetchall()}

    def save_transaction(self, tx_data: Dict[str, Any], is_approved: bool, reason: str) -> None:
        query = """
            INSERT INTO transactions (amount, card_hash, telegram_id, is_approved, fraud_reason)
            VALUES (%s, %s, %s, %s, %s);
        """
        with self.conn.cursor() as cursor:
            cursor.execute(query, (
                tx_data["amount"],
                tx_data["card_hash"],
                tx_data["telegram_id"],
                is_approved,
                reason
            ))

    def add_to_blacklist(self, entity_type: str, value: str, reason: str) -> None:
        query = """
            INSERT INTO blacklisted_entities (entity_type, entity_value, reason)
            VALUES (%s, %s, %s)
            ON CONFLICT (entity_value) DO NOTHING;
        """
        with self.conn.cursor() as cursor:
            cursor.execute(query, (entity_type, value, reason))

    def close(self) -> None:
        if self.conn:
            self.conn.close()
