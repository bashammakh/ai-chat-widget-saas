# --- Backend image: FastAPI + Uvicorn ---
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for psycopg2 build are avoided by using psycopg2-binary.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Run migrations then start the server.
RUN chmod +x ./entrypoint.sh
EXPOSE 8000

CMD ["./entrypoint.sh"]
