from abc import ABC, abstractmethod
from typing import List, Dict, Any, Set, Optional
from app.models.schemas import Signal, Position


class AbstractRepository(ABC):
    """Абстрактный интерфейс для репозитория данных"""
    
    @abstractmethod
    def add_ticker(self, ticker: str) -> None:
        pass
    
    @abstractmethod
    def remove_ticker(self, ticker: str) -> bool:
        pass
    
    @abstractmethod
    def get_watchlist(self) -> List[str]:
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


class InMemoryRepository(AbstractRepository):
    """Реализация репозитория в памяти"""
    
    def __init__(self, initial_balance: float = 1000.0):
        self._watchlist: Set[str] = set()
        self._signals_by_ticker: Dict[str, List[Dict[str, Any]]] = {}
        self._active_signals: List[Dict[str, Any]] = []
        self._signal_history: List[Dict[str, Any]] = []
        self._balance: float = initial_balance
        self._open_positions: Dict[str, Dict[str, Any]] = {}
        self._position_history: List[Dict[str, Any]] = []
    
    def add_ticker(self, ticker: str) -> None:
        self._watchlist.add(ticker.upper())
    
    def remove_ticker(self, ticker: str) -> bool:
        ticker = ticker.upper()
        if ticker in self._watchlist:
            self._watchlist.remove(ticker)
            return True
        return False
    
    def get_watchlist(self) -> List[str]:
        return list(self._watchlist)
    
    def add_signal(self, signal: Signal) -> None:
        signal_dict = signal.to_dict()
        ticker = signal.ticker
        
        # Добавляем в историю всех сигналов
        self._signal_history.append(signal_dict)
        
        # Проверяем, есть ли сигналы для данного тикера
        if ticker not in self._signals_by_ticker:
            self._signals_by_ticker[ticker] = []
        
        # Проверяем, не был ли этот сигнал уже отправлен (по времени и типу)
        add_signal = True
        if self._signals_by_ticker[ticker]:
            last_signal = self._signals_by_ticker[ticker][-1]
            last_time = last_signal["timestamp"]
            current_time = signal_dict["timestamp"]
            # Если последний сигнал того же типа и прошло менее 30 минут, игнорируем
            if last_signal["signal"] == signal_dict["signal"] and \
               (current_time - last_time).total_seconds() < 1800:
                add_signal = False
        
        if add_signal:
            self._signals_by_ticker[ticker].append(signal_dict)
            self._active_signals.append(signal_dict)
    
    def get_signals(self) -> List[Dict[str, Any]]:
        # Возвращаем только активные (pending) сигналы
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
        
        # Обновление в active_signals
        for i, s in enumerate(self._active_signals):
            if s["id"] == signal_id:
                self._active_signals[i].update(data)
                break
        
        # Обновление в signals_by_ticker
        ticker = signal["ticker"]
        if ticker in self._signals_by_ticker:
            for i, s in enumerate(self._signals_by_ticker[ticker]):
                if s["id"] == signal_id:
                    self._signals_by_ticker[ticker][i].update(data)
                    break
        
        # Обновление в history
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
    
    def add_position(self, position: Position) -> None:
        position_dict = position.to_dict()
        ticker = position.ticker
        self._open_positions[ticker] = position_dict
        self._position_history.append(position_dict)
    
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
        
        # Обновляем также в истории позиций
        for i, pos in enumerate(self._position_history):
            if pos["ticker"] == ticker and pos["status"] == "open":
                self._position_history[i].update(data)
                break
        
        return True
    
    def remove_position(self, ticker: str) -> bool:
        ticker = ticker.upper()
        if ticker not in self._open_positions:
            return False
        
        del self._open_positions[ticker]
        return True
    
    def get_position_history(self) -> List[Dict[str, Any]]:
        return self._position_history
    
    def reset_portfolio(self) -> None:
        from app.core.config import settings
        
        self._balance = settings.INITIAL_BALANCE
        
        # Помечаем все позиции как закрытые
        for ticker, position in self._open_positions.items():
            from datetime import datetime
            self._position_history.append({
                **position,
                "close_timestamp": datetime.now().isoformat(),
                "status": "closed_by_reset"
            })
        
        self._open_positions = {} 