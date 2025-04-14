from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.db import repository
from app.models.schemas import SignalConfirmation
from app.services.portfolio_manager import portfolio_manager

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=List[dict])
async def get_signals():
    """Получить все активные сигналы"""
    return repository.get_signals()


@router.get("/{ticker}", response_model=List[dict])
async def get_signals_by_ticker(ticker: str):
    """Получить все сигналы по тикеру"""
    return repository.get_signals_by_ticker(ticker.upper())


@router.post("/confirm")
async def confirm_signal(confirmation: SignalConfirmation):
    """Подтвердить или отклонить сигнал"""
    signal_id = confirmation.signal_id
    action = confirmation.action
    quantity = confirmation.quantity
    
    # Находим сигнал по ID
    signal = repository.get_signal_by_id(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    # Обновляем статус сигнала
    if action == "confirm":
        # Обновляем сигнал
        repository.update_signal(signal_id, {"status": "confirmed"})
        
        if quantity:
            # Обновляем количество в сигнале
            repository.update_signal(signal_id, {"quantity": quantity})
            
            # Создаем позицию при подтверждении сигнала
            ticker = signal["ticker"]
            price = signal["close"]
            signal_type = signal["signal"]
            
            # Открываем позицию
            success, message, position = portfolio_manager.open_position(
                ticker=ticker,
                signal_type=signal_type,
                price=price,
                quantity=quantity
            )
            
            if not success:
                raise HTTPException(status_code=400, detail=message)
            
            return {
                "message": f"Signal {signal_id} confirmed successfully",
                "balance": repository.get_balance(),
                "positions": repository.get_positions()
            }
        
        return {"message": f"Signal {signal_id} confirmed successfully"}
    
    elif action == "reject":
        repository.update_signal(signal_id, {"status": "rejected"})
        return {"message": f"Signal {signal_id} rejected successfully"}
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action")


@router.get("/history", response_model=List[dict])
async def get_signal_history():
    """Получить историю всех сигналов"""
    # Обновленная логика: возвращаем историю сигналов из репозитория
    # Если история пуста, но есть активные сигналы, добавляем их в историю
    signal_history = repository.get_signal_history()
    
    # Если история пуста, но есть активные сигналы, добавляем их в историю
    if not signal_history:
        active_signals = repository.get_signals()
        signal_history = active_signals  # Используем активные сигналы как историю
    
    return signal_history 