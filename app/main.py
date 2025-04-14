from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api import api_router
from app.core.config import settings
from app.services.monitoring import monitoring_service
from app.db import repository

# Импортируем все необходимые модели для обратной совместимости
from app.models.schemas import TickerRequest, SignalConfirmation, PositionClose


def create_application() -> FastAPI:
    """Создание и настройка экземпляра FastAPI"""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        debug=settings.DEBUG
    )
    
    # Настройка CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    
    # Подключение API роутов
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # Обработчики событий запуска и остановки
    @app.on_event("startup")
    def startup_event():
        """Запуск сервисов при старте приложения"""
        monitoring_service.start()
    
    @app.on_event("shutdown")
    def shutdown_event():
        """Остановка сервисов при завершении приложения"""
        monitoring_service.stop()

    # ============ МАРШРУТЫ ОБРАТНОЙ СОВМЕСТИМОСТИ ============
    # Эти маршруты сохраняют старые пути API для клиента,
    # но перенаправляют запросы на новые обработчики

    # Маршруты для тикеров
    @app.post("/monitor")
    async def legacy_monitor_ticker(request: TickerRequest):
        """Обратная совместимость для добавления тикера"""
        from app.api.routes.tickers import monitor_ticker
        return await monitor_ticker(request)

    @app.get("/watchlist")
    async def legacy_get_watchlist():
        """Обратная совместимость для получения списка тикеров"""
        from app.api.routes.tickers import get_watchlist
        return await get_watchlist()

    @app.delete("/monitor/{ticker}")
    async def legacy_remove_ticker(ticker: str):
        """Обратная совместимость для удаления тикера"""
        from app.api.routes.tickers import remove_ticker
        return await remove_ticker(ticker)

    # Маршруты для сигналов
    @app.get("/signals")
    async def legacy_get_signals():
        """Обратная совместимость для получения сигналов"""
        from app.api.routes.signals import get_signals
        return await get_signals()

    @app.get("/signals/{ticker}")
    async def legacy_get_signals_by_ticker(ticker: str):
        """Обратная совместимость для получения сигналов по тикеру"""
        from app.api.routes.signals import get_signals_by_ticker
        return await get_signals_by_ticker(ticker)

    @app.post("/signals/confirm")
    async def legacy_confirm_signal(confirmation: SignalConfirmation):
        """Обратная совместимость для подтверждения сигнала"""
        from app.api.routes.signals import confirm_signal
        return await confirm_signal(confirmation)

    @app.get("/signals/history")
    async def legacy_get_signal_history():
        """Обратная совместимость для получения истории сигналов"""
        from app.api.routes.signals import get_signal_history
        return await get_signal_history()

    # Маршруты для портфеля
    @app.get("/balance")
    async def legacy_get_balance():
        """Обратная совместимость для получения баланса"""
        from app.api.routes.portfolio import get_balance
        return await get_balance()

    @app.get("/positions")
    async def legacy_get_positions():
        """Обратная совместимость для получения позиций"""
        from app.api.routes.portfolio import get_positions
        return await get_positions()

    @app.post("/positions/close/{ticker}")
    async def legacy_close_position(ticker: str, position_close: PositionClose):
        """Обратная совместимость для закрытия позиции"""
        from app.api.routes.portfolio import close_position
        return await close_position(ticker, position_close)

    @app.get("/positions/history")
    async def legacy_get_position_history():
        """Обратная совместимость для получения истории позиций"""
        from app.api.routes.portfolio import get_position_history
        return await get_position_history()

    @app.post("/portfolio/reset")
    async def legacy_reset_portfolio():
        """Обратная совместимость для сброса портфеля"""
        from app.api.routes.portfolio import reset_portfolio
        return await reset_portfolio()
    
    return app


app = create_application()


if __name__ == "__main__":
    """Запуск сервера для разработки"""
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 