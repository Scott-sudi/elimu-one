# ELIMU One — Système de gestion scolaire

Plateforme web **ELIMU One** (personnel Django) + application parents **ELIMU Go** (Flutter).
Chaque établissement configure son identité (nom, adresse, logo) via les variables `SCHOOL_*`.

En local, la base par défaut est **SQLite** (aucun MySQL / Wamp requis).
En hébergement, passez `DB_ENGINE=django.db.backends.mysql`.

## Versions utilisées

| Composant | Version |
|-----------|---------|
| Python | 3.13.12 |
| Django | 5.2.16 (LTS) |
| MySQL (hébergement) | 8.x |
| SQLite (local) | inclus avec Python |
| Node.js | 24.14.1 |
| npm | 11.11.0 |
| Vite | 6.4.x |
| Connecteur MySQL | PyMySQL 1.1+ |

## Structure

```
kalunga-school/
├── backend/          # Application Django
├── mobile/kalunga_parents/  # Réservé Flutter (.gitkeep)
├── docs/
├── .env.example
├── package.json
└── README.md
```

## Démarrage local

```powershell
# 1. Activer l’environnement virtuel
cd kalunga-school
.\.venv\Scripts\Activate.ps1

# 2. SQLite est utilisé automatiquement (fichier backend/db.sqlite3)
#    Pour MySQL en local : DB_ENGINE=django.db.backends.mysql dans .env

# 3. Installer les dépendances (si besoin)
pip install -r backend\requirements\development.txt
npm install

# 4. Appliquer les migrations
cd backend
python manage.py migrate
python manage.py initialize_roles

# 5. Compiler les assets Vite (depuis la racine du dépôt)
cd ..
npm run build

# 6. Démarrer Django
cd backend
python manage.py runserver
```

Ouvrir : http://127.0.0.1:8000

### Première configuration

Si aucun administrateur n’existe, l’application redirige vers `/setup/`.

Remplir le formulaire du **premier administrateur** (aucun compte n’est inventé par le système).

Ensuite : `/connexion/` → tableau de bord.

## Modules de cette phase

- Configuration initiale `/setup/`
- Connexion / déconnexion
- Tableau de bord administrateur
- Gestion des utilisateurs (CRUD, rôles, activation, archivage, reset MDP)
- Rôles et permissions (consultation)
- Historique des connexions
- Journal d’activités
- Mon profil
- API REST `/api/v1/` + JWT pour Flutter (infrastructure)

## Non développé (volontairement)

Secrétariat, comptabilité, discipline, élèves, parents, paiements, présences, Flutter, BI.

## Tests

```powershell
cd kalunga-school
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "$PWD\backend"
pytest backend\tests -c backend\pytest.ini
```

Les tests utilisent SQLite (`config.settings.test`) pour éviter les contraintes de création de base MySQL sous Windows.

## Documentation

- [docs/API.md](docs/API.md) — endpoints REST
- [docs/RAPPORT-PHASE-ADMIN.md](docs/RAPPORT-PHASE-ADMIN.md) — rapport de phase
- [docs/INSTALL.md](docs/INSTALL.md) - installation locale
- [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md) - variables d'environnement
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - deploiement o2switch
- [docs/PRODUCTION.md](docs/PRODUCTION.md) - exploitation de production
- [docs/BACKUP.md](docs/BACKUP.md) - sauvegarde et restauration

## Sécurité

- Mots de passe hachés (Django)
- CSRF actif
- Verrouillage après 5 échecs (15 min, configurable via `.env`)
- Flutter ne se connectera jamais directement à MySQL
