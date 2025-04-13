from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime


class TickerRequest(BaseModel):
    ticker: str


class SignalResponse(BaseModel):
    id: str  # Уникальный ID сигнала
    ticker: str
    signal: str  # "long" или "short"
    message: str
    open: float
    close: float
    change_percent: float
    eps_growth: float
    timestamp: str
    status: str = "pending"  # "pending", "confirmed", "rejected"


class SignalConfirmation(BaseModel):
    signal_id: str
    action: str  # "confirm" или "reject"
    quantity: Optional[float] = None


class PositionOpen(BaseModel):
    ticker: str
    signal_type: str  # "long" или "short"
    price: float
    quantity: float


class PositionClose(BaseModel):
    close_price: float


class PortfolioStatus(BaseModel):
    balance: float
    positions: List[Dict[str, Any]]


class Signal(BaseModel):
    """Модель сигнала для внутреннего использования"""
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

    def to_dict(self) -> dict:
        return self.dict()

    @classmethod
    def from_dict(cls, data: dict) -> "Signal":
        return cls(**data)


class Position(BaseModel):
    """Модель позиции для внутреннего использования"""
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

    def to_dict(self) -> dict:
        return self.dict()

    @classmethod
    def from_dict(cls, data: dict) -> "Position":
        return cls(**data) 