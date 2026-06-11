#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for database..."
python - <<'PY'
import time, sys
from sqlalchemy import create_engine, text
from app.config import settings

for attempt in range(30):
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        print("Database is up.")
        sys.exit(0)
    except Exception as e:
        print(f"DB not ready ({attempt+1}/30): {e}")
        time.sleep(2)
sys.exit("Database never became available")
PY

echo "Running migrations..."
alembic upgrade head

echo "Starting Uvicorn..."
# PORT is provided by the platform (e.g. Render); default to 8000 locally.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}"
