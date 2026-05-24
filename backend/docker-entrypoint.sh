#!/bin/sh
set -e
echo "Waiting for PostgreSQL..."
python <<'PY'
import socket, time
host, port, deadline = "db", 5432, time.time() + 90
while time.time() < deadline:
    try:
        s = socket.create_connection((host, port), 2)
        s.close()
        print("PostgreSQL is accepting connections.")
        break
    except OSError:
        time.sleep(1)
else:
    raise SystemExit("Timed out waiting for PostgreSQL.")
PY

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting API..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 30
