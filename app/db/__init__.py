from app.core.config import settings
from app.db.repository import InMemoryRepository

# Initialize repository
repository = InMemoryRepository(initial_balance=settings.INITIAL_BALANCE) 