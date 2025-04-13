import os
from typing import List
from pydantic import BaseModel


class Settings(BaseModel):
    """Настройки приложения"""
    # API настройки
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Trading Signal API"
    
    # CORS настройки
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # Настройки анализа
    MONITORING_INTERVAL: int = 300  # Секунды
    RETRY_ATTEMPTS: int = 3
    RETRY_DELAY: int = 2  # Секунды
    
    # Настройки портфеля
    INITIAL_BALANCE: float = 1000.0
    
    # Настройки среды
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"


settings = Settings() 