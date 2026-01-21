import os
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.flags import get_flag


class ThrottlingMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:
        # Твой старый код анти-спама можно оставить тут или пока пропустить
        # Если его нет, просто вызываем handler
        return await handler(event, data)


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: [Message, CallbackQuery],
            data: Dict[str, Any]
    ) -> Any:

        # Получаем настройки из .env
        channel_id = os.getenv("CHANNEL_ID")
        channel_url = os.getenv("CHANNEL_URL")

        # Если настройки не заданы - пропускаем проверку (режим разработки)
        if not channel_id or not channel_url:
            return await handler(event, data)

        # Определяем, кто пишет (User)
        user = event.from_user

        # Проверяем статус подписки
        # Бот должен быть АДМИНОМ канала, чтобы это сработало!
        try:
            member = await event.bot.get_chat_member(chat_id=channel_id, user_id=user.id)
        except Exception as e:
            print(f"⚠️ Ошибка проверки подписки: {e}")
            # Если ошибка (например, бот не админ), лучше пропустить юзера, чем блокировать
            return await handler(event, data)

        # Статусы, при которых пускаем: creator (создатель), administrator, member
        if member.status in ["creator", "administrator", "member"]:
            return await handler(event, data)

        # === ЕСЛИ НЕ ПОДПИСАН ===

        text_german = (
            "🚫 <b>Zugriff verweigert</b>\n\n"
            "Um diesen Bot zu nutzen, musst du unseren Kanal abonnieren.\n"
            "Bitte trete dem Kanal bei und klicke dann auf 'Überprüfen'."
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👉 Kanal beitreten", url=channel_url)],
            [InlineKeyboardButton(text="🔄 Überprüfen", callback_data="check_sub")]
        ])

        # Если это сообщение (текст)
        if isinstance(event, Message):
            await event.answer(text_german, parse_mode="HTML", reply_markup=keyboard)
        # Если это нажатие кнопки (Callback)
        elif isinstance(event, CallbackQuery):
            # Если нажали "check_sub" — мы не блокируем, а даем пройти дальше (там обработается)
            if event.data == "check_sub":
                # Но если он все еще не подписан, middleware снова сработает на следующем шаге
                # Поэтому мы просто отвечаем всплывашкой
                await event.answer("❌ Du bist noch nicht abonniert!", show_alert=True)
            else:
                await event.message.answer(text_german, parse_mode="HTML", reply_markup=keyboard)
                await event.answer()

        # Прерываем обработку (не вызываем handler)
        return