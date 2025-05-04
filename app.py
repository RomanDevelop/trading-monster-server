from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import yfinance as yf
import threading
import time
import uvicorn
from datetime import datetime

app = FastAPI(title="Trading Signal API")

# Разрешаем доступ с Flutter клиента (можно уточнить конкретный IP)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Тикеры, которые надо мониторить
watchlist = set()

# Сигналы, которые можно будет получить из Flutter
# Теперь храним словарь, где ключи - тикеры, значения - список сигналов
# Формат: {ticker: [signal1, signal2, ...]}
signals_by_ticker: Dict[str, List[dict]] = {}
# Активные сигналы (те, которые еще не подтверждены)
active_signals = []
# История сигналов
signal_history = []

# Новые переменные для управления портфелем
user_balance = 1000.0  # Начальный баланс пользователя
open_positions = {}    # Словарь открытых позиций: {ticker: position_data}
position_history = []  # История всех позиций (открытых и закрытых)

# 🔹 Форматы данных
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

# Генерация уникального ID для сигнала
def generate_signal_id(ticker: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{ticker}-{timestamp}"

# Расчет P&L для позиции
def calculate_pnl(position: Dict[str, Any], current_price: float) -> float:
    if position["signal_type"].lower() == "long":
        return (current_price - position["price"]) * position["quantity"]
    else:  # short
        return (position["price"] - current_price) * position["quantity"]

# 🔍 Твоя логика анализа тикера
def analyze_stock(ticker: str) -> Optional[SignalResponse]:
    try:
        # Устанавливаем таймаут для запросов к Yahoo Finance
        stock = yf.Ticker(ticker)
        
        # Пробуем получить историю с несколькими попытками в случае ошибки
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                hist = stock.history(period="1d", interval="5m", timeout=15)
                if hist.empty:
                    return None
                break  # Если успешно получили данные, выходим из цикла
            except Exception as e:
                if attempt == max_attempts - 1:  # Если это была последняя попытка
                    print(f"Failed to get history for {ticker} after {max_attempts} attempts: {e}")
                    return None
                print(f"Attempt {attempt+1} failed for {ticker}, retrying...")
                time.sleep(2)  # Ждем 2 секунды перед повторной попыткой
        
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

        # Модель поведения (твоя логика)
        if change_percent > 1.5 and earnings_growth > 0:
            if close_price > open_price:
                signal_id = generate_signal_id(ticker)
                return SignalResponse(
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
                signal_id = generate_signal_id(ticker)
                return SignalResponse(
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

# 🔁 Мониторинг тикеров в фоне
def monitoring_loop():
    while True:
        try:
            new_active_signals = []
            for ticker in list(watchlist):
                try:
                    result = analyze_stock(ticker)
                    if result:
                        # Проверяем, не был ли этот сигнал уже отправлен
                        signal_dict = result.dict()
                        
                        # Добавляем в историю всех сигналов
                        signal_history.append(signal_dict)
                        
                        # Проверяем, есть ли сигналы для данного тикера
                        if ticker not in signals_by_ticker:
                            signals_by_ticker[ticker] = []
                        
                        # Проверяем, не был ли этот сигнал уже отправлен (по времени и типу)
                        # Если последний сигнал отличается от текущего или прошло много времени,
                        # добавляем новый сигнал
                        add_signal = True
                        if signals_by_ticker[ticker]:
                            last_signal = signals_by_ticker[ticker][-1]
                            last_time = datetime.fromisoformat(last_signal["timestamp"])
                            current_time = datetime.fromisoformat(signal_dict["timestamp"])
                            time_diff = (current_time - last_time).total_seconds()
                            # Если последний сигнал того же типа и прошло менее 30 минут, игнорируем
                            if last_signal["signal"] == signal_dict["signal"] and time_diff < 1800:
                                add_signal = False
                        
                        if add_signal:
                            signals_by_ticker[ticker].append(signal_dict)
                            new_active_signals.append(signal_dict)
                except Exception as e:
                    print(f"Error processing ticker {ticker} in monitoring loop: {e}")
                    continue  # Пропускаем этот тикер и продолжаем с другими
            
            # Обновляем активные сигналы
            global active_signals
            active_signals = [
                s for s in active_signals if s["status"] == "pending"
            ] + new_active_signals
            
            # Обновляем текущие цены для открытых позиций
            for ticker in list(open_positions.keys()):
                try:
                    stock = yf.Ticker(ticker)
                    
                    # Несколько попыток получить данные
                    max_attempts = 3
                    hist = None
                    for attempt in range(max_attempts):
                        try:
                            hist = stock.history(period="1d", interval="1m", timeout=15)
                            if not hist.empty:
                                break
                        except Exception as e:
                            if attempt == max_attempts - 1:
                                print(f"Failed to update price for {ticker} after {max_attempts} attempts: {e}")
                            time.sleep(1)
                    
                    if hist is not None and not hist.empty:
                        current_price = hist.iloc[-1]['Close']
                        open_positions[ticker]["current_price"] = current_price
                        open_positions[ticker]["pnl"] = calculate_pnl(open_positions[ticker], current_price)
                        open_positions[ticker]["updated_at"] = datetime.now().isoformat()
                    else:
                        print(f"No data available for {ticker}, skipping price update")
                except Exception as e:
                    print(f"Error updating price for {ticker}: {e}")
        except Exception as e:
            print(f"Unexpected error in monitoring loop: {e}")
            # Продолжаем выполнение цикла даже при непредвиденных ошибках
        
        # Пауза между циклами мониторинга
        time.sleep(300)  # Проверка каждые 5 минут

# ✅ Endpoint: добавить тикер
@app.post("/monitor")
def monitor_ticker(request: TickerRequest):
    ticker = request.ticker.upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")
    watchlist.add(ticker)
    return {"message": f"{ticker} added to watchlist"}

# ✅ Endpoint: получить все активные сигналы
@app.get("/signals", response_model=List[dict])
def get_signals():
    return active_signals

# ✅ Endpoint: получить все сигналы по тикеру
@app.get("/signals/{ticker}", response_model=List[dict])
def get_signals_by_ticker(ticker: str):
    ticker = ticker.upper()
    if ticker not in signals_by_ticker:
        return []
    return signals_by_ticker[ticker]

# ✅ Endpoint: подтвердить или отклонить сигнал
@app.post("/signals/confirm")
def confirm_signal(confirmation: SignalConfirmation):
    global user_balance, open_positions
    
    signal_id = confirmation.signal_id
    action = confirmation.action
    quantity = confirmation.quantity
    
    # Находим сигнал по ID
    signal_to_update = None
    for signal in active_signals:
        if signal["id"] == signal_id:
            signal_to_update = signal
            break
    
    if not signal_to_update:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    # Обновляем статус сигнала
    if action == "confirm":
        signal_to_update["status"] = "confirmed"
        if quantity:
            signal_to_update["quantity"] = quantity
            
            # Создаем позицию при подтверждении сигнала
            ticker = signal_to_update["ticker"]
            price = signal_to_update["close"]
            signal_type = signal_to_update["signal"]
            
            # Вычисляем стоимость позиции
            position_value = price * quantity
            
            # Проверяем хватает ли денег для LONG позиции
            if signal_type.lower() == "long" and position_value > user_balance:
                raise HTTPException(status_code=400, detail="Insufficient balance")
            
            # Создаем новую позицию
            position = {
                "ticker": ticker,
                "signal_type": signal_type,
                "price": price,
                "quantity": quantity,
                "open_timestamp": datetime.now().isoformat(),
                "current_price": price,
                "pnl": 0.0
            }
            
            # Для LONG вычитаем сумму из баланса
            if signal_type.lower() == "long":
                user_balance -= position_value
                print(f"LONG position opened: Balance before={user_balance + position_value}, after={user_balance}")
            else:
                print(f"SHORT position opened: Balance remains {user_balance}")
            
            # Сохраняем позицию и убираем тикер из watchlist после подтверждения
            open_positions[ticker] = position
            position_history.append({**position, "status": "open"})
            
    elif action == "reject":
        signal_to_update["status"] = "rejected"
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    # Обновляем сигнал также в signals_by_ticker
    ticker = signal_to_update["ticker"]
    if ticker in signals_by_ticker:
        for signal in signals_by_ticker[ticker]:
            if signal["id"] == signal_id:
                signal["status"] = signal_to_update["status"]
                if quantity and action == "confirm":
                    signal["quantity"] = quantity
    
    return {
        "message": f"Signal {signal_id} {action}ed successfully",
        "balance": user_balance,
        "positions": list(open_positions.values())
    }

# ✅ Endpoint: получить историю всех сигналов
@app.get("/signals/history", response_model=List[dict])
def get_signal_history():
    return signal_history

# ✅ Endpoint: удалить тикер из мониторинга
@app.delete("/monitor/{ticker}")
def remove_ticker(ticker: str):
    ticker = ticker.upper()
    if ticker in watchlist:
        watchlist.remove(ticker)
        return {"message": f"{ticker} removed from watchlist"}
    raise HTTPException(status_code=404, detail="Ticker not found in watchlist")

# ✅ Endpoint: получить список отслеживаемых тикеров
@app.get("/watchlist", response_model=List[str])
def get_watchlist():
    return list(watchlist)

# 🆕 Endpoint: получить текущий баланс
@app.get("/balance")
def get_balance():
    return {"balance": user_balance}

# 🆕 Endpoint: получить открытые позиции
@app.get("/positions")
def get_positions():
    return {
        "positions": list(open_positions.values()),
        "balance": user_balance
    }

# 🆕 Endpoint: получить историю позиций
@app.get("/positions/history")
def get_position_history():
    return position_history

# 🆕 Endpoint: закрыть позицию
@app.post("/positions/close/{ticker}")
def close_position(ticker: str, position_close: PositionClose):
    global user_balance, open_positions
    
    ticker = ticker.upper()
    if ticker not in open_positions:
        raise HTTPException(status_code=404, detail="Position not found")
    
    position = open_positions[ticker]
    close_price = position_close.close_price
    
    # Расчет P&L
    pnl = calculate_pnl(position, close_price)
    
    # Расчет инвестированной суммы
    invested_amount = position["price"] * position["quantity"]
    
    # Обновление баланса
    if position["signal_type"].lower() == "long":
        # Для LONG: возвращаем инвестиции + P&L
        closing_amount = close_price * position["quantity"]
        user_balance += closing_amount
        print(f"LONG position closed: Balance before={user_balance - closing_amount}, after={user_balance}, P&L={pnl}")
    else:
        # Для SHORT: только P&L
        user_balance += pnl
        print(f"SHORT position closed: Balance before={user_balance - pnl}, after={user_balance}, P&L={pnl}")
    
    # Сохраняем информацию о закрытой позиции
    closed_position = {
        **position,
        "close_price": close_price,
        "close_timestamp": datetime.now().isoformat(),
        "pnl": pnl,
        "status": "closed"
    }
    position_history.append(closed_position)
    
    # Удаляем позицию из открытых
    del open_positions[ticker]
    
    return {
        "message": f"Position {ticker} closed successfully",
        "closed_position": closed_position,
        "balance": user_balance,
        "pnl": pnl
    }

# 🆕 Endpoint: очистить портфель и сбросить баланс
@app.post("/portfolio/reset")
def reset_portfolio():
    global user_balance, open_positions, position_history
    
    user_balance = 1000.0
    old_positions = open_positions.copy()
    open_positions = {}
    
    # Помечаем все позиции как закрытые
    for ticker, position in old_positions.items():
        position_history.append({
            **position,
            "close_timestamp": datetime.now().isoformat(),
            "status": "closed_by_reset"
        })
    
    return {
        "message": "Portfolio reset successfully",
        "balance": user_balance,
        "positions": []
    }

# 🔄 Старт фонового потока мониторинга
threading.Thread(target=monitoring_loop, daemon=True).start()

@app.get("/")
def root():
    return {"message": "Trading Signal API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Запуск сервера (если напрямую)
if __name__ == '__main__':
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)