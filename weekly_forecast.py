# weekly_forecast.py
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from database_sqlite import Database
except ImportError:
    from database import Database

from numerology_core import reduce_to_single, personal_year
from interpret import send_to_n8n_for_interpretation
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

db = Database()


async def get_active_subscribers() -> List[Dict[str, Any]]:
    """Получает список активных подписчиков (статус active или trial, push_enabled = True)."""
    try:
        await db.init()
        subscriptions = await db.get_active_subscribers()
        return subscriptions
    except Exception as e:
        logger.error(f"Ошибка получения подписчиков: {e}")
        return []


async def generate_weekly_forecast(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Генерирует еженедельный прогноз для пользователя."""
    try:
        birthdate_str = user_data.get("birthdate")
        fio = user_data.get("fio")
        if not birthdate_str or not fio:
            return {"error": "Недостаточно данных"}
        birthdate = datetime.strptime(birthdate_str, "%Y-%m-%d").date()
        now = datetime.now()
        week_number = reduce_to_single(now.isocalendar()[1])
        py = personal_year(birthdate)

        forecast_data = {
            "user": {"fio": fio, "birthdate": birthdate_str},
            "forecast": {
                "week_number": week_number,
                "personal_year": py,
                "date_from": (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d"),
                "date_to": (now + timedelta(days=6 - now.weekday())).strftime("%Y-%m-%d")
            }
        }
        interpretation = await send_to_n8n_for_interpretation(forecast_data, "weekly")
        return interpretation
    except Exception as e:
        logger.error(f"Ошибка генерации прогноза: {e}")
        return {"error": str(e)}


async def send_forecast_to_user(bot: Bot, tg_id: int, forecast: Dict[str, Any]) -> bool:
    """
    Отправляет прогноз пользователю.
    Принимает переданный экземпляр бота, чтобы не создавать новый.
    """
    try:
        if "error" in forecast:
            logger.error(f"Ошибка прогноза для {tg_id}: {forecast['error']}")
            return False

        # Извлекаем текст прогноза
        text = forecast.get("weekly_forecast", "")
        if not text:
            logger.warning(f"Пустой прогноз для {tg_id}")
            return False

        # Форматируем даты недели
        now = datetime.now()
        date_from = (now - timedelta(days=now.weekday())).strftime("%d.%m.%Y")
        date_to = (now + timedelta(days=6 - now.weekday())).strftime("%d.%m.%Y")

        message = (
            f"🔮 <b>Ваш еженедельный нумерологический прогноз</b>\n"
            f"<i>на период {date_from} - {date_to}</i>\n\n"
            f"{text}\n\n"
            f"Хорошей недели! Ваш Супер-Нумеролог."
        )

        await bot.send_message(chat_id=tg_id, text=message)

        # Сохраняем историю отправленного прогноза в БД
        try:
            await db.save_forecast_history(tg_id, text[:500])  # обрезаем для краткости
        except Exception as e:
            logger.error(f"Ошибка сохранения истории прогноза для {tg_id}: {e}")

        return True
    except Exception as e:
        logger.error(f"Ошибка отправки прогноза {tg_id}: {e}")
        return False


async def process_weekly_forecasts(bot: Bot):
    """
    Основная функция отправки еженедельных прогнозов.
    Принимает экземпляр бота.
    """
    try:
        logger.info("Начало отправки еженедельных прогнозов")
        subscribers = await get_active_subscribers()
        logger.info(f"Найдено {len(subscribers)} подписчиков")

        success = 0
        for sub in subscribers:
            tg_id = sub.get("tg_id")
            if not tg_id:
                continue

            forecast = await generate_weekly_forecast(sub)
            if await send_forecast_to_user(bot, tg_id, forecast):
                success += 1

            # Небольшая задержка между отправками, чтобы не превысить лимиты
            await asyncio.sleep(0.2)

        logger.info(f"Отправлено успешно: {success}/{len(subscribers)}")

    except Exception as e:
        logger.error(f"Ошибка в процессе отправки прогнозов: {e}")
    finally:
        # Не закрываем сессию бота, т.к. она управляется извне
        pass


# Для запуска вручную (для отладки) – передаём бота извне
if __name__ == "__main__":
    # Для теста можно создать бота локально, но обычно запускается через scheduler
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не найден!")
        sys.exit(1)
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        asyncio.run(process_weekly_forecasts(bot))
    finally:
        asyncio.run(bot.session.close())
