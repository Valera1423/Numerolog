FROM python:3.11-slim

# Базовые системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Директория для постоянных данных
ENV DATA_DIR=/app/data
RUN mkdir -p /app/data && chmod 777 /app/data
RUN chown -R $(id -u):$(id -g) /app/data 2>/dev/null || chown -R 1000:1000 /app/data || true

# Копируем requirements и устанавливаем зависимости
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
    tenacity>=8.2.0 \
    redis>=5.0.0
# Для отправки ошибок (sentry-sdk уже включён)

# Устанавливаем Playwright и системные зависимости
RUN pip install playwright && \
    playwright install-deps && \
    playwright install chromium

# Копируем весь код, включая папку data
COPY . .

# Явно копируем папку data (если она есть на хосте), чтобы файлы были внутри образа
# Это гарантирует, что даже при пустом томе файлы будут доступны
COPY data /app/data

# Проверяем, что файлы действительно скопировались (вывод в лог для отладки)
RUN ls -la /app/data || echo "Папка data пуста"

# Entrypoint
RUN echo '#!/bin/sh' > /usr/local/bin/entrypoint.sh && \
    echo 'set -e' >> /usr/local/bin/entrypoint.sh && \
    echo '# Инициализация прав на /app/data' >> /usr/local/bin/entrypoint.sh && \
    echo 'mkdir -p /app/data' >> /usr/local/bin/entrypoint.sh && \
    echo 'chmod 777 /app/data' >> /usr/local/bin/entrypoint.sh && \
    echo 'chown -R $(id -u):$(id -g) /app/data 2>/dev/null || true' >> /usr/local/bin/entrypoint.sh && \
    echo 'exec "$@"' >> /usr/local/bin/entrypoint.sh && \
    chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

CMD ["python", "bot.py"]
