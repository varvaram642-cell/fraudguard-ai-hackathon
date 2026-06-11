CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS blacklisted_entities (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_value VARCHAR(255) NOT NULL UNIQUE,
    reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    amount NUMERIC(12, 2) NOT NULL,
    card_hash VARCHAR(255) NOT NULL,
    telegram_id BIGINT NOT NULL,
    is_approved BOOLEAN NOT NULL,
    fraud_reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transactions_card_hash_time 
ON transactions(card_hash, created_at);

CREATE INDEX IF NOT EXISTS idx_transactions_card_hash_user 
ON transactions(card_hash, telegram_id);

CREATE INDEX IF NOT EXISTS idx_blacklist_value 
ON blacklisted_entities(entity_value);
"""
