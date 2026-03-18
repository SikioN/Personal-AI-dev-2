"""Access control middleware for the Telegram bot."""
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery


class AccessControlMiddleware(BaseMiddleware):
    """Allow only listed users (by username or user_id).

    ``allowed_raw`` is a comma-separated list of usernames (with or without @)
    and/or numeric user IDs.  Pass ``"*"`` (or leave empty) to allow everyone.
    """

    def __init__(self, allowed_raw: str):
        if not allowed_raw or allowed_raw.strip() == "*":
            self.allowed: set[str] = set()  # empty = allow all
        else:
            self.allowed = {
                u.strip().lstrip("@").lower()
                for u in allowed_raw.split(",")
                if u.strip()
            }

    async def __call__(self, handler, event: TelegramObject, data):
        if not self.allowed:
            return await handler(event, data)

        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)

        uid = str(user.id)
        uname = (user.username or "").lower()
        if uid in self.allowed or uname in self.allowed:
            return await handler(event, data)

        if isinstance(event, Message):
            await event.answer("У вас нет доступа к этому боту.")
        elif isinstance(event, CallbackQuery):
            await event.answer("Нет доступа.", show_alert=True)
