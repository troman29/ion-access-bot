FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/troman29/tontokengate-bot" \
      org.opencontainers.image.description="Telegram bot that grants access to private chats by ION and ION jettons." \
      org.opencontainers.image.licenses="MIT"

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "app"]
