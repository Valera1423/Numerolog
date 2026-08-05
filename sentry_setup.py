# sentry_setup.py
import os
import logging
import sentry_sdk
from sentry_sdk.integrations.aiogram import AiogramIntegration

logger = logging.getLogger(__name__)

def init_sentry():
    """
    Инициализирует Sentry SDK, если задан DSN.
    """
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        logger.info("Sentry DSN не задан, мониторинг ошибок отключён.")
        return

    try:
        sentry_sdk.init(
            dsn=dsn,
            integrations=[AiogramIntegration()],
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0")),
            environment=os.getenv("ENVIRONMENT", "production"),
            # Можно добавить дополнительные настройки
        )
        logger.info("Sentry успешно инициализирован.")
    except Exception as e:
        logger.error(f"Ошибка при инициализации Sentry: {e}")

# В bot.py в main():
# from sentry_setup import init_sentry
# init_sentry()
