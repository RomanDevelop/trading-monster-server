from pydantic import BaseModel
from typing import List, Dict, Optional, Any, Literal
from datetime import datetime


# Definition of possible analysis model types
AnalysisModelType = Literal["RSI_MODEL", "MACD_MODEL", "BOLLINGER_MODEL"]


class TickerRequest(BaseModel):
    ticker: str
    model_type: AnalysisModelType = "RSI_MODEL"  # Using RSI model by default


class SignalResponse(BaseModel):
    id: str  # Unique signal ID
    ticker: str
    signal: str  # "long" or "short"
    message: str
    open: float
    close: float
    change_percent: float
    eps_growth: float
    timestamp: str
    status: str = "pending"  # "pending", "confirmed", "rejected"
    model_type: AnalysisModelType  # Type of model that generated the signal


class SignalConfirmation(BaseModel):
    signal_id: str
    action: str  # "confirm" or "reject"
    quantity: Optional[float] = None


class PositionOpen(BaseModel):
    ticker: str
    signal_type: str  # "long" or "short"
    price: float
    quantity: float


class PositionClose(BaseModel):
    close_price: float


class PortfolioStatus(BaseModel):
    balance: float
    positions: List[Dict[str, Any]]


class Signal(BaseModel):
    """Signal model for internal use"""
    id: str
    ticker: str
    signal: str
    message: str
    open: float
    close: float
    change_percent: float
    eps_growth: float
    timestamp: str
    status: str = "pending"
    quantity: Optional[float] = None
    model_type: AnalysisModelType  # Type of model that generated the signal

    def to_dict(self) -> dict:
        return self.dict()

    @classmethod
    def from_dict(cls, data: dict) -> "Signal":
        return cls(**data)


class Position(BaseModel):
    """Position model for internal use"""
    ticker: str
    signal_type: str
    price: float
    quantity: float
    open_timestamp: str
    current_price: float
    pnl: float
    status: str = "open"
    close_price: Optional[float] = None
    close_timestamp: Optional[str] = None
    model_type: AnalysisModelType  # Type of model that was used to open the position

    def to_dict(self) -> dict:
        return self.dict()

    @classmethod
    def from_dict(cls, data: dict) -> "Position":
        return cls(**data)


class WatchlistItem(BaseModel):
    """Watchlist item with analysis model type"""
    ticker: str
    model_type: AnalysisModelType

    def to_dict(self) -> dict:
        return self.dict()

    @classmethod
    def from_dict(cls, data: dict) -> "WatchlistItem":
        return cls(**data) 