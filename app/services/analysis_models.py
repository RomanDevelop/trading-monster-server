from abc import ABC, abstractmethod
from typing import Optional, Tuple
import pandas as pd
import numpy as np
import yfinance as yf
import time
from datetime import datetime

from app.models.schemas import Signal, AnalysisModelType
from app.core.config import settings


class BaseAnalysisModel(ABC):
    """Базовый абстрактный класс для моделей анализа тикеров"""
    
    @property
    @abstractmethod
    def model_type(self) -> AnalysisModelType:
        """Тип модели анализа"""
        pass
    
    @abstractmethod
    def analyze(self, ticker: str) -> Optional[Signal]:
        """Выполнить анализ тикера и вернуть сигнал, если он есть"""
        pass
    
    @abstractmethod
    def get_signal_proximity(self, ticker: str) -> Tuple[float, str]:
        """
        Вычисляет и возвращает процент близости к сигналу (0-100%)
        
        Returns:
            Tuple[float, str]: (процент близости к сигналу, описание текущего состояния)
        """
        pass
    
    @staticmethod
    def generate_signal_id(ticker: str) -> str:
        """Генерация уникального ID для сигнала"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{ticker}-{timestamp}"
    
    def get_stock_data(self, ticker: str, period: str = "30d", interval: str = "1d") -> Optional[pd.DataFrame]:
        """Получить исторические данные для тикера с повторными попытками при ошибке"""
        try:
            stock = yf.Ticker(ticker)
            max_attempts = settings.RETRY_ATTEMPTS
            hist = None
            
            for attempt in range(max_attempts):
                try:
                    hist = stock.history(period=period, interval=interval, timeout=15)
                    if not hist.empty:
                        break
                except Exception as e:
                    if attempt == max_attempts - 1:
                        print(f"Failed to get history for {ticker} after {max_attempts} attempts: {e}")
                        return None
                    print(f"Attempt {attempt+1} failed for {ticker}, retrying...")
                    time.sleep(settings.RETRY_DELAY)
            
            if hist is None or hist.empty:
                return None
                
            return hist
        except Exception as e:
            print(f"Error getting data for {ticker}: {e}")
            return None
    
    def get_earnings_growth(self, ticker: str) -> float:
        """Получить рост прибыли для тикера"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return info.get('earningsQuarterlyGrowth', 0)
        except Exception as e:
            print(f"Error getting ticker info for {ticker}: {e}")
            return 0


