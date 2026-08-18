"""Build a single cPanel paste script (no ZIP) for Horaires + guardian ID."""

from __future__ import annotations

import base64
import gzip
import io
import tarfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parents[3] / "COLLER_DANS_TERMINAL_HORAIRES_RESPONSABLES.sh"

FILES = [
    "apps/secretariat/models/academic.py",
    "apps/secretariat/migrations/0005_schoolclass_vacation.py",
    "apps/discipline/models.py",
    "apps/discipline/migrations/0004_vacation_and_schedule_present_until.py",
    "apps/discipline/admin.py",
    "apps/discipline/services/attendance_service.py",
    "apps/discipline/services/class_attendance_service.py",
    "apps/discipline/services/schedule_service.py",
    "apps/discipline/forms.py",
    "apps/discipline/views.py",
    "apps/discipline/urls.py",
    "templates/discipline/schedules/index.html",
    "templates/discipline/dashboard/index.html",
    "templates/components/navbar.html",
    "apps/secretariat/services/guardian_identification_service.py",
    "apps/secretariat/services/guardian_service.py",
    "apps/secretariat/forms/enrollment.py",
    "apps/secretariat/forms/guardian.py",
    "apps/secretariat/views/class_enrollments.py",
    "apps/secretariat/api/serializers.py",
    "templates/secretariat/classes/enroll.html",
    "templates/secretariat/classes/reenroll.html",
    "templates/secretariat/classes/_guardian_lookup_js.html",
    "templates/secretariat/guardians/detail.html",
    "templates/secretariat/guardians/update.html",
    "templates/secretariat/guardians/_table.html",
    "static/src/js/pages/secretariat/classes.js",
    "static/src/css/components/inputs.css",
]


def main() -> None:
    missing = [rel for rel in FILES if not (BACKEND / rel).is_file()]
    if missing:
        raise SystemExit("Missing files: " + ", ".join(missing))

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for rel in FILES:
            tar.add(BACKEND / rel, arcname=rel.replace("\\", "/"))
    raw = gzip.compress(buf.getvalue(), compresslevel=9)
    b64 = base64.b64encode(raw).decode("ascii")
    wrapped = "\n".join(b64[i : i + 76] for i in range(0, len(b64), 76))

    script = f"""# ===== UN SEUL COLLAGE — Horaires + ID responsable automatique =====
# Terminal cPanel : coller TOUT ce bloc, puis Entrée.
# Pas de ZIP. Pas de seed. Conserve .env / media / photos.
set +e
cd ~/kalunga-school/backend || {{ echo BACKEND_NOT_FOUND; exit 1; }}

python3 - <<'PY'
import base64, gzip, io, tarfile, pathlib
payload = \"\"\"
{wrapped}
\"\"\"
raw = base64.b64decode(''.join(payload.split()))
buf = io.BytesIO(gzip.decompress(raw))
root = pathlib.Path('.')
count = 0
with tarfile.open(fileobj=buf, mode='r:') as tar:
    for member in tar.getmembers():
        if not member.isfile():
            continue
        name = member.name.replace('\\\\', '/').lstrip('/')
        if '..' in name:
            raise SystemExit('BAD_PATH ' + name)
        dest = root / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        src = tar.extractfile(member)
        dest.write_bytes(src.read())
        count += 1
        print('WROTE', name)
print('FILES_OK', count)
PY

VENV=$(ls -d ~/virtualenv/kalunga-school/backend/*/bin/activate 2>/dev/null | head -n 1)
[ -z "$VENV" ] && VENV=$(ls -d ~/virtualenv/kalunga-school/*/bin/activate 2>/dev/null | head -n 1)
[ -z "$VENV" ] && {{ echo VENV_NOT_FOUND; exit 1; }}
. "$VENV"
mkdir -p tmp staticfiles logs media

echo "=== migrate ==="
python manage.py migrate --noinput
echo MIGRATE_RC=$?

echo "=== collectstatic ==="
python manage.py collectstatic --noinput
echo COLLECTSTATIC_RC=$?

python manage.py shell -c "
from django.urls import reverse
from apps.secretariat.models import SchoolClass
print('vacation=', hasattr(SchoolClass, 'vacation'))
print('schedules=', reverse('discipline:schedules'))
print('lookup=', reverse('secretariat:guardian-phone-lookup'))
print('OK')
"

touch tmp/restart.txt
touch passenger_wsgi.py 2>/dev/null || true
echo ===== FIN =====
echo Discipline: Horaires
echo Secretariat: inscription = ID automatique
echo DONE
"""
    OUT.write_text(script, encoding="utf-8", newline="\n")
    print(f"WROTE {OUT}")
    print(f"SIZE {OUT.stat().st_size}")
    print(f"GZ {len(raw)} B64 {len(b64)}")


if __name__ == "__main__":
    main()
