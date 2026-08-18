#!/usr/bin/env sh
set -eu

BACKEND_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$BACKEND_DIR/.." && pwd)

if [ -z "${VIRTUAL_ENV:-}" ]; then
    echo "Activate the o2switch virtual environment before running this script."
    exit 1
fi

cd "$BACKEND_DIR"
python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ -x "$PROJECT_DIR/node_modules/.bin/vite" ]; then
    cd "$PROJECT_DIR"
    npm run build
    cd "$BACKEND_DIR"
    python manage.py collectstatic --noinput
fi

mkdir -p "$BACKEND_DIR/tmp"
touch "$BACKEND_DIR/tmp/restart.txt"

echo "Deployment completed. Passenger restart requested."