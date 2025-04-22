import os
from typing import List
from pydantic import BaseModel


class Settings(BaseModel):
    """Application settings"""
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Trading Signal API"
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # Analysis settings
    MONITORING_INTERVAL: int = 300  # Seconds
    RETRY_ATTEMPTS: int = 3
    RETRY_DELAY: int = 2  # Seconds
    
    # Portfolio settings
    INITIAL_BALANCE: float = 175000.0
    PORTFOLIO_DATA_FILE: str = "portfolio_data.json"
    
    # Environment settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"


settings = Settings() 