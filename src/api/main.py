import logging
import os
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI
from src.api.routes import router
from src.database.db_client import DatabaseClient
from src.core.engine import FraudEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("FastAPIApp")

db_client_instance: Optional[DatabaseClient] = None
fraud_engine_instance: Optional[FraudEngine] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_client_instance, fraud_engine_instance
    
    logger.info("Запуск FastAPI-приложения: Инициализация ресурсов...")
    
    try:
        db_client_instance = DatabaseClient()
        db_client_instance.initialize_schema()
        logger.info("DatabaseClient и схема БД успешно инициализированы.")
        
        fraud_engine_instance = FraudEngine(db=db_client_instance)
        logger.info("FraudEngine успешно инициализирован.")
        
        yield
        
    except Exception as e:
        logger.critical(f"Критическая ошибка при старте FastAPI: {e}", exc_info=True)
        raise RuntimeError(f"Не удалось запустить FastAPI-приложение: {e}")
    finally:
        if db_client_instance:
            db_client_instance.close()
            logger.info("Соединение DatabaseClient закрыто.")
        logger.info("FastAPI-приложение завершило работу.")

app = FastAPI(title="FraudGuard AI API", version="1.0.0", lifespan=lifespan)

app.include_router(router)

@app.get("/", summary="Корневой эндпоинт API")
async def root():
    return {"message": "FraudGuard AI API is running. Visit /docs for OpenAPI specification."}
