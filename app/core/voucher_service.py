import secrets
import string
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.voucher import Voucher
from app.models.settings import Settings


def generate_code(length=8):
    """Генерирует случайный код типа A1B2-C3D4"""
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(secrets.choice(chars) for _ in range(length // 2))
    part2 = ''.join(secrets.choice(chars) for _ in range(length // 2))
    return f"{part1}-{part2}"


def create_voucher(db: Session, days: int) -> str:
    """Создает ваучер в базе"""
    code = generate_code()
    # Проверка на уникальность (маловероятно, но на всякий случай)
    while db.query(Voucher).filter(Voucher.code == code).first():
        code = generate_code()

    voucher = Voucher(code=code, days=days)
    db.add(voucher)
    db.commit()
    return code


def redeem_voucher(db: Session, user_id: int, code: str) -> str:
    """Активирует ваучер для пользователя"""
    voucher = db.query(Voucher).filter(Voucher.code == code, Voucher.is_used == False).first()

    if not voucher:
        return "❌ Ungültiger oder bereits benutzter Code."

    settings = db.query(Settings).filter(Settings.user_id == user_id).first()
    if not settings:
        # Если юзера нет в базе (странно, но создадим)
        settings = Settings(user_id=user_id)
        db.add(settings)

    # Логика продления
    now = datetime.now()
    if settings.premium_until and settings.premium_until > now:
        # Если уже есть премиум — добавляем дни к текущей дате окончания
        settings.premium_until += timedelta(days=voucher.days)
    else:
        # Если нет — добавляем к "сейчас"
        settings.premium_until = now + timedelta(days=voucher.days)

    settings.is_premium = True
    voucher.is_used = True  # Помечаем как использованный

    db.commit()

    date_str = settings.premium_until.strftime("%d.%m.%Y")
    return f"✅ <b>Erfolg!</b> Premium aktiviert bis: {date_str}"