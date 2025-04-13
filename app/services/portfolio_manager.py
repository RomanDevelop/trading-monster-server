from typing import Dict, Any, Tuple, Optional
from datetime import datetime
from app.db import repository
from app.models.schemas import Position
from app.services.stock_analyzer import stock_analyzer


class PortfolioManager:
    """Сервис для управления портфелем и позициями"""
    
    def calculate_pnl(self, position: Dict[str, Any], current_price: float) -> float:
        """Расчет прибыли/убытка для позиции"""
        if position["signal_type"].lower() == "long":
            return (current_price - position["price"]) * position["quantity"]
        else:  # short
            return (position["price"] - current_price) * position["quantity"]
    
    def open_position(self, ticker: str, signal_type: str, price: float, quantity: float) -> Tuple[bool, str, Dict[str, Any]]:
        """Открытие новой позиции и обновление баланса"""
        ticker = ticker.upper()
        current_balance = repository.get_balance()
        
        # Вычисляем стоимость позиции
        position_value = price * quantity
        
        # Проверяем хватает ли денег для LONG позиции
        if signal_type.lower() == "long" and position_value > current_balance:
            return False, "Insufficient balance", {}
        
        # Создаем новую позицию
        position = Position(
            ticker=ticker,
            signal_type=signal_type,
            price=price,
            quantity=quantity,
            open_timestamp=datetime.now().isoformat(),
            current_price=price,
            pnl=0.0
        )
        
        # Для LONG вычитаем сумму из баланса
        if signal_type.lower() == "long":
            new_balance = current_balance - position_value
            repository.update_balance(new_balance)
            print(f"LONG position opened: Balance before={current_balance}, after={new_balance}")
        else:
            print(f"SHORT position opened: Balance remains {current_balance}")
        
        # Сохраняем позицию
        repository.add_position(position)
        
        return True, "Position opened successfully", position.to_dict()
    
    def close_position(self, ticker: str, close_price: float) -> Tuple[bool, str, Dict[str, Any]]:
        """Закрытие позиции и обновление баланса"""
        ticker = ticker.upper()
        position = repository.get_position(ticker)
        
        if not position:
            return False, "Position not found", {}
        
        # Расчет P&L
        pnl = self.calculate_pnl(position, close_price)
        current_balance = repository.get_balance()
        
        # Обновление баланса
        if position["signal_type"].lower() == "long":
            # Для LONG: возвращаем инвестиции + P&L
            closing_amount = close_price * position["quantity"]
            new_balance = current_balance + closing_amount
            repository.update_balance(new_balance)
            print(f"LONG position closed: Balance before={current_balance}, after={new_balance}, P&L={pnl}")
        else:
            # Для SHORT: только P&L
            new_balance = current_balance + pnl
            repository.update_balance(new_balance)
            print(f"SHORT position closed: Balance before={current_balance}, after={new_balance}, P&L={pnl}")
        
        # Обновляем информацию о закрытой позиции
        closed_position = {
            **position,
            "close_price": close_price,
            "close_timestamp": datetime.now().isoformat(),
            "pnl": pnl,
            "status": "closed"
        }
        
        # Обновляем позицию в истории и удаляем из открытых
        repository.update_position(ticker, closed_position)
        repository.remove_position(ticker)
        
        return True, "Position closed successfully", closed_position
    
    def update_positions_prices(self) -> None:
        """Обновление текущих цен для всех открытых позиций"""
        positions = repository.get_positions()
        
        for position in positions:
            ticker = position["ticker"]
            current_price = stock_analyzer.get_current_price(ticker)
            
            if current_price is not None:
                pnl = self.calculate_pnl(position, current_price)
                
                # Обновляем позицию
                updated_data = {
                    "current_price": current_price,
                    "pnl": pnl,
                    "updated_at": datetime.now().isoformat()
                }
                
                repository.update_position(ticker, updated_data)
    
    def reset_portfolio(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Сброс портфеля к начальному состоянию"""
        repository.reset_portfolio()
        
        return True, "Portfolio reset successfully", {
            "balance": repository.get_balance(),
            "positions": []
        }


# Создаем экземпляр сервиса
portfolio_manager = PortfolioManager() 