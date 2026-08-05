# logger.py
import logging
import uuid
from datetime import datetime

class ContextLogger:
    """
    Логгер с поддержкой контекстных полей (user_id, session_id и т.д.).
    """
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context = {}
        # Настройка форматирования по умолчанию
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def set_context(self, **kwargs):
        """Устанавливает поля контекста."""
        self.context.update(kwargs)

    def clear_context(self):
        """Очищает контекст."""
        self.context.clear()

    def _format(self, msg: str) -> str:
        """Добавляет контекстные поля к сообщению."""
        if self.context:
            ctx = " ".join([f"{k}={v}" for k, v in self.context.items()])
            return f"[{ctx}] {msg}"
        return msg

    def info(self, msg: str, *args, **kwargs):
        self.logger.info(self._format(msg), *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self.logger.error(self._format(msg), *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self.logger.warning(self._format(msg), *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs):
        self.logger.debug(self._format(msg), *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        self.logger.critical(self._format(msg), *args, **kwargs)

def setup_logging(log_file: str = "bot.log", level=logging.INFO):
    """
    Настраивает глобальное логирование в файл и консоль.
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

# Создаём глобальный экземпляр для использования в проекте
logger = ContextLogger("super_bot")