class RSIModel(BaseAnalysisModel):
    """Модель анализа на основе RSI (Relative Strength Index)"""
    
    @property
    def model_type(self) -> AnalysisModelType:
        return "RSI_MODEL"
    
    def calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculation of RSI (Relative Strength Index) indicator
        
        RSI = 100 - (100 / (1 + RS))
        RS = Average gain / Average loss over period
        
        RSI > 70 is considered overbought
        RSI < 30 is considered oversold
        """
        delta = data.diff()
        
        # Get positive and negative changes
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average values
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Calculate RS
        rs = avg_gain / avg_loss
        
        # Calculate RSI
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def get_signal_proximity(self, ticker: str) -> Tuple[float, str]:
        """
        Вычисляет и возвращает процент близости к сигналу на основе RSI
        
        Returns:
            Tuple[float, str]: (процент близости к сигналу, описание текущего состояния)
        """
        try:
            # Get historical data
            hist = self.get_stock_data(ticker, period="30d", interval="1d")
            if hist is None:
                return 0.0, "Unable to retrieve data"
            
            # Get earnings growth
            earnings_growth = self.get_earnings_growth(ticker)
            
            # Calculate RSI
            rsi = self.calculate_rsi(hist['Close'])
            current_rsi = rsi.iloc[-1] if not rsi.empty and not pd.isna(rsi.iloc[-1]) else 50
            
            # Analyze proximity to signals
            if current_rsi <= 30:
                # For long signals: RSI is already in oversold territory
                if earnings_growth > 0:
                    return 100.0, f"Oversold (RSI={current_rsi:.1f}) - 100% buy signal"
                else:
                    return 70.0, f"Oversold (RSI={current_rsi:.1f}) but negative earnings growth"
            elif current_rsi >= 70:
                # For short signals: RSI is already in overbought territory
                if earnings_growth < 0:
                    return 100.0, f"Overbought (RSI={current_rsi:.1f}) - 100% sell signal"
                else:
                    return 70.0, f"Overbought (RSI={current_rsi:.1f}) but positive earnings growth"
            elif 30 < current_rsi < 40:
                # Approaching oversold territory
                proximity = 100 - ((current_rsi - 30) / 10 * 100)
                return proximity, f"Approaching oversold (RSI={current_rsi:.1f}) - {proximity:.0f}% close to buy signal"
            elif 60 < current_rsi < 70:
                # Approaching overbought territory
                proximity = 100 - ((70 - current_rsi) / 10 * 100)
                return proximity, f"Approaching overbought (RSI={current_rsi:.1f}) - {proximity:.0f}% close to sell signal"
            else:
                # In neutral territory
                if current_rsi < 50:
                    # Closer to oversold
                    proximity = (50 - current_rsi) / 20 * 50  # 0% at RSI=50, 50% at RSI=30
                    return proximity, f"Neutral with bearish tendency (RSI={current_rsi:.1f}) - {proximity:.0f}% close to signal"
                else:
                    # Closer to overbought
                    proximity = (current_rsi - 50) / 20 * 50  # 0% at RSI=50, 50% at RSI=70
                    return proximity, f"Neutral with bullish tendency (RSI={current_rsi:.1f}) - {proximity:.0f}% close to signal"
        except Exception as e:
            print(f"Error calculating RSI signal proximity for {ticker}: {e}")
            return 0.0, "Error calculating proximity"
            
    def analyze(self, ticker: str) -> Optional[Signal]:
        """Analysis of ticker using RSI and fundamental indicators"""
        try:
            # Get historical data
            hist = self.get_stock_data(ticker, period="30d", interval="1d")
            if hist is None:
                return None
            
            # Analysis of the last trading day
            today = hist.index[-1].date()
            hist_today = hist[hist.index.date == today]

            if len(hist_today) == 0:
                return None

            open_price = hist_today.iloc[0]['Open']
            close_price = hist_today.iloc[-1]['Close']
            change_percent = (close_price - open_price) / open_price * 100
            
            # Get earnings growth
            earnings_growth = self.get_earnings_growth(ticker)
            
            # Calculate RSI
            rsi = self.calculate_rsi(hist['Close'])
            current_rsi = rsi.iloc[-1] if not rsi.empty and not pd.isna(rsi.iloc[-1]) else 50
            
            # Signal generation logic based on RSI values
            signal_type = None
            message = ""
            
            # Explicit signals based on RSI values
            if current_rsi < 30 and earnings_growth > 0:
                signal_type = "long"
                message = f"Oversold condition (RSI={current_rsi:.1f}) with positive earnings growth ({earnings_growth:.1%}) - potential buying opportunity"
            elif current_rsi > 30 and current_rsi < 70 and change_percent > 2 and earnings_growth > 0:
                signal_type = "long"
                message = f"Stock up by {change_percent:.1f}% with RSI={current_rsi:.1f} and positive earnings growth ({earnings_growth:.1%})"
            
            # Short signals - made conditions stricter
            elif current_rsi > 70 and earnings_growth < 0:
                signal_type = "short"
                message = f"Overbought condition (RSI={current_rsi:.1f}) with negative earnings growth ({earnings_growth:.1%}) - potential shorting opportunity"
            elif current_rsi > 30 and current_rsi < 70 and change_percent < -2 and earnings_growth < 0:
                signal_type = "short"
                message = f"Stock down by {change_percent:.1f}% with RSI={current_rsi:.1f} and negative earnings growth ({earnings_growth:.1%})"
            
            # Create signal if type is determined
            if signal_type:
                signal_id = self.generate_signal_id(ticker)
                return Signal(
                    id=signal_id,
                    ticker=ticker.upper(),
                    signal=signal_type,
                    message=message,
                    open=round(open_price, 2),
                    close=round(close_price, 2),
                    change_percent=round(change_percent, 2),
                    eps_growth=earnings_growth,
                    timestamp=datetime.now().isoformat(),
                    status="pending",
                    model_type=self.model_type
                )
                
        except Exception as e:
            print(f"Error analyzing {ticker} with RSI model: {e}")
            
        return None


class MACDModel(BaseAnalysisModel):
    """Модель анализа на основе MACD (Moving Average Convergence Divergence)"""
    
    @property
    def model_type(self) -> AnalysisModelType:
        return "MACD_MODEL"
    
    def calculate_macd(self, data: pd.Series, 
                      fast_period: int = 12, 
                      slow_period: int = 26, 
                      signal_period: int = 9) -> tuple:
        """
        Calculation of MACD (Moving Average Convergence Divergence) indicator
        
        MACD Line = EMA(fast_period) - EMA(slow_period)
        Signal Line = EMA(MACD Line, signal_period)
        Histogram = MACD Line - Signal Line
        
        Returns:
            tuple: (macd_line, signal_line, histogram)
        """
        # Calculate exponential moving averages
        ema_fast = data.ewm(span=fast_period, adjust=False).mean()
        ema_slow = data.ewm(span=slow_period, adjust=False).mean()
        
        # Calculate MACD line
        macd_line = ema_fast - ema_slow
        
        # Calculate signal line
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        
        # Calculate histogram
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def get_signal_proximity(self, ticker: str) -> Tuple[float, str]:
        """
        Вычисляет и возвращает процент близости к сигналу на основе MACD
        
        Returns:
            Tuple[float, str]: (процент близости к сигналу, описание текущего состояния)
        """
        try:
            # Get historical data
            hist = self.get_stock_data(ticker, period="60d", interval="1d")
            if hist is None:
                return 0.0, "Unable to retrieve data"
            
            # Get earnings growth
            earnings_growth = self.get_earnings_growth(ticker)
            
            # Calculate MACD
            macd_line, signal_line, histogram = self.calculate_macd(hist['Close'])
            
            # Get current and previous values
            current_macd = macd_line.iloc[-1]
            prev_macd = macd_line.iloc[-2]
            current_signal = signal_line.iloc[-1]
            prev_signal = signal_line.iloc[-2]
            current_hist = histogram.iloc[-1]
            prev_hist = histogram.iloc[-2]
            
            # Calculate distance between MACD line and signal line
            distance = abs(current_macd - current_signal)
            avg_distance = abs(macd_line - signal_line).mean()  # Average distance for scaling
            
            # Calculate proximity based on different patterns
            
            # For bullish crossover (MACD line crossing above signal line)
            if current_macd < current_signal and current_macd > prev_macd:
                # How close MACD is to crossing the signal line
                cross_proximity = 100 * (1 - min(1, (current_signal - current_macd) / avg_distance))
                if earnings_growth > 0:
                    return cross_proximity, f"Approaching bullish crossover ({cross_proximity:.0f}% close to buy signal)"
                else:
                    return cross_proximity * 0.7, f"Approaching bullish crossover but negative earnings"
            
            # For bearish crossover (MACD line crossing below signal line)
            elif current_macd > current_signal and current_macd < prev_macd:
                # How close MACD is to crossing the signal line
                cross_proximity = 100 * (1 - min(1, (current_macd - current_signal) / avg_distance))
                if earnings_growth < 0:
                    return cross_proximity, f"Approaching bearish crossover ({cross_proximity:.0f}% close to sell signal)"
                else:
                    return cross_proximity * 0.7, f"Approaching bearish crossover but positive earnings"
            
            # For bullish trend (MACD line above signal line)
            elif current_macd > current_signal:
                if current_macd > prev_macd and current_signal > prev_signal:
                    # Strengthening bullish trend
                    return 80.0, "Strong bullish trend - potential buy signal"
                elif current_macd < prev_macd and current_signal < prev_signal:
                    # Weakening bullish trend
                    return 30.0, "Weakening bullish trend"
                else:
                    return 50.0, "Bullish trend"
            
            # For bearish trend (MACD line below signal line)
            elif current_macd < current_signal:
                if current_macd < prev_macd and current_signal < prev_signal:
                    # Strengthening bearish trend
                    return 80.0, "Strong bearish trend - potential sell signal"
                elif current_macd > prev_macd and current_signal > prev_signal:
                    # Weakening bearish trend
                    return 30.0, "Weakening bearish trend"
                else:
                    return 50.0, "Bearish trend"
            
            # Default case
            return 0.0, "Neutral trend"
            
        except Exception as e:
            print(f"Error calculating MACD signal proximity for {ticker}: {e}")
            return 0.0, "Error calculating proximity"
    
    def analyze(self, ticker: str) -> Optional[Signal]:
        """Analysis of ticker using MACD and fundamental indicators"""
        try:
            # Get historical data
            hist = self.get_stock_data(ticker, period="60d", interval="1d")  # MACD requires more data
            if hist is None:
                return None
            
            # Analysis of the last trading day
            today = hist.index[-1].date()
            hist_today = hist[hist.index.date == today]

            if len(hist_today) == 0:
                return None

            open_price = hist_today.iloc[0]['Open']
            close_price = hist_today.iloc[-1]['Close']
            change_percent = (close_price - open_price) / open_price * 100
            
            # Get earnings growth
            earnings_growth = self.get_earnings_growth(ticker)
            
            # Calculate MACD
            macd_line, signal_line, histogram = self.calculate_macd(hist['Close'])
            
            # Get current and previous values
            current_macd = macd_line.iloc[-1]
            prev_macd = macd_line.iloc[-2]
            current_signal = signal_line.iloc[-1]
            prev_signal = signal_line.iloc[-2]
            current_hist = histogram.iloc[-1]
            prev_hist = histogram.iloc[-2]
            
            # MACD signal analysis
            signal_type = None
            message = ""
            
            # Bullish signals
            if (
                macd_line.iloc[-1] > macd_line.iloc[-2] and 
                macd_line.iloc[-2] < signal_line.iloc[-2] and 
                earnings_growth > 0
            ):
                signal_type = "long"
                message = f"MACD bullish crossover with positive earnings growth ({earnings_growth:.1%})"
            
            # Bullish divergence
            elif (
                current_macd < prev_macd and
                current_signal < prev_signal and
                current_hist < prev_hist and
                earnings_growth > 0
            ):
                signal_type = "long"
                message = f"MACD bullish divergence with positive earnings growth ({earnings_growth:.1%})"
            
            # Bearish signals
            elif (
                macd_line.iloc[-1] < macd_line.iloc[-2] and 
                macd_line.iloc[-2] > signal_line.iloc[-2] and 
                earnings_growth < 0
            ):
                signal_type = "short"
                message = f"MACD bearish crossover with negative earnings growth ({earnings_growth:.1%})"
            
            # Bearish divergence
            elif (
                current_macd > prev_macd and
                current_signal > prev_signal and
                current_hist > prev_hist and
                earnings_growth < 0
            ):
                signal_type = "short"
                message = f"MACD bearish divergence with negative earnings growth ({earnings_growth:.1%})"
            
            # Create signal if type is determined
            if signal_type:
                signal_id = self.generate_signal_id(ticker)
                return Signal(
                    id=signal_id,
                    ticker=ticker.upper(),
                    signal=signal_type,
                    message=message,
                    open=round(open_price, 2),
                    close=round(close_price, 2),
                    change_percent=round(change_percent, 2),
                    eps_growth=earnings_growth,
                    timestamp=datetime.now().isoformat(),
                    status="pending",
                    model_type=self.model_type
                )
                
        except Exception as e:
            print(f"Error analyzing {ticker} with MACD model: {e}")
            
        return None


class BollingerBandsModel(BaseAnalysisModel):
    """Модель анализа на основе Bollinger Bands (Полосы Боллинджера)"""
    
    @property
    def model_type(self) -> AnalysisModelType:
        return "BOLLINGER_MODEL"
    
    def calculate_bollinger_bands(self, data: pd.Series, window: int = 20, num_std: float = 2.0) -> tuple:
        """
        Calculation of Bollinger Bands indicator
        
        Middle Band = SMA(data, window)
        Upper Band = Middle Band + (num_std * std(data, window))
        Lower Band = Middle Band - (num_std * std(data, window))
        
        Returns:
            tuple: (upper_band, middle_band, lower_band)
        """
        # Calculate middle band (SMA)
        middle_band = data.rolling(window=window).mean()
        
        # Calculate standard deviation
        std = data.rolling(window=window).std()
        
        # Calculate upper and lower bands
        upper_band = middle_band + (std * num_std)
        lower_band = middle_band - (std * num_std)
        
        return upper_band, middle_band, lower_band
    
    def get_signal_proximity(self, ticker: str) -> Tuple[float, str]:
        """
        Вычисляет и возвращает процент близости к сигналу на основе Bollinger Bands
        
        Returns:
            Tuple[float, str]: (процент близости к сигналу, описание текущего состояния)
        """
        try:
            # Get historical data
            hist = self.get_stock_data(ticker, period="60d", interval="1d")
            if hist is None:
                return 0.0, "Unable to retrieve data"
            
            # Get earnings growth
            earnings_growth = self.get_earnings_growth(ticker)
            
            # Calculate Bollinger Bands
            upper_band, middle_band, lower_band = self.calculate_bollinger_bands(hist['Close'])
            
            # Get current and previous values
            current_price = hist['Close'].iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_middle = middle_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            
            # Calculate band width (volatility)
            band_width = (current_upper - current_lower) / current_middle
            
            # Calculate normalized position within the bands (0 = lower band, 1 = upper band)
            position_in_band = (current_price - current_lower) / (current_upper - current_lower)
            
            # Proximity calculation based on position within bands and band width
            if position_in_band <= 0.1:  # Very close to lower band
                if earnings_growth > 0:
                    return 95.0, f"Price near lower Bollinger Band ({position_in_band*100:.0f}%) - strong buy signal potential"
                else:
                    return 70.0, f"Price near lower Bollinger Band but negative earnings growth"
            elif position_in_band >= 0.9:  # Very close to upper band
                if earnings_growth < 0:
                    return 95.0, f"Price near upper Bollinger Band ({(1-position_in_band)*100:.0f}%) - strong sell signal potential"
                else:
                    return 70.0, f"Price near upper Bollinger Band but positive earnings growth"
            elif position_in_band < 0.3:  # Approaching lower band
                proximity = 100 - (position_in_band / 0.3 * 70)  # 100% at lower band, 30% at 30% of the band
                return proximity, f"Approaching lower Bollinger Band - {proximity:.0f}% close to buy signal"
            elif position_in_band > 0.7:  # Approaching upper band
                proximity = 100 - ((1 - position_in_band) / 0.3 * 70)  # 100% at upper band, 30% at 70% of the band
                return proximity, f"Approaching upper Bollinger Band - {proximity:.0f}% close to sell signal"
            elif band_width < 0.05:  # Very narrow bands - potential breakout
                return 80.0, f"Low volatility ({band_width:.2f}) - potential breakout signal approaching"
            else:
                # In the middle of the bands - calculate how close to middle (50% at middle, 0% half way to either band)
                middle_proximity = (1 - abs(0.5 - position_in_band) * 4) * 50
                return middle_proximity, f"Price in neutral territory - {middle_proximity:.0f}% signal strength"
                
        except Exception as e:
            print(f"Error calculating Bollinger Bands signal proximity for {ticker}: {e}")
            return 0.0, "Error calculating proximity"
    
    def analyze(self, ticker: str) -> Optional[Signal]:
        """Analysis of ticker using Bollinger Bands and fundamental indicators"""
        try:
            # Get historical data
            hist = self.get_stock_data(ticker, period="60d", interval="1d")
            if hist is None:
                return None
            
            # Analysis of the last trading day
            today = hist.index[-1].date()
            hist_today = hist[hist.index.date == today]

            if len(hist_today) == 0:
                return None

            open_price = hist_today.iloc[0]['Open']
            close_price = hist_today.iloc[-1]['Close']
            change_percent = (close_price - open_price) / open_price * 100
            
            # Get earnings growth
            earnings_growth = self.get_earnings_growth(ticker)
            
            # Calculate Bollinger Bands
            upper_band, middle_band, lower_band = self.calculate_bollinger_bands(hist['Close'])
            
            # Get current and previous values
            current_price = close_price
            current_upper = upper_band.iloc[-1]
            current_middle = middle_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            
            # Calculate band width (volatility)
            band_width = (current_upper - current_lower) / current_middle
            
            # Logic for generating signals based on Bollinger Bands
            signal_type = None
            message = ""
            
            # Check for bounce from lower band (potential LONG)
            if current_price <= current_lower * 1.05:  # Increased range from 1.02 to 1.05
                prev_prices = hist['Close'].iloc[-5:-1]
                min_prev_price = prev_prices.min()
                
                # Check if bounce occurred (current price above minimum of previous days)
                if current_price > min_prev_price * 0.99:  # Softened bounce condition
                    signal_type = "long"
                    message = f"Bounce from the lower Bollinger Band with positive earnings growth ({earnings_growth:.1%}). Potential upward trend reversal."
            
            # Check for bounce from upper band (potential SHORT)
            elif current_price >= current_upper * 0.95:  # Increased range from 0.98 to 0.95
                prev_prices = hist['Close'].iloc[-5:-1]
                max_prev_price = prev_prices.max()
                
                # Check if bounce occurred (current price below maximum of previous days)
                if current_price < max_prev_price * 1.01:  # Softened bounce condition
                    signal_type = "short"
                    message = f"Bounce from the upper Bollinger Band with negative earnings growth ({earnings_growth:.1%}). Potential downward trend reversal."
            
            # Check for band compression (low volatility) - waiting for breakout
            elif band_width < 0.08:  # Increased threshold from 0.05 to 0.08
                # Upward trend
                if current_price > current_middle and earnings_growth >= 0:  # Changed condition to >=
                    signal_type = "long"
                    message = f"Low volatility with price above the middle Bollinger Band with positive earnings growth ({earnings_growth:.1%}). Potential upward breakout."
                # Downward trend
                elif current_price < current_middle and earnings_growth <= 0:  # Changed condition to <=
                    signal_type = "short"
                    message = f"Low volatility with price below the middle Bollinger Band with negative earnings growth ({earnings_growth:.1%}). Potential downward breakout."
            
            # Create signal if type is determined
            if signal_type:
                signal_id = self.generate_signal_id(ticker)
                return Signal(
                    id=signal_id,
                    ticker=ticker.upper(),
                    signal=signal_type,
                    message=message,
                    open=round(open_price, 2),
                    close=round(close_price, 2),
                    change_percent=round(change_percent, 2),
                    eps_growth=earnings_growth,
                    timestamp=datetime.now().isoformat(),
                    status="pending",
                    model_type=self.model_type
                )
                
        except Exception as e:
            print(f"Error analyzing {ticker} with Bollinger Bands model: {e}")
            
        return None


# Factory for creating instances of analysis models
class AnalysisModelFactory:
    """Factory for creating instances of analysis models"""
    
    @staticmethod
    def create_model(model_type: AnalysisModelType) -> BaseAnalysisModel:
        """Create an instance of analysis model based on its type"""
        if model_type == "RSI_MODEL":
            return RSIModel()
        elif model_type == "MACD_MODEL":
            return MACDModel()
        elif model_type == "BOLLINGER_MODEL":
            return BollingerBandsModel()
        else:
            raise ValueError(f"Unknown analysis model type: {model_type}") 