from abc import ABC, abstractmethod
from typing import List, Dict, Any, Set, Optional, Tuple
import os
import json
from datetime import datetime
from app.models.schemas import Signal, Position, WatchlistItem, AnalysisModelType
from app.core.config import settings


class AbstractRepository(ABC):
    """Abstract interface for data repository"""
    
    @abstractmethod
    def add_ticker(self, ticker: str, model_type: AnalysisModelType) -> None:
        pass
    
    @abstractmethod
    def remove_ticker(self, ticker: str) -> bool:
        pass
    
    @abstractmethod
    def get_watchlist(self) -> List[str]:
        pass
    
    @abstractmethod
    def get_watchlist_with_models(self) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def get_ticker_model(self, ticker: str) -> Optional[AnalysisModelType]:
        pass
    
    @abstractmethod
    def add_signal(self, signal: Signal) -> None:
        pass
    
    @abstractmethod
    def get_signals(self) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def get_signals_by_ticker(self, ticker: str) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def get_signal_by_id(self, signal_id: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def update_signal(self, signal_id: str, data: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    def get_signal_history(self) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def get_balance(self) -> float:
        pass
    
    @abstractmethod
    def update_balance(self, new_balance: float) -> None:
        pass
    
    @abstractmethod
    def add_position(self, position: Position) -> None:
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def get_position(self, ticker: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def update_position(self, ticker: str, data: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    def remove_position(self, ticker: str) -> bool:
        pass
    
    @abstractmethod
    def get_position_history(self) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def reset_portfolio(self) -> None:
        pass
    
    @abstractmethod
    def save_portfolio_data(self) -> bool:
        """Save portfolio data to a file"""
        pass
    
    @abstractmethod
    def load_portfolio_data(self) -> bool:
        """Load portfolio data from a file"""
        pass


class InMemoryRepository(AbstractRepository):
    """In-memory repository implementation"""
    
    def __init__(self, initial_balance: float = 5000.0):
        # Instead of a simple set of tickers, we use a dictionary {ticker: model_type}
        self._watchlist: Dict[str, AnalysisModelType] = {}
        self._signals_by_ticker: Dict[str, List[Dict[str, Any]]] = {}
        self._active_signals: List[Dict[str, Any]] = []
        self._signal_history: List[Dict[str, Any]] = []
        self._balance: float = initial_balance
        self._open_positions: Dict[str, Dict[str, Any]] = {}
        self._position_history: List[Dict[str, Any]] = []
        
        # Try to load data from file if it exists
        self.load_portfolio_data()
    
    def add_ticker(self, ticker: str, model_type: AnalysisModelType) -> None:
        """Add ticker to watchlist with specified analysis model"""
        self._watchlist[ticker.upper()] = model_type
        # Save portfolio data after adding a ticker
        self.save_portfolio_data()
    
    def remove_ticker(self, ticker: str) -> bool:
        """Remove ticker from watchlist"""
        ticker = ticker.upper()
        if ticker in self._watchlist:
            del self._watchlist[ticker]
            # Save portfolio data after removing a ticker
            self.save_portfolio_data()
            return True
        return False
    
    def get_watchlist(self) -> List[str]:
        """Return list of tickers without analysis model information"""
        return list(self._watchlist.keys())
    
    def get_watchlist_with_models(self) -> List[Dict[str, Any]]:
        """Return list of tickers with analysis model information"""
        return [
            {"ticker": ticker, "model_type": model_type}
            for ticker, model_type in self._watchlist.items()
        ]
    
    def get_ticker_model(self, ticker: str) -> Optional[AnalysisModelType]:
        """Return analysis model type for the specified ticker"""
        ticker = ticker.upper()
        return self._watchlist.get(ticker)
    
    def add_signal(self, signal: Signal) -> None:
        signal_dict = signal.to_dict()
        ticker = signal.ticker
        
        # Add to history of all signals
        self._signal_history.append(signal_dict)
        
        # Check if there are signals for this ticker
        if ticker not in self._signals_by_ticker:
            self._signals_by_ticker[ticker] = []
        
        # Check if this signal has already been sent (by time and type)
        add_signal = True
        if self._signals_by_ticker[ticker]:
            last_signal = self._signals_by_ticker[ticker][-1]
            last_time = last_signal["timestamp"]
            current_time = signal_dict["timestamp"]
            # If the last signal is of the same type and less than 30 minutes have passed, ignore
            if last_signal["signal"] == signal_dict["signal"] and \
               (current_time < last_time or abs(current_time.index(last_time)) < 1800):
                add_signal = False
        
        if add_signal:
            self._signals_by_ticker[ticker].append(signal_dict)
            self._active_signals.append(signal_dict)
    
    def get_signals(self) -> List[Dict[str, Any]]:
        # Return only active (pending) signals
        return [s for s in self._active_signals if s["status"] == "pending"]
    
    def get_signals_by_ticker(self, ticker: str) -> List[Dict[str, Any]]:
        ticker = ticker.upper()
        if ticker not in self._signals_by_ticker:
            return []
        return self._signals_by_ticker[ticker]
    
    def get_signal_by_id(self, signal_id: str) -> Optional[Dict[str, Any]]:
        for signal in self._active_signals:
            if signal["id"] == signal_id:
                return signal
        return None
    
    def update_signal(self, signal_id: str, data: Dict[str, Any]) -> bool:
        signal = self.get_signal_by_id(signal_id)
        if not signal:
            return False
        
        # Update in active_signals
        for i, s in enumerate(self._active_signals):
            if s["id"] == signal_id:
                self._active_signals[i].update(data)
                break
        
        # Update in signals_by_ticker
        ticker = signal["ticker"]
        if ticker in self._signals_by_ticker:
            for i, s in enumerate(self._signals_by_ticker[ticker]):
                if s["id"] == signal_id:
                    self._signals_by_ticker[ticker][i].update(data)
                    break
        
        # Update in history
        for i, s in enumerate(self._signal_history):
            if s["id"] == signal_id:
                self._signal_history[i].update(data)
                break
        
        return True
    
    def get_signal_history(self) -> List[Dict[str, Any]]:
        return self._signal_history
    
    def get_balance(self) -> float:
        return self._balance
    
    def update_balance(self, new_balance: float) -> None:
        self._balance = new_balance
        # Save portfolio data after balance update
        self.save_portfolio_data()
    
    def add_position(self, position: Position) -> None:
        position_dict = position.to_dict()
        ticker = position.ticker
        self._open_positions[ticker] = position_dict
        self._position_history.append(position_dict)
        # Save portfolio data after adding a position
        self.save_portfolio_data()
    
    def get_positions(self) -> List[Dict[str, Any]]:
        return list(self._open_positions.values())
    
    def get_position(self, ticker: str) -> Optional[Dict[str, Any]]:
        ticker = ticker.upper()
        return self._open_positions.get(ticker)
    
    def update_position(self, ticker: str, data: Dict[str, Any]) -> bool:
        ticker = ticker.upper()
        if ticker not in self._open_positions:
            return False
        
        self._open_positions[ticker].update(data)
        
        # Also update in position history
        for i, pos in enumerate(self._position_history):
            if pos["ticker"] == ticker and pos["status"] == "open":
                self._position_history[i].update(data)
                break
        
        # Save portfolio data after updating a position
        self.save_portfolio_data()
        return True
    
    def remove_position(self, ticker: str) -> bool:
        ticker = ticker.upper()
        if ticker not in self._open_positions:
            return False
        
        del self._open_positions[ticker]
        # Save portfolio data after removing a position
        self.save_portfolio_data()
        return True
    
    def get_position_history(self) -> List[Dict[str, Any]]:
        return self._position_history
    
    def reset_portfolio(self) -> None:
        from app.core.config import settings
        
        self._balance = settings.INITIAL_BALANCE
        
        # Mark all positions as closed
        for ticker, position in self._open_positions.items():
            from datetime import datetime
            self._position_history.append({
                **position,
                "close_timestamp": datetime.now().isoformat(),
                "status": "closed_by_reset"
            })
        
        self._open_positions = {}
        
        # Save portfolio data after reset
        self.save_portfolio_data()
    
    def save_portfolio_data(self) -> bool:
        """Save portfolio data to a file"""
        try:
            # Convert watchlist dictionary to a serializable format
            # since AnalysisModelType can't be directly serialized to JSON
            serializable_watchlist = {ticker: model_type for ticker, model_type in self._watchlist.items()}
            
            data = {
                "balance": self._balance,
                "open_positions": self._open_positions,
                "position_history": self._position_history,
                "watchlist": serializable_watchlist,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(settings.PORTFOLIO_DATA_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"Portfolio data saved to {settings.PORTFOLIO_DATA_FILE}")
            return True
        except Exception as e:
            print(f"Error saving portfolio data: {e}")
            return False
    
    def load_portfolio_data(self) -> bool:
        """Load portfolio data from a file"""
        try:
            if not os.path.exists(settings.PORTFOLIO_DATA_FILE):
                print(f"Portfolio data file {settings.PORTFOLIO_DATA_FILE} does not exist. Using default values.")
                return False
            
            with open(settings.PORTFOLIO_DATA_FILE, 'r') as f:
                data = json.load(f)
            
            self._balance = data.get("balance", settings.INITIAL_BALANCE)
            self._open_positions = data.get("open_positions", {})
            self._position_history = data.get("position_history", [])
            
            # Load watchlist if it exists in the data
            if "watchlist" in data:
                # Convert loaded watchlist data to dictionary of AnalysisModelType
                self._watchlist = data.get("watchlist", {})
                print(f"Loaded watchlist with {len(self._watchlist)} tickers")
            
            print(f"Portfolio data loaded from {settings.PORTFOLIO_DATA_FILE}")
            return True
        except Exception as e:
            print(f"Error loading portfolio data: {e}")
            return False 