#!/bin/bash
# ELIMU Go — FCM projet elimu-go (PAS institut-kalunga).
# Ne contient aucune clé privée. Uploadez firebase-adminsdk.json via File Manager.
set -e
cd ~/elimu-school/backend || { echo "ELIMU_SCHOOL_NOT_FOUND"; exit 1; }
pwd
mkdir -p secrets tmp
SA="secrets/firebase-adminsdk.json"
if [ ! -f "$SA" ]; then
  echo "MANQUE $SA"
  echo "Dans File Manager : copiez la clé JSON Firebase ELIMU Go ici,"
  echo "renommez-la firebase-adminsdk.json"
  exit 1
fi
if [ -f ../.env ]; then ENV=../.env; elif [ -f .env ]; then ENV=.env; else ENV=../.env; touch "$ENV"; fi
grep -q '^FCM_PROJECT_ID=' "$ENV" 2>/dev/null && sed -i 's/^FCM_PROJECT_ID=.*/FCM_PROJECT_ID=elimu-go/' "$ENV" || echo 'FCM_PROJECT_ID=elimu-go' >> "$ENV"
grep -q '^FCM_SERVICE_ACCOUNT_FILE=' "$ENV" 2>/dev/null && sed -i 's|^FCM_SERVICE_ACCOUNT_FILE=.*|FCM_SERVICE_ACCOUNT_FILE=secrets/firebase-adminsdk.json|' "$ENV" || echo 'FCM_SERVICE_ACCOUNT_FILE=secrets/firebase-adminsdk.json' >> "$ENV"
echo "ENV=$ENV"
python3 - <<'PY'
import json
from pathlib import Path
raw = json.loads(Path("secrets/firebase-adminsdk.json").read_text(encoding="utf-8"))
pid = raw.get("project_id")
print("SA_PROJECT", pid)
if pid != "elimu-go":
    raise SystemExit(f"MAUVAISE CLE : project_id={pid} (attendu elimu-go, pas Kalunga)")
print("SA_EMAIL", raw.get("client_email"))
PY
VENV=$(ls -d ~/virtualenv/elimu-school/backend/*/bin/activate 2>/dev/null | head -n 1 || true)
if [ -n "$VENV" ]; then source "$VENV"; fi
pip install 'google-auth>=2.29' -q || python3 -m pip install 'google-auth>=2.29' -q || true
python3 - <<'PY'
from google.oauth2 import service_account
from google.auth.transport.requests import Request
creds = service_account.Credentials.from_service_account_file(
    'secrets/firebase-adminsdk.json',
    scopes=['https://www.googleapis.com/auth/firebase.messaging'],
)
creds.refresh(Request())
print('FCM_AUTH_OK', bool(creds.token))
PY
python manage.py send_test_parent_push --help >/dev/null
touch tmp/restart.txt
echo DONE_ELIMU_FCM
