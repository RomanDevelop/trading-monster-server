from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.db import repository
from app.models.schemas import PositionClose
from app.services.portfolio_manager import portfolio_manager

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/balance")
def get_balance():
    """Получить текущий баланс"""
    return {"balance": repository.get_balance()}


@router.get("/positions")
def get_positions():
    """Получить список открытых позиций"""
    return {
        "positions": repository.get_positions(),
        "balance": repository.get_balance()
    }


@router.get("/positions/history")
def get_position_history():
    """Получить историю позиций"""
    return repository.get_position_history()


@router.post("/positions/close/{ticker}")
def close_position(ticker: str, position_close: PositionClose):
    """Закрыть позицию"""
    success, message, closed_position = portfolio_manager.close_position(
        ticker=ticker.upper(),
        close_price=position_close.close_price
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=message)
    
    return {
        "message": message,
        "closed_position": closed_position,
        "balance": repository.get_balance(),
        "pnl": closed_position.get("pnl", 0)
    }


@router.post("/reset")
def reset_portfolio():
    """Сбросить портфель к начальному состоянию"""
    success, message, data = portfolio_manager.reset_portfolio()
    
    return {
        "message": message,
        "balance": data["balance"],
        "positions": data["positions"]
    } 