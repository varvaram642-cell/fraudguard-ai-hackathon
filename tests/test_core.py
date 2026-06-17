import pytest
from unittest.mock import Mock, MagicMock
from src.core.checkers import BlacklistHandler, LimitHandler, FrequencyHandler, GraphHandler, AIChecker
from src.core.engine import FraudEngine
from src.database.db_client import DatabaseClient
from src.core.ai_processor import KodikAIProcessor


@pytest.fixture
def mock_db_client():
    mock = Mock(spec=DatabaseClient)
    mock.is_blacklisted.return_value = False
    mock.get_recent_transactions_count.return_value = 0
    mock.get_unique_users_count_for_card.return_value = 1
    mock.save_transaction.return_value = None
    return mock

@pytest.fixture
def mock_ai_processor():
    mock = Mock(spec=KodikAIProcessor)
    mock.analyze.return_value = {"approved": True, "reason": "AI: Low Risk", "risk_level": "LOW_RISK"}
    return mock


class TestLimitHandler:
    def test_limit_approved(self):
        handler = LimitHandler(limit=50000)
        tx = {"amount": 10000}
        result = handler.handle(tx)
        assert result["approved"] is True

    def test_limit_rejected(self):
        handler = LimitHandler(limit=50000)
        tx = {"amount": 60000}
        result = handler.handle(tx)
        assert result["approved"] is False
        assert "превышен" in result["reason"].lower()

    def test_limit_edge_case(self):
        handler = LimitHandler(limit=50000)
        tx = {"amount": 50000}
        result = handler.handle(tx)
        assert result["approved"] is True


class TestBlacklistHandler:
    def test_blacklist_approved_no_match(self, mock_db_client):
        mock_db_client.is_blacklisted.side_effect = [False, False]
        handler = BlacklistHandler(db=mock_db_client)
        tx = {"card_hash": "card_bl_ok", "telegram_id": 123}
        result = handler.handle(tx)
        assert result["approved"] is True
        mock_db_client.is_blacklisted.assert_any_call("card", "card_bl_ok")
        mock_db_client.is_blacklisted.assert_any_call("user", "123")

    def test_blacklist_rejected_card(self, mock_db_client):
        mock_db_client.is_blacklisted.return_value = True
        handler = BlacklistHandler(db=mock_db_client)
        tx = {"card_hash": "card_bl_bad", "telegram_id": 123}
        result = handler.handle(tx)
        assert result["approved"] is False
        assert "черном списке" in result["reason"].lower()

    def test_blacklist_rejected_user(self, mock_db_client):
        mock_db_client.is_blacklisted.side_effect = [False, True]
        handler = BlacklistHandler(db=mock_db_client)
        tx = {"card_hash": "card_bl_ok", "telegram_id": 456}
        result = handler.handle(tx)
        assert result["approved"] is False
        assert "черном списке" in result["reason"].lower()


class TestFrequencyHandler:
    def test_frequency_approved_first_tx(self, mock_db_client):
        mock_db_client.get_recent_transactions_count.return_value = 0
        handler = FrequencyHandler(db=mock_db_client, window_size=10, max_count=3)
        tx = {"card_hash": "card_freq_ok"}
        result = handler.handle(tx)
        assert result["approved"] is True

    def test_frequency_approved_below_threshold(self, mock_db_client):
        mock_db_client.get_recent_transactions_count.return_value = 2
        handler = FrequencyHandler(db=mock_db_client, window_size=10, max_count=3)
        tx = {"card_hash": "card_freq_ok_2"}
        result = handler.handle(tx)
        assert result["approved"] is True

    def test_frequency_rejected_at_threshold(self, mock_db_client):
        mock_db_client.get_recent_transactions_count.return_value = 3
        handler = FrequencyHandler(db=mock_db_client, window_size=10, max_count=3)
        tx = {"card_hash": "card_freq_bad"}
        result = handler.handle(tx)
        assert result["approved"] is False
        assert "аномальная частота" in result["reason"].lower()


class TestGraphHandler:
    def test_graph_approved_below_threshold(self, mock_db_client):
        mock_db_client.get_unique_users_count_for_card.return_value = 2
        handler = GraphHandler(db=mock_db_client, threshold=5)
        tx = {"card_hash": "card_graph_ok"}
        result = handler.handle(tx)
        assert result["approved"] is True

    def test_graph_rejected_at_threshold(self, mock_db_client):
        mock_db_client.get_unique_users_count_for_card.return_value = 5
        handler = GraphHandler(db=mock_db_client, threshold=5)
        tx = {"card_hash": "card_graph_bad"}
        result = handler.handle(tx)
        assert result["approved"] is False
        assert "скомпрометирована" in result["reason"].lower()


