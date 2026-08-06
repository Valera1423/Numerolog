# scheduler.py
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from weekly_forecast import process_weekly_forecasts

logger = logging.getLogger(__name__)

scheduler = None
_bot_instance = None  # сохраняем переданный экземпляр бота


def start_scheduler(bot: Bot):
    """
    Запускает планировщик для еженедельной рассылки прогнозов.
    Принимает экземпляр Bot, чтобы не создавать новый.
    """
    global scheduler, _bot_instance

    if scheduler is not None:
        logger.info("Планировщик уже запущен.")
        return

    _bot_instance = bot
    scheduler = AsyncIOScheduler()

    # Запуск каждое воскресенье в 10:00 (можно изменить)
    scheduler.add_job(
        lambda: asyncio.create_task(process_weekly_forecasts(_bot_instance)),
        trigger=CronTrigger(day_of_week='sun', hour=10, minute=0)
    )
    scheduler.start()
    logger.info("Планировщик еженедельных прогнозов запущен.")


def stop_scheduler():
    """Останавливает планировщик (если нужно)."""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        scheduler = None
        logger.info("Планировщик остановлен.")
