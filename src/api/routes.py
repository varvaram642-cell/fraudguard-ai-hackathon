import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from src.database.db_client import DatabaseClient
from src.core.engine import FraudEngine
from src.api.main import get_db_client, get_fraud_engine

logger = logging.getLogger("APIRoutes")

router = APIRouter(prefix="/api/v1", tags=["Fraud Detection"])

@router.post(
    "/transactions/check",
    summary="Проверить транзакцию на предмет фрода",
    response_model=Dict[str, Any]
)
async def check_transaction(
    transaction_data: Dict[str, Any],
    engine: FraudEngine = Depends(get_fraud_engine)
) -> Dict[str, Any]:
    logger.info(f"Получен запрос на проверку транзакции: {transaction_data}")
    try:
        result = engine.check_transaction(transaction_data)
        return result
    except Exception as e:
        logger.error(f"Ошибка при проверке транзакции: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера при проверке транзакции.")

@router.get(
    "/analytics/stats",
    summary="Получить общую статистику по транзакциям",
    response_model=Dict[str, Any]
)
async def get_stats(db: DatabaseClient = Depends(get_db_client)) -> Dict[str, Any]:
    logger.info("Получен запрос на получение статистики.")
    try:
        with db.conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*), 
                       SUM(CASE WHEN is_approved = FALSE THEN 1 ELSE 0 END) 
                FROM transactions
            """)
            total, fraud = cur.fetchone()
            return {"total_transactions": total, "fraud_count": fraud if fraud is not None else 0}
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера при получении статистики.")

@router.post(
    "/admin/blacklist/add",
    summary="Добавить сущность в черный список",
    status_code=200,
    response_model=Dict[str, str]
)
async def add_to_blacklist(
    entity_data: Dict[str, str],
    db: DatabaseClient = Depends(get_db_client)
) -> Dict[str, str]:
    entity_type = entity_data.get("entity_type")
    entity_value = entity_data.get("entity_value")
    reason = entity_data.get("reason", "Добавлено администратором вручную")

    if not entity_type or not entity_value:
        raise HTTPException(status_code=400, detail="Требуются 'entity_type' и 'entity_value'")
    
    try:
        db.add_to_blacklist(entity_type, entity_value, reason)
        logger.info(f"{entity_type} '{entity_value}' добавлен в черный список.")
        return {"message": f"{entity_type} '{entity_value}' успешно добавлен в черный список."}
    except Exception as e:
        logger.error(f"Ошибка при добавлении в черный список: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера при добавлении в черный список.")
