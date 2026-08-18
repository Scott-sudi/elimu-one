# Rapport final — Phase Administrateur

## Versions

- **Python** : 3.13.12
- **Django** : 5.2.16 (LTS, compatible Python 3.13)
- **MySQL** : 8.4.7 (WampServer)
- **Node.js** : 24.14.1 / **npm** : 11.11.0
- **Vite** : 6.4.3
- **PyMySQL** : connecteur MySQL Python compatible avec les environnements mutualisés

## Dépendances Python principales

Django, djangorestframework, djangorestframework-simplejwt, django-environ, django-cors-headers, django-filter, PyMySQL, Pillow, whitenoise, python-dateutil, pytest, pytest-django, factory-boy, coverage, ruff, black.

Voir `backend/requirements/` et `backend/requirements/freeze.txt`.

## Dépendances npm

vite, htmx.org, alpinejs, lucide, chart.js

## Applications Django

| App | Rôle phase 1 |
|-----|----------------|
| core | Utilitaires, mixins, contexte, erreurs, Vite |
| accounts | User, Role, auth, setup, profil |
| dashboard | Tableau de bord admin |
| audit | LoginAttempt, AuditLog |
| api | REST v1 + JWT |
| secretariat | Structure vide |
| finance | Structure vide |
| discipline | Structure vide |

## Modèles

- `accounts.Role`, `accounts.User`, `accounts.SystemConfiguration`
- `audit.LoginAttempt`, `audit.AuditLog`

## Migrations

- `accounts.0001_initial`, `accounts.0002_seed_roles`
- `audit.0001_initial`
- + migrations Django contrib (auth, sessions, admin, contenttypes)

## Rôles système

ADMINISTRATEUR, SECRETAIRE, COMPTABLE, DISCIPLINE

## Permissions User (custom)

view_admin_dashboard, manage_users, view_login_history, view_audit_log, manage_own_profile

## Routes web principales

- `/setup/`
- `/connexion/`, `/deconnexion/`
- `/tableau-de-bord/`
- `/utilisateurs/` (+ CRUD HTMX)
- `/roles/`
- `/connexions/`
- `/journal/`
- `/profil/`, `/profil/mot-de-passe/`

## Routes API

Voir `docs/API.md`.

## Templates / JS / CSS

- Templates : `backend/templates/` (layouts, components, accounts, dashboard, audit, errors, setup)
- JS ES6 : `backend/static/src/js/` (app, core, components, pages)
- CSS design system : `backend/static/src/css/` (tokens, base, layouts, components, pages)
- Build : `backend/static/dist/`

## Tests exécutés

```
pytest backend/tests/test_admin_module.py
```

**Résultat** : 14 tests OK (exit code 0)

Couverture fonctionnelle : setup, rôles, hash MDP, login/échec, lockout, cycle de vie utilisateurs, recherche/filtres/pagination, dashboard, API/JWT, CSRF, 404.

## Procédure premier administrateur

1. Base vide → ouvrir http://127.0.0.1:8000 → redirection `/setup/`
2. Saisir identité + username + mot de passe
3. Redirection vers `/connexion/`
4. Se connecter

Alternative CLI (sans mot de passe en dur) :

```powershell
python manage.py create_initial_admin --nom "..." --prenom "..." --username "..."
```

## Procédure WampServer

1. Lancer WampServer
2. Vérifier icône verte
3. MySQL actif sur `127.0.0.1:3306`
4. Base `kalunga_school` existante (utf8mb4)
5. `python manage.py check_database`

## Compilation Vite

```powershell
npm install
npm run build
```

## Erreurs / limites restantes

- Blacklist JWT côté serveur non activée (index MySQL MyISAM historique sur WAMP) : déconnexion API = discard client. Rotation des refresh tokens active.
- Tests automatisés sur SQLite ; MySQL validé manuellement via migrate + check_database.
- Chart.js installé mais non utilisé (pas de graphiques nécessaires sur le dashboard comptes).
- Logo officiel absent : fallback Lucide + texte Kalunga.
- Modules secrétariat / finance / discipline / Flutter : volontairement absents.

## Fonctionnalités non terminées (hors périmètre)

Tout le reste du système scolaire (élèves, parents, paiements, présences, discipline métier, Flutter, BI).

## Arrêt

Phase Administrateur validée. **Aucun autre acteur n’est commencé.**
