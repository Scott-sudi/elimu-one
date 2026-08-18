# Installation locale

## Prerequis

- Python 3.10 ou plus recent
- MySQL 8
- Node.js 20 ou plus recent et npm

## Installation Windows

Depuis la racine du depot :

```powershell
Copy-Item .env.example .env
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements\development.txt
npm install
npm run build
Set-Location backend
python manage.py migrate
python manage.py initialize_roles
python manage.py runserver
```

Le fichier `.env` local doit conserver
`DJANGO_SETTINGS_MODULE=config.settings.development`. La base locale par defaut est
`kalunga_school` sur `127.0.0.1`, avec l'utilisateur `root` sans mot de passe.

## Verification locale

```powershell
python manage.py check
python manage.py test
python manage.py collectstatic --noinput
```

Ne copiez jamais le fichier `.env` local sur un serveur de production.