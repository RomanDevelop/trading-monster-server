from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api import api_router
from app.core.config import settings
from app.services.monitoring import monitoring_service
from app.db import repository

# Import all necessary models for backward compatibility
from app.models.schemas import TickerRequest, SignalConfirmation, PositionClose


def create_application() -> FastAPI:
    """Create and configure FastAPI instance"""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        debug=settings.DEBUG
    )
    
    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    
    # Connect API routes
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # Event handlers for startup and shutdown
    @app.on_event("startup")
    def startup_event():
        """Start services when application starts"""
        monitoring_service.start()
    
    @app.on_event("shutdown")
    def shutdown_event():
        """Stop services when application shuts down"""
        monitoring_service.stop()

    # ============ BACKWARD COMPATIBILITY ROUTES ============
    # These routes maintain old API paths for the client,
    # but redirect requests to new handlers

    # Routes for tickers
    @app.post("/monitor")
    async def legacy_monitor_ticker(request: TickerRequest):
        """Backward compatibility for adding a ticker"""
        from app.api.routes.tickers import monitor_ticker
        return await monitor_ticker(request)

    @app.get("/watchlist")
    async def legacy_get_watchlist():
        """Backward compatibility for getting ticker list"""
        from app.api.routes.tickers import get_watchlist
        return await get_watchlist()

    @app.delete("/monitor/{ticker}")
    async def legacy_remove_ticker(ticker: str):
        """Backward compatibility for removing a ticker"""
        from app.api.routes.tickers import remove_ticker
        return await remove_ticker(ticker)

    # Add new routes for models
    @app.get("/models")
    async def legacy_get_models():
        """Backward compatibility for getting model list"""
        from app.api.routes.tickers import get_available_models
        return await get_available_models()

    @app.get("/watchlist/with_models")
    async def legacy_get_watchlist_with_models():
        """Backward compatibility for getting ticker list with models"""
        from app.api.routes.tickers import get_watchlist_with_models
        return await get_watchlist_with_models()

    # Routes for signals
    @app.get("/signals")
    async def legacy_get_signals():
        """Backward compatibility for getting signals"""
        from app.api.routes.signals import get_signals
        return await get_signals()

    @app.get("/signals/{ticker}")
    async def legacy_get_signals_by_ticker(ticker: str):
        """Backward compatibility for getting signals by ticker"""
        from app.api.routes.signals import get_signals_by_ticker
        return await get_signals_by_ticker(ticker)

    @app.get("/signals/history")
    async def legacy_get_signal_history():
        """Backward compatibility for getting signal history"""
        from app.api.routes.signals import get_signal_history
        return await get_signal_history()

    @app.post("/signals/confirm")
    async def legacy_confirm_signal(confirmation: SignalConfirmation):
        """Backward compatibility for confirming signals"""
        from app.api.routes.signals import confirm_signal
        return await confirm_signal(confirmation)

    # Routes for portfolio
    @app.get("/portfolio/balance")
    async def legacy_get_balance():
        """Backward compatibility for getting balance"""
        from app.api.routes.portfolio import get_balance
        return await get_balance()

    @app.get("/portfolio/positions")
    async def legacy_get_positions():
        """Backward compatibility for getting positions"""
        from app.api.routes.portfolio import get_positions
        return await get_positions()

    @app.get("/portfolio/positions/history")
    async def legacy_get_position_history():
        """Backward compatibility for getting position history"""
        from app.api.routes.portfolio import get_position_history
        return await get_position_history()

    @app.post("/portfolio/positions/close/{ticker}")
    async def legacy_close_position(ticker: str, position_close: PositionClose):
        """Backward compatibility for closing positions"""
        from app.api.routes.portfolio import close_position
        return await close_position(ticker, position_close)

    @app.post("/portfolio/reset")
    async def legacy_reset_portfolio():
        """Backward compatibility for resetting portfolio"""
        from app.api.routes.portfolio import reset_portfolio
        return await reset_portfolio()

    return app


app = create_application()

if __name__ == "__main__":
    """Run the application with Uvicorn server"""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 