from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import yfinance as yf
import time
from app.db import repository
from app.models.schemas import Position
from app.core.config import settings


class PortfolioManager:
    """Service for portfolio and position management"""
    
    def calculate_pnl(self, position: Dict[str, Any], current_price: float) -> float:
        """Calculate profit/loss for a position"""
        if position["signal_type"].lower() == "long":
            return (current_price - position["price"]) * position["quantity"]
        else:  # short
            return (position["price"] - current_price) * position["quantity"]
    
    def open_position(self, ticker: str, signal_type: str, price: float, quantity: float, model_type: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Open a new position and update balance"""
        ticker = ticker.upper()
        current_balance = repository.get_balance()
        
        # Calculate position value
        position_value = price * quantity
        
        # Check if there's enough balance for LONG position
        if signal_type.lower() == "long" and position_value > current_balance:
            return False, "Insufficient balance", {}
        
        # Check if there's enough balance for SHORT position
        if signal_type.lower() == "short" and position_value > current_balance:
            return False, "Insufficient balance", {}
        
        # Create new position
        position = Position(
            ticker=ticker,
            signal_type=signal_type,
            price=price,
            quantity=quantity,
            open_timestamp=datetime.now().isoformat(),
            current_price=price,
            pnl=0.0,
            model_type=model_type
        )
        
        # Subtract position value from balance for both position types
        new_balance = current_balance - position_value
        repository.update_balance(new_balance)
        
        if signal_type.lower() == "long":
            print(f"LONG position opened: Balance before={current_balance}, after={new_balance}")
        else:
            print(f"SHORT position opened: Balance before={current_balance}, after={new_balance}")
        
        # Save position
        repository.add_position(position)
        
        return True, "Position opened successfully", position.to_dict()
    
    def close_position(self, ticker: str, close_price: float) -> Tuple[bool, str, Dict[str, Any]]:
        """Close position and update balance"""
        ticker = ticker.upper()
        position = repository.get_position(ticker)
        
        if not position:
            return False, "Position not found", {}
        
        # Calculate P&L
        pnl = self.calculate_pnl(position, close_price)
        current_balance = repository.get_balance()
        
        # Calculate initial investment
        initial_investment = position["price"] * position["quantity"]
        
        # Update balance
        if position["signal_type"].lower() == "long":
            # For LONG: return investment + P&L
            closing_amount = close_price * position["quantity"]
            new_balance = current_balance + closing_amount
            repository.update_balance(new_balance)
            print(f"LONG position closed: Balance before={current_balance}, after={new_balance}, P&L={pnl}")
        else:
            # For SHORT: return investment + P&L
            new_balance = current_balance + initial_investment + pnl
            repository.update_balance(new_balance)
            print(f"SHORT position closed: Balance before={current_balance}, after={new_balance}, P&L={pnl}")
        
        # Update closed position information
        closed_position = {
            **position,
            "close_price": close_price,
            "close_timestamp": datetime.now().isoformat(),
            "pnl": pnl,
            "status": "closed"
        }
        
        # Update position in history and remove from open positions
        repository.update_position(ticker, closed_position)
        repository.remove_position(ticker)
        
        return True, "Position closed successfully", closed_position
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """Get current stock price"""
        try:
            stock = yf.Ticker(ticker)
            
            # Multiple attempts to get data
            max_attempts = settings.RETRY_ATTEMPTS
            hist = None
            
            for attempt in range(max_attempts):
                try:
                    hist = stock.history(period="1d", interval="1m", timeout=15)
                    if not hist.empty:
                        break
                except Exception as e:
                    if attempt == max_attempts - 1:
                        print(f"Failed to get price for {ticker} after {max_attempts} attempts: {e}")
                        return None
                    time.sleep(settings.RETRY_DELAY)
            
            if hist is not None and not hist.empty:
                return hist.iloc[-1]['Close']
            
            return None
        except Exception as e:
            print(f"Error getting price for {ticker}: {e}")
            return None
    
    def update_positions_prices(self) -> None:
        """Update current prices for all open positions"""
        positions = repository.get_positions()
        
        for position in positions:
            ticker = position["ticker"]
            current_price = self.get_current_price(ticker)
            
            if current_price is not None:
                pnl = self.calculate_pnl(position, current_price)
                
                # Update position
                updated_data = {
                    "current_price": current_price,
                    "pnl": pnl,
                    "updated_at": datetime.now().isoformat()
                }
                
                repository.update_position(ticker, updated_data)
    
    def reset_portfolio(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Reset portfolio to initial state"""
        repository.reset_portfolio()
        
        return True, "Portfolio reset successfully", {
            "balance": repository.get_balance(),
            "positions": []
        }


# Create service instance
portfolio_manager = PortfolioManager() 