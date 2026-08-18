#!/usr/bin/env sh
set -eu

BACKEND_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$BACKEND_DIR/.." && pwd)
BACKUP_DIR=${1:-"$PROJECT_DIR/backups"}
STAMP=$(date +%Y%m%d-%H%M%S)

set -a
. "$PROJECT_DIR/.env"
set +a

mkdir -p "$BACKUP_DIR"
MYSQL_PWD="${DB_PASSWORD:-}" mysqldump \
    --host="$DB_HOST" \
    --port="${DB_PORT:-3306}" \
    --user="$DB_USER" \
    --single-transaction \
    --default-character-set=utf8mb4 \
    "$DB_NAME" > "$BACKUP_DIR/${DB_NAME}-${STAMP}.sql"

tar -czf "$BACKUP_DIR/media-${STAMP}.tar.gz" -C "${MEDIA_ROOT:-$BACKEND_DIR/media}" .
echo "Backup created in $BACKUP_DIR"