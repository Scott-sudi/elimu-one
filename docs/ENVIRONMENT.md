# Variables d'environnement

Copiez `.env.example` vers `.env`. `django-environ` lit ce fichier automatiquement
depuis la racine du depot. Il est ignore par Git.

## Local (SQLite)

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.development
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
SCHOOL_NAME=
SCHOOL_SLOGAN=
PLATFORM_NAME=ELIMU One
PLATFORM_TAGLINE=Système de gestion scolaire
```

Aucun serveur MySQL n'est requis sur la machine de developpement.

## Production minimale (MySQL)

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=generate-a-new-long-random-secret-for-production
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=institut-kalunga.net,www.institut-kalunga.net,institut-kalunga.net.susc3383.odns.fr
CSRF_TRUSTED_ORIGINS=https://institut-kalunga.net,https://www.institut-kalunga.net,https://institut-kalunga.net.susc3383.odns.fr,http://institut-kalunga.net.susc3383.odns.fr
DJANGO_SECURE_SSL_REDIRECT=True

DB_ENGINE=django.db.backends.mysql
DB_NAME=susc3383_kalunga
DB_USER=susc3383_kalunga_user
DB_PASSWORD=replace-with-the-mysql-password
DB_HOST=localhost
DB_PORT=3306

CORS_ALLOWED_ORIGINS=https://institut-kalunga.net,https://www.institut-kalunga.net,https://institut-kalunga.net.susc3383.odns.fr
EMAIL_HOST=mail.institut-kalunga.net
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@institut-kalunga.net
EMAIL_HOST_PASSWORD=replace-with-mail-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@institut-kalunga.net
SERVER_EMAIL=noreply@institut-kalunga.net
```

`DB_HOST` doit etre la valeur affichee dans cPanel si o2switch ne fournit pas
`localhost`. Les noms MySQL sont generalement prefixes par le compte cPanel (`susc3383_...`).

Incluez l'URL temporaire o2switch (`*.odns.fr`) dans `DJANGO_ALLOWED_HOSTS` tant
que le DNS public du `.net` n'est pas propage — sinon Passenger renvoie 400/502
sur l'URL de test.

## Fichiers et logs

Utilisez les chemins absolus o2switch (compte `susc3383`).

```dotenv
STATIC_ROOT=/home/susc3383/kalunga-school/backend/staticfiles
MEDIA_ROOT=/home/susc3383/kalunga-school/backend/media
DJANGO_LOG_DIR=/home/susc3383/kalunga-school/backend/logs
DJANGO_LOG_LEVEL=INFO
CACHE_LOCATION=kalunga-school
CACHE_DEFAULT_TIMEOUT=300
FILE_UPLOAD_MAX_MEMORY_SIZE=10485760
DATA_UPLOAD_MAX_MEMORY_SIZE=12582912
```

Ne mettez des guillemets dans `.env` que si une valeur contient un espace. Les scripts
de sauvegarde chargent ce fichier dans leur environnement shell.

| Variable | Usage |
|---|---|
| `DJANGO_SECRET_KEY` | Cle cryptographique Django, unique et secrete |
| `DJANGO_DEBUG` | Toujours `False` en production |
| `DJANGO_ALLOWED_HOSTS` | Domaines HTTP acceptes |
| `CSRF_TRUSTED_ORIGINS` | Origines HTTPS avec protocole |
| `DB_*` | Connexion MySQL o2switch |
| `EMAIL_*` | SMTP applicatif |
| `STATIC_ROOT` | Destination de `collectstatic` |
| `MEDIA_ROOT` | Photos, QR codes, documents, rapports et recus |
| `CORS_ALLOWED_ORIGINS` | Origines web autorisees pour l'API |

Pour Flutter mobile, ne mettez pas d'origine mobile dans CORS. Une application native
utilise `Authorization: Bearer` et ne depend pas de CORS.