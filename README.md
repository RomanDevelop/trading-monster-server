# ⚙️ Trading Signal Backend (FastAPI)

This backend server monitors stock tickers, generates AI-based trading signals, and communicates with a mobile Flutter client.

## 🔧 Tech Stack

- **FastAPI** – modern async Python web framework
- **yFinance** – for fetching real-time market data
- **SQLite** – for storing signal history
- **CORS Middleware** – enables frontend-backend connection
- **Threading** – for background monitoring

## 🚀 Getting Started

1. Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```
