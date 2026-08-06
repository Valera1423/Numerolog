# Используем официальный образ Python 3.11
FROM python:3.11-slim

# Установка системных зависимостей для Playwright (Chromium) и работы с PDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    libnss3 \
    libatk-bridge-2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Директория для постоянных данных: БД, PDF-отчёты, логи
# Монтируется как Docker volume — данные сохраняются при перезапуске
ENV DATA_DIR=/app/data
RUN mkdir -p /app/data && chmod 777 /app/data
# Устанавливаем владельца (попытка использовать текущего пользователя или fallback)
RUN chown -R $(id -u):$(id -g) /app/data 2>/dev/null || chown -R 1000:1000 /app/data || true

# Копируем файл зависимостей и устанавливаем Python-библиотеки
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем Playwright и браузеры (Chromium) для генерации PDF
RUN pip install playwright && playwright install chromium

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
