from app.core.config import settings
from app.db.repository import InMemoryRepository

# Инициализация репозитория
repository = InMemoryRepository(initial_balance=settings.INITIAL_BALANCE) 