class TestAIChecker:
    def test_ai_checker_approved(self, mock_ai_processor):
        handler = AIChecker(ai_processor=mock_ai_processor)
        tx = {"amount": 100, "card_hash": "card_ai_ok", "telegram_id": 111}
        result = handler.handle(tx)
        assert result["approved"] is True
        mock_ai_processor.analyze.assert_called_once_with(tx)

    def test_ai_checker_rejected(self, mock_ai_processor):
        mock_ai_processor.analyze.return_value = {"approved": False, "reason": "AI: High Risk", "risk_level": "HIGH_RISK"}
        handler = AIChecker(ai_processor=mock_ai_processor)
        tx = {"amount": 5000, "card_hash": "card_ai_bad", "telegram_id": 222}
        result = handler.handle(tx)
        assert result["approved"] is False
        assert "high risk" in result["reason"].lower()


class TestFraudEngine:
    def test_engine_approves_normal_tx(self, mock_db_client, mock_ai_processor):
        mock_db_client.is_blacklisted.return_value = False
        mock_db_client.get_recent_transactions_count.return_value = 0
        mock_db_client.get_unique_users_count_for_card.return_value = 1
        mock_ai_processor.analyze.return_value = {"approved": True, "reason": "AI: Low Risk", "risk_level": "LOW_RISK"}

        engine = FraudEngine(db=mock_db_client, ai_processor=mock_ai_processor,
                             limit=50000, window_size=10, max_count=3, graph_threshold=5)
        
        tx = {"amount": 10000, "card_hash": "card_engine_ok", "telegram_id": 111}
        result = engine.check_transaction(tx)
        
        assert result["approved"] is True
        mock_db_client.save_transaction.assert_called_once_with(
            tx_data=tx, is_approved=True, reason="Одобрено"
        )
        mock_ai_processor.analyze.assert_called_once_with(tx)

    def test_engine_rejects_limit_exceed(self, mock_db_client, mock_ai_processor):
        engine = FraudEngine(db=mock_db_client, ai_processor=mock_ai_processor,
                             limit=50000, window_size=10, max_count=3, graph_threshold=5)
        
        tx = {"amount": 100000, "card_hash": "card_engine_limit", "telegram_id": 222}
        result = engine.check_transaction(tx)
        
        assert result["approved"] is False
        assert "превышен" in result["reason"].lower()
        mock_db_client.save_transaction.assert_called_once_with(
            tx_data=tx, is_approved=False, reason=result["reason"]
        )
        mock_ai_processor.analyze.assert_not_called()

    def test_engine_rejects_blacklist(self, mock_db_client, mock_ai_processor):
        mock_db_client.is_blacklisted.return_value = True
        engine = FraudEngine(db=mock_db_client, ai_processor=mock_ai_processor,
                             limit=50000, window_size=10, max_count=3, graph_threshold=5)
        
        tx = {"amount": 1000, "card_hash": "card_engine_bl", "telegram_id": 333}
        result = engine.check_transaction(tx)
        
        assert result["approved"] is False
        assert "черном списке" in result["reason"].lower()
        mock_db_client.save_transaction.assert_called_once_with(
            tx_data=tx, is_approved=False, reason=result["reason"]
        )
        mock_ai_processor.analyze.assert_not_called()

    def test_engine_ai_rejects_tx(self, mock_db_client, mock_ai_processor):
        mock_db_client.is_blacklisted.return_value = False
        mock_db_client.get_recent_transactions_count.return_value = 0
        mock_db_client.get_unique_users_count_for_card.return_value = 1
        mock_ai_processor.analyze.return_value = {"approved": False, "reason": "AI: Suspicious pattern", "risk_level": "HIGH_RISK"}

        engine = FraudEngine(db=mock_db_client, ai_processor=mock_ai_processor,
                             limit=50000, window_size=10, max_count=3, graph_threshold=5)
        
        tx = {"amount": 1000, "card_hash": "card_engine_ai_fail", "telegram_id": 444}
        result = engine.check_transaction(tx)
        
        assert result["approved"] is False
        assert "suspicious pattern" in result["reason"].lower()
        mock_db_client.save_transaction.assert_called_once_with(
            tx_data=tx, is_approved=False, reason=result["reason"]
        )
        mock_ai_processor.analyze.assert_called_once_with(tx)
