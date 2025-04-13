from typing import Optional
import yfinance as yf
import time
from datetime import datetime
from app.models.schemas import Signal
from app.core.config import settings


class StockAnalyzer:
    """Сервис для анализа акций и генерации торговых сигналов"""
    
    @staticmethod
    def generate_signal_id(ticker: str) -> str:
        """Генерация уникального ID для сигнала"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{ticker}-{timestamp}"
    
    def analyze_stock(self, ticker: str) -> Optional[Signal]:
        """Анализ акции и создание сигнала, если анализ успешен"""
        try:
            # Устанавливаем таймаут для запросов к Yahoo Finance
            stock = yf.Ticker(ticker)
            
            # Пробуем получить историю с несколькими попытками в случае ошибки
            max_attempts = settings.RETRY_ATTEMPTS
            hist = None
            
            for attempt in range(max_attempts):
                try:
                    hist = stock.history(period="1d", interval="5m", timeout=15)
                    if not hist.empty:
                        break  # Если успешно получили данные, выходим из цикла
                except Exception as e:
                    if attempt == max_attempts - 1:  # Если это была последняя попытка
                        print(f"Failed to get history for {ticker} after {max_attempts} attempts: {e}")
                        return None
                    print(f"Attempt {attempt+1} failed for {ticker}, retrying...")
                    time.sleep(settings.RETRY_DELAY)  # Ждем перед повторной попыткой
            
            if hist is None or hist.empty:
                return None
            
            today = hist.index[-1].date()
            hist_today = hist[hist.index.date == today]

            if len(hist_today) == 0:
                return None

            open_price = hist_today.iloc[0]['Open']
            close_price = hist_today.iloc[-1]['Close']
            change_percent = (close_price - open_price) / open_price * 100

            # Безопасное получение информации о тикере
            try:
                info = stock.info
                earnings_growth = info.get('earningsQuarterlyGrowth', 0)
            except Exception as e:
                print(f"Error getting ticker info for {ticker}: {e}")
                earnings_growth = 0  # Используем дефолтное значение при ошибке

            # Модель поведения
            if change_percent > 1.5 and earnings_growth > 0:
                if close_price > open_price:
                    signal_id = self.generate_signal_id(ticker)
                    return Signal(
                        id=signal_id,
                        ticker=ticker.upper(),
                        signal="long",
                        message="Positive earnings and price above open — look for pullback breakout",
                        open=round(open_price, 2),
                        close=round(close_price, 2),
                        change_percent=round(change_percent, 2),
                        eps_growth=earnings_growth,
                        timestamp=datetime.now().isoformat(),
                        status="pending"
                    )
            elif change_percent < -1.5 and earnings_growth < 0:
                if close_price < open_price:
                    signal_id = self.generate_signal_id(ticker)
                    return Signal(
                        id=signal_id,
                        ticker=ticker.upper(),
                        signal="short",
                        message="Negative earnings and price below open — look for continuation drop",
                        open=round(open_price, 2),
                        close=round(close_price, 2),
                        change_percent=round(change_percent, 2),
                        eps_growth=earnings_growth,
                        timestamp=datetime.now().isoformat(),
                        status="pending"
                    )
        except Exception as e:
            print(f"Error analyzing {ticker}: {e}")
            return None
        
        return None
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """Получение текущей цены акции"""
        try:
            stock = yf.Ticker(ticker)
            
            # Несколько попыток получить данные
            max_attempts = settings.RETRY_ATTEMPTS
            hist = None
            
            for attempt in range(max_attempts):
                try:
                    hist = stock.history(period="1d", interval="1m", timeout=15)
                    if not hist.empty:
                        break
                except Exception as e:
                    if attempt == max_attempts - 1:
                        print(f"Failed to get price for {ticker} after {max_attempts} attempts: {e}")
                        return None
                    time.sleep(settings.RETRY_DELAY)
            
            if hist is not None and not hist.empty:
                return hist.iloc[-1]['Close']
            
            return None
        except Exception as e:
            print(f"Error getting price for {ticker}: {e}")
            return None


# Создаем экземпляр сервиса
stock_analyzer = StockAnalyzer() 