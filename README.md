# ⚙️ Trading Signal Backend (FastAPI)

Это бэкенд-сервер для мониторинга тикеров акций, генерации торговых сигналов на основе AI и коммуникации с мобильным Flutter клиентом.

## 🔧 Технологический стек

- **FastAPI** – современный асинхронный веб-фреймворк на Python
- **yFinance** – для получения данных с рынка в реальном времени
- **Pydantic** – для валидации данных и моделей
- **CORS Middleware** – для соединения с фронтендом
- **Threading** – для фонового мониторинга

## 🏗️ Архитектура проекта

Проект следует принципам чистой архитектуры и SOLID:

```
app/
├── api/                    # API слой
│   ├── routes/             # Маршруты API
│   │   ├── tickers.py      # Эндпоинты для тикеров
│   │   ├── signals.py      # Эндпоинты для сигналов
│   │   └── portfolio.py    # Эндпоинты для портфеля
├── core/                   # Ядро приложения
│   └── config.py           # Настройки приложения
├── db/                     # Слой доступа к данным
│   └── repository.py       # Хранилище данных с абстрактным интерфейсом
├── models/                 # Модели данных
│   └── schemas.py          # Схемы Pydantic
├── services/               # Бизнес-логика
│   ├── stock_analyzer.py   # Анализ акций
│   ├── portfolio_manager.py # Управление портфелем
│   └── monitoring.py       # Фоновый мониторинг
└── main.py                 # Точка входа приложения
```

## 🚀 Начало работы

1. Создайте виртуальное окружение:

```bash
python3 -m venv venv
source venv/bin/activate  # На Linux/Mac
# или
venv\Scripts\activate  # На Windows
```

2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Запустите сервер:

```bash
python main.py
```

Сервер будет доступен по адресу http://localhost:8000

## 📚 API Документация

После запуска сервера документация доступна по адресу:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 Основные эндпоинты

- **GET /api/v1/tickers** - получить список отслеживаемых тикеров
- **POST /api/v1/tickers** - добавить тикер в список
- **GET /api/v1/signals** - получить активные сигналы
- **POST /api/v1/signals/confirm** - подтвердить или отклонить сигнал
- **GET /api/v1/portfolio/positions** - получить открытые позиции
- **POST /api/v1/portfolio/positions/close/{ticker}** - закрыть позицию

## 🛠️ Варианты запуска сервера

Есть два способа запустить сервер:

### Способ 1: Через Python (рекомендуется)

```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Запустите сервер
python main.py
```

### Способ 2: Напрямую через Uvicorn

```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Запустите сервер через uvicorn, указав путь к приложению
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

**Обратите внимание:** В отличие от старой версии, теперь запуск осуществляется не через `uvicorn app:app`, а через `uvicorn app.main:app` из-за модульной структуры приложения.
