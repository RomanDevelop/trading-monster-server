from fastapi import APIRouter
from app.api.routes import tickers, signals, portfolio

# Основной роутер
api_router = APIRouter()

# Включаем все роуты
api_router.include_router(tickers.router)
api_router.include_router(signals.router)
api_router.include_router(portfolio.router) 