from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from cachetools import TTLCache

# Кэш: помним пользователя 0.5 секунды
# Если он придет снова раньше - игнорируем
cache = TTLCache(maxsize=10_000, ttl=0.5)


class ThrottlingMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id

        # Если юзер есть в кэше - значит он частит
        if user_id in cache:
            # Можно ответить "Не спеши!", а можно просто игнорировать
            return

            # Запоминаем его
        cache[user_id] = True

        return await handler(event, data)