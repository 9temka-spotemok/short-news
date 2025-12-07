FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements отдельно
COPY backend/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь backend
COPY backend/ ./backend/

WORKDIR /app/backend

# Запуск backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

