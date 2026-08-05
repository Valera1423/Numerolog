# scheduler.py
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from weekly_forecast import process_weekly_forecasts
from aiogram import Bot

logger = logging.getLogger(__name__)

scheduler = None

def start_scheduler(bot: Bot):
    global scheduler
    if scheduler is not None:
        return
    scheduler = AsyncIOScheduler()
    # Запуск каждое воскресенье в 10:00 (или понедельник, как вам нужно)
    scheduler.add_job(
        lambda: asyncio.create_task(process_weekly_forecasts()),
        trigger=CronTrigger(day_of_week='sun', hour=10, minute=0)
    )
    scheduler.start()
    logger.info("Планировщик еженедельных прогнозов запущен.")