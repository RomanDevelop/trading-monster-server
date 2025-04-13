from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api import api_router
from app.core.config import settings
from app.services.monitoring import monitoring_service


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
    
    return app


app = create_application()


if __name__ == "__main__":
    """Запуск сервера для разработки"""
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 