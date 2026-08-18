#!/usr/bin/env sh
set -eu

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 DATABASE_BACKUP.sql MEDIA_BACKUP.tar.gz"
    exit 1
fi

BACKEND_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$BACKEND_DIR/.." && pwd)
DATABASE_BACKUP=$1
MEDIA_BACKUP=$2

set -a
. "$PROJECT_DIR/.env"
set +a

printf 'This replaces the database and media. Type RESTORE to continue: '
read -r confirmation
[ "$confirmation" = "RESTORE" ] || exit 1

MYSQL_PWD="${DB_PASSWORD:-}" mysql \
    --host="$DB_HOST" \
    --port="${DB_PORT:-3306}" \
    --user="$DB_USER" \
    "$DB_NAME" < "$DATABASE_BACKUP"

mkdir -p "${MEDIA_ROOT:-$BACKEND_DIR/media}"
tar -xzf "$MEDIA_BACKUP" -C "${MEDIA_ROOT:-$BACKEND_DIR/media}"
echo "Restore completed. Run deploy.sh to restart Passenger."