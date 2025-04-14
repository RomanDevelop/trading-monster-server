from fastapi import APIRouter, HTTPException
from typing import List
from app.db import repository
from app.models.schemas import TickerRequest

router = APIRouter(prefix="/tickers", tags=["tickers"])


@router.post("")
async def monitor_ticker(request: TickerRequest):
    """Добавить тикер в список наблюдения"""
    ticker = request.ticker.upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")
    
    repository.add_ticker(ticker)
    return {"message": f"{ticker} added to watchlist"}


@router.delete("/{ticker}")
async def remove_ticker(ticker: str):
    """Удалить тикер из списка наблюдения"""
    ticker = ticker.upper()
    if repository.remove_ticker(ticker):
        return {"message": f"{ticker} removed from watchlist"}
    
    raise HTTPException(status_code=404, detail="Ticker not found in watchlist")


@router.get("", response_model=List[str])
async def get_watchlist():
    """Получить список всех отслеживаемых тикеров"""
    return repository.get_watchlist() 