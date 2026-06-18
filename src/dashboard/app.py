import streamlit as st
import requests
import pandas as pd
import time
import json 
import os # <-- Импортируем os

# Конфигурация API
# Используем os.getenv для гибкой настройки базового URL API
# В Docker Compose это будет "http://api:8000/api/v1" (через переменную окружения)
# Локально (вне Docker) это будет "http://localhost:8000/api/v1"
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(layout="wide", page_title="FintechGuard AI Dashboard")

st.sidebar.title("Навигация")
page = st.sidebar.radio("Перейти к", ["Обзор и статистика", "Проверка транзакций", "Управление черным списком"])

# --- Вспомогательные функции для API-запросов ---
@st.cache_data(ttl=5) # Кэшируем данные на 5 секунд
def get_dashboard_stats():
    try:
        response = requests.get(f"{API_BASE_URL}/analytics/stats")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Ошибка получения статистики: {e}")
        return None

def check_transaction_api(transaction_data):
    try:
        response = requests.post(f"{API_BASE_URL}/transactions/check", json=transaction_data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Ошибка проверки транзакции: {e}")
        return None

def add_to_blacklist_api(entity_type, entity_value, reason):
    try:
        payload = {"entity_type": entity_type, "entity_value": entity_value, "reason": reason}
        response = requests.post(f"{API_BASE_URL}/admin/blacklist/add", json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Ошибка добавления в черный список: {e}")
        return None

# --- Страница "Обзор и статистика" ---
if page == "Обзор и статистика":
    st.title("🛡️ Обзор системы FintechGuard AI")
    st.markdown("### Метрики антифрода")

    stats = get_dashboard_stats()

    if stats:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Всего транзакций", stats.get("total_transactions", 0))
        with col2:
            st.metric("Фродовых транзакций", stats.get("fraud_count", 0))
        with col3:
            if stats.get("total_transactions", 0) > 0:
                fraud_rate = (stats.get("fraud_count", 0) / stats.get("total_transactions", 0)) * 100
                st.metric("Процент фрода", f"{fraud_rate:.2f}%")
            else:
                st.metric("Процент фрода", "0.00%")

        st.markdown("---")
        st.subheader("Последние транзакции (из БД)")
        st.info("Для более детального анализа последних транзакций необходимо добавить соответствующий эндпоинт в API.")

    else:
        st.warning("Не удалось загрузить статистику. Убедитесь, что FastAPI-сервер запущен.")

# --- Страница "Проверка транзакций" ---
elif page == "Проверка транзакций":
    st.title("🔍 Проверка новой транзакции")
    st.markdown("Введите данные для проверки транзакции в реальном времени.")

    with st.form("transaction_form"):
        amount = st.number_input("Сумма транзакции", min_value=1.0, value=1000.0, step=100.0)
        card_hash = st.text_input("Хэш карты (например: card_123)", value="card_test_123")
        telegram_id = st.number_input("Telegram ID пользователя", min_value=1, value=123456789)
        
        submitted = st.form_submit_button("Проверить транзакцию")

        if submitted:
            transaction_data = {
                "amount": amount,
                "card_hash": card_hash,
                "telegram_id": telegram_id
            }
            st.info("Отправка транзакции на проверку...")
            
            result = check_transaction_api(transaction_data)
            
            if result:
                st.subheader("Результат проверки:")
                if result["approved"]:
                    st.success(f"✅ **ТРАНЗАКЦИЯ ОДОБРЕНА**")
                    st.write(f"**Причина:** {result.get('reason', 'Угроз не обнаружено.')}")
                    st.write(f"**Уровень риска:** {result.get('risk_level', 'LOW_RISK')}")
                else:
                    st.error(f"🚨 **ТРАНЗАКЦИЯ ОТКЛОНЕНА**")
                    st.write(f"**Причина:** {result.get('reason', 'Фрод обнаружен.')}")
                    st.write(f"**Уровень риска:** {result.get('risk_level', 'HIGH_RISK')}")
                
                st.markdown("---")
                st.json(result)
            else:
                st.error("Не удалось получить результат проверки от API.")

# --- Страница "Управление черным списком" ---
elif page == "Управление черным списком":
    st.title("🚫 Управление черным списком")
    st.markdown("Добавьте карту или пользователя в черный список.")

    with st.form("blacklist_form"):
        entity_type = st.radio("Тип сущности", ["card", "user"])
        entity_value = st.text_input("Значение (хэш карты или Telegram ID)", value="")
        reason = st.text_area("Причина добавления", value="Подозрительная активность")
        
        submitted_blacklist = st.form_submit_button("Добавить в черный список")

        if submitted_blacklist:
            if not entity_value:
                st.error("Значение сущности не может быть пустым.")
            else:
                st.info(f"Добавление {entity_type} '{entity_value}' в черный список...")
                result = add_to_blacklist_api(entity_type, entity_value, reason)
                
                if result:
                    st.success(f"✅ Успешно: {result.get('message', 'Сущность добавлена.')}")
                    st.json(result)
                else:
                    st.error("Не удалось добавить сущность в черный список.")
