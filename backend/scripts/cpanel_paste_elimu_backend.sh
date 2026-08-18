#!/bin/bash
# Déploie le backend ELIMU (push + inbox) depuis GitHub, puis redémarre.
set -e
cd ~/elimu-school || { echo ELIMU_SCHOOL_NOT_FOUND; exit 1; }
if [ -d .git ]; then
  git fetch origin
  git pull --ff-only origin master || git pull --ff-only origin main
else
  echo "PAS_DE_GIT — mettez à jour le code autrement, puis relancez cpanel_paste_elimu_fcm.sh"
fi
cd backend
if [ -f ../.env ]; then ENV=../.env; elif [ -f .env ]; then ENV=.env; else ENV=../.env; touch "$ENV"; fi
grep -q '^FCM_PROJECT_ID=' "$ENV" 2>/dev/null && sed -i 's/^FCM_PROJECT_ID=.*/FCM_PROJECT_ID=elimu-go/' "$ENV" || echo 'FCM_PROJECT_ID=elimu-go' >> "$ENV"
grep -q '^FCM_SERVICE_ACCOUNT_FILE=' "$ENV" 2>/dev/null && sed -i 's|^FCM_SERVICE_ACCOUNT_FILE=.*|FCM_SERVICE_ACCOUNT_FILE=secrets/firebase-adminsdk.json|' "$ENV" || echo 'FCM_SERVICE_ACCOUNT_FILE=secrets/firebase-adminsdk.json' >> "$ENV"
VENV=$(ls -d ~/virtualenv/elimu-school/backend/*/bin/activate 2>/dev/null | head -n 1 || true)
if [ -n "$VENV" ]; then source "$VENV"; fi
python manage.py collectstatic --noinput || true
mkdir -p tmp
touch tmp/restart.txt
echo DONE_BACKEND_PUSH
echo "Ensuite : cPanel → Setup Python App → Restart, puis coller cpanel_paste_elimu_fcm.sh"
