import os
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger("KodikAIProcessor")

class KodikAIProcessor:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, 
                 ai_model: str = "gpt-3.5-turbo", timeout: int = 30):
        self.api_key = api_key or os.getenv("KODIK_API_KEY")
        self.base_url = base_url or os.getenv("KODIK_API_URL", "https://api.kodik.ai/v1/chat/completions")
        self.ai_model = ai_model
        self.timeout = timeout
        self.enabled = bool(self.api_key)
        
        if not self.enabled:
            logger.warning("KODIK_API_KEY не установлен. AI-анализ будет пропущен.")

    def _build_prompt(self, transaction_data: Dict[str, Any]) -> str:
        amount = transaction_data.get("amount", 0.0)
        card_hash = transaction_data.get("card_hash", "неизвестно")
        telegram_id = transaction_data.get("telegram_id", "неизвестен")
        
        prompt = (
            f"Оцени риск мошенничества для следующей финансовой транзакции:\n"
            f"- Сумма: {amount} руб.\n"
            f"- Карта (хэш): {card_hash}\n"
            f"- Пользователь (Telegram ID): {telegram_id}\n"
            f"Ожидаемый ответ: 'HIGH_RISK_FRAUD' если риск высокий, 'LOW_RISK' если низкий, "
            f"'MODERATE_RISK' если средний. Укажи краткую причину. "
            f"Пример: 'HIGH_RISK_FRAUD: Нетипичная сумма для пользователя.'"
        )
        return prompt

    def _send_request(self, prompt: str) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
            
        payload = {
            "model": self.ai_model,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(self.base_url, json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"AI API request failed: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Неизвестная ошибка при запросе к AI API: {e}", exc_info=True)
            return None

    def _parse_response(self, response_json: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not response_json or not self.enabled:
            return {"approved": True, "reason": "AI-анализ не выполнен (отключен/нет ответа)", "risk_level": "UNKNOWN"}
        
        try:
            content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
            content_lower = content.lower()
            risk_level = "LOW_RISK"
            
            if "high_risk" in content_lower or "мошенничество" in content_lower or "фрод" in content_lower:
                risk_level = "HIGH_RISK"
            elif "moderate_risk" in content_lower:
                risk_level = "MODERATE_RISK"
            
            approved = True if risk_level == "LOW_RISK" else False
            reason = f"AI: {content.strip()[:150]}"
            
            return {"approved": approved, "reason": reason, "risk_level": risk_level}
        except Exception as e:
            logger.error(f"Ошибка парсинга AI ответа: {e}", exc_info=True)
            return {"approved": True, "reason": "AI ответ не распознан (ошибка парсинга)", "risk_level": "UNKNOWN"}

    def analyze(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled:
            return {"approved": True, "reason": "AI отключён", "risk_level": "DISABLED"}
            
        prompt = self._build_prompt(transaction_data)
        response = self._send_request(prompt)
        result = self._parse_response(response)
        logger.info(f"AI анализ транзакции: {transaction_data.get('card_hash')} -> {result['risk_level']}")
        return result
