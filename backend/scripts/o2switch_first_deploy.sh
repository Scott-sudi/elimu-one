#!/usr/bin/env sh
# Premier déploiement ELIMU One sur o2switch (Terminal cPanel).
# Usage : activer le venv Python App, puis :
#   cd ~/elimu-school && sh backend/scripts/o2switch_first_deploy.sh

set -eu

BACKEND_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PROJECT_DIR="$(CDPATH= cd -- "$BACKEND_DIR/.." && pwd)"

if [ -z "${VIRTUAL_ENV:-}" ]; then
  echo "Erreur : activez d'abord l'environnement virtuel Python App (source .../bin/activate)."
  exit 1
fi

if [ ! -f "$PROJECT_DIR/.env" ]; then
  echo "Erreur : créez $PROJECT_DIR/.env depuis .env.production.example"
  exit 1
fi

cd "$BACKEND_DIR"
echo "=== Migrations ==="
python manage.py migrate --noinput

echo "=== Rôles & secrétariat ==="
python manage.py initialize_roles
python manage.py initialize_secretariat

echo "=== Assets statiques ==="
python manage.py collectstatic --noinput

if [ -x "$PROJECT_DIR/node_modules/.bin/vite" ]; then
  echo "=== Build Vite ==="
  cd "$PROJECT_DIR"
  npm ci
  npm run build
  cd "$BACKEND_DIR"
  python manage.py collectstatic --noinput
fi

echo "=== Année & horaires ==="
python manage.py ensure_open_academic_year
python manage.py ensure_attendance_schedules --strict-hours

echo "=== Contrôle déploiement ==="
python manage.py check --deploy

mkdir -p "$BACKEND_DIR/tmp"
touch "$BACKEND_DIR/tmp/restart.txt"

echo ""
echo "OK — Redémarrez Python App dans cPanel si besoin."
echo "Puis ouvrez : https://VOTRE-DOMAINE/setup/ (première fois) ou /connexion/"
