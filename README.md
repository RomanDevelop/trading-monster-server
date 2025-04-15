# ⚙️ Trading Signal Backend (FastAPI)

This is a backend server for monitoring stock tickers, generating AI-based trading signals, and communicating with the mobile Flutter client.

## 🔧 Technology Stack

- **FastAPI** – modern asynchronous web framework for Python
- **yFinance** – for real-time market data retrieval
- **Pydantic** – for data validation and modeling
- **CORS Middleware** – for frontend connection
- **Threading** – for background monitoring
- **Pandas** – for data analysis and technical indicators
- **JSON** – for persistent portfolio data storage

## 🏗️ Project Architecture

The project follows clean architecture and SOLID principles:

```
app/
├── api/                    # API layer
│   ├── routes/             # API routes
│   │   ├── tickers.py      # Endpoints for tickers
│   │   ├── signals.py      # Endpoints for signals
│   │   └── portfolio.py    # Endpoints for portfolio
├── core/                   # Application core
│   └── config.py           # Application settings
├── db/                     # Data access layer
│   └── repository.py       # Data repository with abstract interface
├── models/                 # Data models
│   └── schemas.py          # Pydantic schemas
├── services/               # Business logic
│   ├── analysis_models.py  # Analysis models (RSI, MACD, Bollinger Bands)
│   ├── portfolio_manager.py # Portfolio management
│   └── monitoring.py       # Background monitoring
└── main.py                 # Application entry point
```

## 📊 Analysis Models and Indicators

The system supports several analysis models that can be selected when adding a ticker:

### 1. RSI Model

- **RSI (Relative Strength Index)** - used to determine overbought/oversold conditions
  - RSI > 70: indicates overbought condition (SHORT signal with negative outlook)
  - RSI < 30: indicates oversold condition (LONG signal with positive outlook)
- **Fundamental indicators** - earnings growth for assessing company financial health
- **Price dynamics** - analysis of price changes relative to opening price
  - Significant growth (>1.5%) with RSI < 50 can generate a LONG signal
  - Significant decline (<-1.5%) with RSI > 50 can generate a SHORT signal

### 2. MACD Model

- **MACD (Moving Average Convergence Divergence)** - trend and momentum indicator
  - MACD crosses signal line from below: indicates growing bullish trend (LONG signal)
  - MACD crosses signal line from above: indicates downward bearish trend (SHORT signal)
  - MACD above zero: market in bullish trend
  - MACD below zero: market in bearish trend
- **Fundamental indicators** - similar to RSI model
- **MACD histogram analysis** - for determining trend strength and direction

### 3. Bollinger Bands Model

- **Bollinger Bands** - volatility indicator using standard deviations around a moving average
  - Price near lower band: potential buying opportunity (LONG signal)
  - Price near upper band: potential selling opportunity (SHORT signal)
  - Band compression (low volatility): potential breakout signals

### Important Features

- Only one analysis model can be selected for each ticker
- After adding a ticker, the analysis model cannot be changed (need to delete and re-add the ticker)
- Each model has its own criteria for generating trading signals

## 💼 Portfolio Data Persistence

The application now features portfolio data persistence:

- **Automatic saving** - portfolio balance and positions are automatically saved to a file
- **Data retention** - positions remain open until explicitly closed by the user
- **Persistent storage** - all portfolio data is saved in JSON format (`portfolio_data.json`)
- **Automatic recovery** - data is loaded on application startup

This ensures that:

- Portfolio status is preserved between server restarts
- Open positions remain active until the user closes them
- Portfolio history is maintained for future analysis

## 🚀 Getting Started

1. Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the server:

```bash
python main.py
```

The server will be available at http://localhost:8000

## 📚 API Documentation

After starting the server, documentation is available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 Main Endpoints

### Tickers and Analysis Models

- **GET /api/v1/tickers** - get list of monitored tickers
- **POST /api/v1/tickers** - add ticker to list with selected analysis model
- **GET /api/v1/tickers/with_models** - get list of tickers with analysis model information
- **GET /api/v1/tickers/models** - get list of available analysis models with description

### Signals

- **GET /api/v1/signals** - get active signals
- **POST /api/v1/signals/confirm** - confirm or reject signal
- **GET /api/v1/signals/history** - get signal history

### Portfolio

- **GET /api/v1/portfolio/balance** - get current balance
- **GET /api/v1/portfolio/positions** - get open positions
- **POST /api/v1/portfolio/positions/close/{ticker}** - close position
- **GET /api/v1/portfolio/positions/history** - get position history
- **POST /api/v1/portfolio/reset** - reset portfolio to initial state

## 🛠️ Server Launch Options

There are two ways to start the server:

### Option 1: Through Python (recommended)

```bash
# Activate virtual environment
source venv/bin/activate

# Start the server
python main.py
```

### Option 2: Directly through Uvicorn

```bash
# Activate virtual environment
source venv/bin/activate

# Start the server through uvicorn, specifying the application path
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

**Note:** Unlike the old version, now the launch is done not through `uvicorn app:app`, but through `uvicorn app.main:app` due to the modular structure of the application.
