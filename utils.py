# utils.py
import asyncio
import re
from datetime import datetime
from typing import Optional, Callable, Any, TypeVar, Coroutine
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

logger = logging.getLogger(__name__)

# ========== Валидация данных ==========

def validate_date(date_str: str) -> Optional[datetime.date]:
    """
    Проверяет строку на формат ДД.ММ.ГГГГ и возвращает объект date или None.
    """
    try:
        return datetime.strptime(date_str, "%d.%m.%Y").date()
    except ValueError:
        return None

def validate_fio(fio: str) -> bool:
    """
    Проверяет, что ФИО содержит только буквы (русские/английские), пробелы и дефисы.
    """
    return bool(re.match(r'^[а-яА-ЯёЁa-zA-Z\s\-]+$', fio.strip()))

# ========== Фоновые задачи ==========

def run_in_background(coro: Coroutine) -> asyncio.Task:
    """
    Запускает корутину в фоновом режиме (не блокирует текущий поток).
    Возвращает объект Task, который можно отслеживать при необходимости.
    """
    return asyncio.create_task(coro)

# ========== Повторные попытки с экспоненциальной задержкой ==========

def retry_n8n(func=None, *, stop_attempts: int = 3, wait_multiplier: float = 1.0, wait_max: float = 10):
    """
    Декоратор для повторных попыток вызова n8n с экспоненциальной задержкой.
    Использует библиотеку tenacity.
    """
    if func is None:
        return lambda f: retry_n8n(f, stop_attempts=stop_attempts, wait_multiplier=wait_multiplier, wait_max=wait_max)
    
    return retry(
        stop=stop_after_attempt(stop_attempts),
        wait=wait_exponential(multiplier=wait_multiplier, min=2, max=wait_max),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )(func)

# Пример использования:
# @retry_n8n
# async def call_n8n(data): ...

# ========== Другие полезные функции ==========

def format_datetime(dt: Optional[datetime] = None) -> str:
    """Возвращает строку с текущим временем в формате ДД.ММ.ГГГГ ЧЧ:ММ:СС."""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%d.%m.%Y %H:%M:%S")

def truncate_text(text: str, max_len: int = 200) -> str:
    """Обрезает текст до заданной длины, добавляя многоточие."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."
