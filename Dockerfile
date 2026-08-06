# Используем официальный образ Python 3.11
FROM python:3.11-slim

# Установка только базовых системных зависимостей, необходимых для некоторых Python-библиотек
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Директория для постоянных данных: БД, PDF-отчёты, логи
ENV DATA_DIR=/app/data
RUN mkdir -p /app/data && chmod 777 /app/data
# Устанавливаем владельца (попытка использовать текущего пользователя или fallback)
RUN chown -R $(id -u):$(id -g) /app/data 2>/dev/null || chown -R 1000:1000 /app/data || true

# Копируем файл зависимостей и устанавливаем Python-библиотеки
COPY requirements.txt .
RUN pip install --no-cache-dir \
    aiogram>=3.0.0 \
    aiohttp>=3.8.3 \
    jinja2>=3.1.2 \
    pillow>=9.5.0 \
    python-dotenv>=1.0.0 \
    playwright>=1.40.0 \
    apscheduler>=3.10.0 \
    sentry-sdk>=1.40.0 \
    tenacity>=8.2.0

# Устанавливаем Playwright и все системные зависимости через официальный инструмент
RUN pip install playwright && \
    playwright install-deps && \
    playwright install chromium

# Копируем весь код проекта
COPY . .

# Создаём entrypoint-скрипт для инициализации прав на /app/data
RUN echo '#!/bin/sh' > /usr/local/bin/entrypoint.sh && \
    echo 'set -e' >> /usr/local/bin/entrypoint.sh && \
    echo '# Инициализация прав на /app/data (важно для volume)' >> /usr/local/bin/entrypoint.sh && \
    echo 'mkdir -p /app/data' >> /usr/local/bin/entrypoint.sh && \
    echo 'chmod 777 /app/data' >> /usr/local/bin/entrypoint.sh && \
    echo 'chown -R $(id -u):$(id -g) /app/data 2>/dev/null || true' >> /usr/local/bin/entrypoint.sh && \
    echo '# Запускаем основное приложение' >> /usr/local/bin/entrypoint.sh && \
    echo 'exec "$@"' >> /usr/local/bin/entrypoint.sh && \
    chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Запускаем главный файл бота
CMD ["python", "bot.py"]
