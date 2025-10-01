    #!/usr/bin/env bash
    set -euo pipefail

    # Default envs
    : "${DJANGO_SETTINGS_MODULE:=config.settings}"
    : "${DB_HOST:=db}"
    : "${DB_PORT:=3306}"
    : "${GUNICORN_WORKERS:=3}"
    : "${GUNICORN_TIMEOUT:=120}"

    echo "[entrypoint] Waiting for database $DB_HOST:$DB_PORT ..."
    python - <<'PY'
import os, socket, time, sys
host=os.environ.get("DB_HOST","db")
port=int(os.environ.get("DB_PORT","3306"))
for i in range(90):
    try:
        s=socket.create_connection((host,port),2); s.close()
        print("DB reachable"); break
    except OSError:
        time.sleep(2)
else:
    sys.exit("Database not reachable after timeout")
PY

    echo "[entrypoint] Running migrations & collectstatic ..."
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput || true

    echo "[entrypoint] Starting gunicorn ..."
    exec gunicorn config.wsgi:application         --bind 0.0.0.0:8000         --workers "${GUNICORN_WORKERS}"         --timeout "${GUNICORN_TIMEOUT}"
