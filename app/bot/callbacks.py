from aiogram.filters.callback_data import CallbackData

# Структура для кнопки "Добавить/Удалить"
# action: 'add' (добавить), 'del' (удалить), 'show' (показать детали)
# id: ID квартиры в нашей базе
class FavCallback(CallbackData, prefix="fav"):
    action: str
    id: int