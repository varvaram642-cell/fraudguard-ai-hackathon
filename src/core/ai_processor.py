import os
import random

class KodikAIProcessor:
    def __init__(self):
        self.api_endpoint = os.getenv("KODIK_ROUTER_API_URL", "https://api.kodikrouter.com/v1/chat/completions") 
        self.api_key = os.getenv("KODIK_API_KEY") 
        print("INFO: KodikAIProcessor запущен в ДЕМО-режиме (без внешних API-запросов).")

    def analyze(self, transaction_data: dict) -> dict:
        amount = transaction_data.get("amount", 0)
        card_hash = transaction_data.get("card_hash", "").lower()
        telegram_id = str(transaction_data.get("telegram_id", ""))
        
        if amount >= 75000:
            return {
                "approved": False, 
                "reason": "AI (ДЕМО-режим): Транзакция превышает установленный AI-лимит для данного профиля риска.", 
                "risk_level": "HIGH_RISK"
            }
        
        if "fraud_test" in card_hash or telegram_id == "999999999":
            reasons_fraud = [
                "AI (ДЕМО-режим): Обнаружен паттерн, связанный с известной мошеннической активностью по карте.",
                "AI (ДЕМО-режим): Высокий риск: аккаунт связан с подозрительными операциями.",
                "AI (ДЕМО-режим): Необычное поведение пользователя для данной суммы."
            ]
            return {
                "approved": False, 
                "reason": random.choice(reasons_fraud), 
                "risk_level": "HIGH_RISK"
            }
        
        if amount <= 500 and "safe_card" in card_hash:
            return {
                "approved": True, 
                "reason": "AI (ДЕМО-режим): Транзакция с низким риском, одобрена.", 
                "risk_level": "LOW_RISK"
            }

        if random.random() < 0.85:
            reasons_approved = [
                "AI (ДЕМО-режим): Транзакция проверена, риск низкий.",
                "AI (ДЕМО-режим): Платеж одобрен, аномалий не обнаружено.",
                "AI (ДЕМО-режим): Системный анализ не выявил угроз."
            ]
            return {
                "approved": True, 
                "reason": random.choice(reasons_approved), 
                "risk_level": "LOW_RISK"
            }
        else:
            reasons_default_risk = [
                "AI (ДЕМО-режим): Незначительные аномалии, рекомендовано к ручной проверке.",
                "AI (ДЕМО-режим): Выявлена неопределенность в паттерне транзакции, риск средний.",
                "AI (ДЕМО-режим): Отклонено из-за совокупности факторов риска."
            ]
            return {
                "approved": False, 
                "reason": random.choice(reasons_default_risk), 
                "risk_level": "MEDIUM_RISK"
            }
