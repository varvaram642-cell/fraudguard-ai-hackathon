# FraudGuard AI 🛡️

**Интеллектуальная система защиты от мошеннических платежей в Telegram**

---

## 📋 Описание

FraudGuard AI — это автоматизированная система для выявления и блокировки мошеннических транзакций в Telegram-коммерции. Проект разработан в рамках хакатона **Kodik Launchpad 2026**.

Система анализирует транзакции в реальном времени через многоуровневую цепочку проверок и помогает защитить бизнес и пользователей от финансовых потерь.

---

## ⚙️ Возможности

- 🤖 **Telegram-бот** для проверки транзакций и приёма жалоб
- 🔍 **Многоуровневая цепочка проверок:**
  - Лимиты сумм
  - Частота платежей (скользящее окно)
  - Графовый анализ связей карт и аккаунтов
  - AI-скоринг через Kodik AI
- 📊 **Веб-дашборд** (Streamlit) для мониторинга статистики
- 🚫 **Чёрный список** карт и пользователей
- 🐳 **Docker-контейнеризация** для лёгкого развёртывания

---

## 🛠️ Технологии

| Компонент | Технология |
|-----------|-----------|
| **Язык** | Python 3.11 |
| **API** | FastAPI |
| **База данных** | PostgreSQL / SQLite |
| **Бот** | Telegram Bot API (telebot) |
| **AI** | Kodik AI (заглушка для демо) |
| **Дашборд** | Streamlit |
| **Тестирование** | pytest, unittest.mock |
| **Контейнеризация** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions |
| **Деплой** | Render |

## 🚀 Запуск проекта FraudGuard AI

Через Docker (рекомендуется)

```bash
git clone https://github.com/varvaram642-cell/fraudguard-ai-hackathon.git
cd fraudguard-ai-hackathon
docker-compose up --build
```

После запуска:

· API: http://localhost:8000/docs
· Дашборд: http://localhost:8501

---

Локально (без Docker)

```bash
git clone https://github.com/varvaram642-cell/fraudguard-ai-hackathon.git
cd fraudguard-ai-hackathon
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # Windows: copy .env.example .env
python -m src.bot.telegram_bot
```

---

✅ Проверка

· Бот: @FraudGuardAIBot
· Демо: https://fraudguard-ai-hackathon.onrender.com
