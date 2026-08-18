FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/backend

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend

RUN addgroup --system setup-leitos \
    && adduser --system --ingroup setup-leitos setup-leitos \
    && chown -R setup-leitos:setup-leitos /app

USER setup-leitos

EXPOSE 8000

# Um único worker preserva o broadcast WebSocket em memória.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips=*"]
