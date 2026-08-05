# redis_cache.py
import os
import json
import logging
from typing import Any, Optional
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Загрузка переменных окружения
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_TTL = int(os.getenv("REDIS_TTL", "3600"))  # по умолчанию 1 час

# Создаём клиент Redis с автоматическим декодированием
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=5)
except Exception as e:
    logger.error(f"Не удалось подключиться к Redis: {e}")
    redis_client = None

async def cache_get(key: str) -> Optional[Any]:
    """
    Получает значение из кеша по ключу.
    Возвращает десериализованный объект или None, если ключ отсутствует или Redis недоступен.
    """
    if redis_client is None:
        return None
    try:
        data = await redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении из кеша (key={key}): {e}")
        return None

async def cache_set(key: str, value: Any, ttl: int = REDIS_TTL):
    """
    Сохраняет значение в кеш с заданным TTL (в секундах).
    Значение сериализуется в JSON.
    """
    if redis_client is None:
        return
    try:
        serialized = json.dumps(value, default=str)
        await redis_client.setex(key, ttl, serialized)
    except Exception as e:
        logger.error(f"Ошибка при сохранении в кеш (key={key}): {e}")

async def cache_delete(key: str):
    """Удаляет ключ из кеша."""
    if redis_client is None:
        return
    try:
        await redis_client.delete(key)
    except Exception as e:
        logger.error(f"Ошибка при удалении из кеша (key={key}): {e}")

async def cache_clear():
    """Очищает весь кеш (осторожно!)."""
    if redis_client is None:
        return
    try:
        await redis_client.flushdb()
    except Exception as e:
        logger.error(f"Ошибка при очистке кеша: {e}")

# ========== Примеры использования ==========
# async def get_user_report(user_id):
#     key = f"report:{user_id}"
#     cached = await cache_get(key)
#     if cached:
#         return cached
#     # ... генерация отчёта ...
#     await cache_set(key, report_data)
#     return report_data
