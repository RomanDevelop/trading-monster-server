from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from datetime import datetime
from app.db import repository
from app.models.schemas import TickerRequest, WatchlistItemDetails, SignalProximity
from app.services.analysis_models import AnalysisModelFactory

router = APIRouter(prefix="/tickers", tags=["tickers"])


@router.post("")
async def monitor_ticker(request: TickerRequest):
    """Add ticker to watchlist with the selected analysis model"""
    ticker = request.ticker.upper()
    model_type = request.model_type
    
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")
    
    repository.add_ticker(ticker, model_type)
    return {
        "message": f"{ticker} added to watchlist with {model_type} analysis model",
        "ticker": ticker,
        "model_type": model_type
    }


@router.delete("/{ticker}")
async def remove_ticker(ticker: str):
    """Remove ticker from watchlist"""
    ticker = ticker.upper()
    if repository.remove_ticker(ticker):
        return {"message": f"{ticker} removed from watchlist"}
    
    raise HTTPException(status_code=404, detail="Ticker not found in watchlist")


@router.get("", response_model=List[str])
async def get_watchlist():
    """Get list of all monitored tickers"""
    return repository.get_watchlist()


@router.get("/with_models", response_model=List[Dict[str, Any]])
async def get_watchlist_with_models():
    """Get list of all monitored tickers with analysis model information"""
    return repository.get_watchlist_with_models()


@router.get("/details", response_model=List[WatchlistItemDetails])
async def get_watchlist_details():
    """
    Get detailed information about watchlist tickers, including signal proximity
    
    Returns information about how close each ticker is to generating a signal based
    on its assigned analysis model
    """
    watchlist_with_models = repository.get_watchlist_with_models()
    result = []
    
    for item in watchlist_with_models:
        ticker = item["ticker"]
        model_type = item["model_type"]
        
        # Get the appropriate analysis model
        model = AnalysisModelFactory.create_model(model_type)
        
        # Calculate signal proximity
        proximity, description = model.get_signal_proximity(ticker)
        
        # Create watchlist item details
        item_details = WatchlistItemDetails(
            ticker=ticker,
            model_type=model_type,
            proximity=proximity,
            description=description,
            updated_at=datetime.now().isoformat()
        )
        
        result.append(item_details)
    
    return result


@router.get("/{ticker}/signal_proximity", response_model=SignalProximity)
async def get_ticker_signal_proximity(ticker: str):
    """
    Get information about how close a specific ticker is to generating a signal
    """
    ticker = ticker.upper()
    watchlist = repository.get_watchlist_with_models()
    
    # Find the ticker in the watchlist
    ticker_info = next((item for item in watchlist if item["ticker"] == ticker), None)
    
    if not ticker_info:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found in watchlist")
    
    model_type = ticker_info["model_type"]
    
    # Get the appropriate analysis model
    model = AnalysisModelFactory.create_model(model_type)
    
    # Calculate signal proximity
    proximity, description = model.get_signal_proximity(ticker)
    
    # Create signal proximity info
    signal_proximity = SignalProximity(
        ticker=ticker,
        model_type=model_type,
        proximity=proximity,
        description=description,
        updated_at=datetime.now().isoformat()
    )
    
    return signal_proximity


@router.get("/models")
async def get_available_models():
    """Получить список доступных моделей анализа"""
    return [
        {
            "id": "RSI_MODEL",
            "name": "RSI Model",
            "description": "Relative Strength Index (RSI) model analyzes overbought/oversold stock prices"
        },
        {
            "id": "MACD_MODEL",
            "name": "MACD Model",
            "description": "Moving Average Convergence Divergence (MACD) model analyzes trends and turning points"
        },
        {
            "id": "BOLLINGER_MODEL",
            "name": "Bollinger Bands Model",
            "description": "Bollinger Bands model analyzes volatility and potential breakout points from price range boundaries"
        }
    ] 