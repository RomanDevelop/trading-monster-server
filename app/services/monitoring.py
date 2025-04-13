import threading
import time
from datetime import datetime
from app.db import repository
from app.services.stock_analyzer import stock_analyzer
from app.services.portfolio_manager import portfolio_manager
from app.core.config import settings


class MonitoringService:
    """Сервис для мониторинга акций и обработки сигналов в фоновом режиме"""
    
    def __init__(self):
        self._thread = None
        self._running = False
    
    def start(self):
        """Запуск мониторинга в отдельном потоке"""
        if self._thread is None or not self._thread.is_alive():
            self._running = True
            self._thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self._thread.start()
            print("Monitoring service started")
    
    def stop(self):
        """Остановка мониторинга"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            print("Monitoring service stopped")
    
    def _monitoring_loop(self):
        """Основной цикл мониторинга"""
        while self._running:
            try:
                # Мониторинг тикеров и генерация сигналов
                self._monitor_tickers()
                
                # Обновление цен для открытых позиций
                portfolio_manager.update_positions_prices()
            except Exception as e:
                print(f"Unexpected error in monitoring loop: {e}")
            
            # Пауза между циклами мониторинга
            time.sleep(settings.MONITORING_INTERVAL)
    
    def _monitor_tickers(self):
        """Мониторинг тикеров из списка наблюдения"""
        for ticker in repository.get_watchlist():
            try:
                result = stock_analyzer.analyze_stock(ticker)
                if result:
                    # Добавляем сигнал в репозиторий
                    repository.add_signal(result)
            except Exception as e:
                print(f"Error processing ticker {ticker} in monitoring: {e}")


# Создаем экземпляр сервиса
monitoring_service = MonitoringService() 