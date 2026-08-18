# ELIMU One / ELIMU Go — Document de passation pour agent IA

**Version :** 18 août 2026  
**Destinataire :** agent IA qui reprend le projet  
**Demandeur :** Elisée (non-programmeur — agir de manière autonome)  
**Dépôt local :** `C:\Users\Elisée\Desktop\Mes_Projet_finis\CS-Elimu\kalunga-school`

---

## 1. Mission de l'agent suivant

Tu reprends un **ERP scolaire Django + Flutter** déjà fonctionnel en local. Le propriétaire du projet **n'est pas développeur** : tu dois **analyser, décider et exécuter** sans lui demander de détails techniques sauf pour les secrets (mots de passe MySQL, accès cPanel, nom de domaine final, compte GitHub).

### Objectifs prioritaires (dans cet ordre)

1. **Héberger ELIMU One** sur le compte **o2switch** du client (nouveau déploiement propre — voir section 6).
2. **Configurer MySQL, SSL, DNS**, créer une **nouvelle base** et un **nouvel utilisateur MySQL** dédiés à ELIMU (ne pas réutiliser l'ancienne base « Kalunga » sans validation explicite).
3. **Brancher ELIMU Go** (Flutter) sur l'API hébergée — sans changer la logique métier, seulement thème / branding / URL API.
4. **Générer l'APK** Android signé et le **publier sur le GitHub** du client.
5. **Documenter** ce que tu as fait (URL finale, identifiants admin créés, commandes exécutées).

### Ce que tu ne dois PAS faire sans accord explicite

- Déployer par-dessus l'ancien site **institut-kalunga.net** en supposant que c'est le bon domaine ELIMU.
- Commiter le fichier `.env` ou des mots de passe dans Git.
- Pousser des données de démo (`seed_platform_demo`) en production réelle sans `purge_for_production` avant.
- Modifier la logique métier (secrétariat, finance, discipline) sauf bug avéré.

---

## 2. Contexte : d'où vient le projet

### Origine

- Codebase héritée d'un projet **« Kalunga School » / « Institut Kalunga »** (Likasi, RDC) : ERP complet secrétariat, finance, discipline, BI, API parents Flutter.
- Dossier applicatif : **`kalunga-school/`** (nom interne conservé — ne pas confondre avec la marque produit).
- Racine workspace : **`CS-Elimu/`** contient les assets marque **`ELIMU/`** (logo, favicons).

### Pivot effectué (session IA août 2026)

Le client a demandé de **transformer l'application école unique** en **plateforme de gestion scolaire** white-label :

| Avant | Après |
|-------|-------|
| Marque « CS Elimu » / « Complexe Scolaire » | **ELIMU One** (web) |
| App parents « CS Elimu » | **ELIMU Go** (mobile) |
| Identité = une école fixe | Identité établissement via `SCHOOL_*` (vide par défaut) |
| MySQL local (Wamp) | **SQLite** en dev, **MySQL** en prod |
| Logo / couleurs Kalunga | Logo et palette **ELIMU** (marine `#002858`, vert `#40a040`) |

---

## 3. Identité produit (état actuel)

### Web — ELIMU One

- `PLATFORM_NAME=ELIMU One`
- `PLATFORM_TAGLINE=Système de gestion scolaire`
- Navbar, login, titres → nom plateforme
- Cartes élèves, reçus → `SCHOOL_NAME` ou « Établissement scolaire » si non configuré

**Fichiers clés :**

- `backend/apps/core/branding.py` — helpers affichage
- `backend/apps/core/context_processors.py` — variables template
- `backend/config/settings/base.py` — `PLATFORM_*`, `SCHOOL_*`
- `backend/templates/components/brand.html`
- `backend/static/src/css/tokens/colors.css`
- `backend/static/src/images/branding/` — logo, favicons, manifest PWA

### Mobile — ELIMU Go

- `mobile/kalunga_parents/lib/constants/app_constants.dart` — `appName = 'ELIMU Go'`
- `AndroidManifest.xml`, `Info.plist`, `web/manifest.json` — libellés ELIMU Go
- **Encore à faire :** renommer package Android `net.institutkalunga.parents` (optionnel mais recommandé), Firebase/FCM si nouveau projet Google, icônes launcher régénérées

### Assets source

- Dossier : `CS-Elimu/ELIMU/` (logo PNG, favicons, site.webmanifest)
- Copiés vers : `backend/static/src/images/branding/` et `mobile/kalunga_parents/assets/branding/`

---

## 4. Architecture technique

```
CS-Elimu/
├── ELIMU/                    # Assets marque (source)
└── kalunga-school/
    ├── backend/              # Django 5.2 — ELIMU One
    │   ├── apps/
    │   │   ├── accounts/     # Auth, rôles, setup
    │   │   ├── secretariat/  # Années, classes, élèves, cartes
    │   │   ├── finance/      # Minerval, paiements, reçus
    │   │   ├── discipline/   # Présences QR, incidents
    │   │   ├── bi/           # Business intelligence préfet
    │   │   └── api/          # REST + JWT + API parents mobile
    │   ├── config/settings/
    │   │   ├── development.py  # SQLite
    │   │   ├── production.py   # MySQL o2switch
    │   │   └── test.py
    │   ├── passenger_wsgi.py   # Entrée o2switch / Passenger
    │   ├── db.sqlite3          # Base locale (NE PAS envoyer en prod)
    │   └── scripts/
    │       ├── deploy.sh
    │       └── smoke_routes.py
    ├── mobile/kalunga_parents/ # Flutter — ELIMU Go
    ├── docs/                   # DEPLOYMENT.md, ENVIRONMENT.md, ce fichier
    ├── .env                    # Local (gitignored)
    └── package.json            # Vite 6 — assets frontend
```

### Stack

| Composant | Version / note |
|-----------|----------------|
| Python | 3.13.x |
| Django | 5.2 LTS |
| MySQL | 8.x (o2switch prod) |
| SQLite | dev local |
| Node / Vite | build CSS/JS → `backend/static/dist/` |
| Flutter | app parents dans `mobile/kalunga_parents/` |

---

## 5. Modifications déjà apportées (inventaire session IA)

### 5.1 Rebrand & configuration

- [x] Palette CSS navy/vert ELIMU
- [x] Logo / favicons / PWA manifest « ELIMU One »
- [x] Suppression références UI « CS Elimu », « Complexe Scolaire », « campus scolaire »
- [x] `SCHOOL_NAME` / `SCHOOL_SLOGAN` vides par défaut (plateforme générique)
- [x] SQLite local via `build_databases()` dans `settings/base.py`
- [x] MySQL forcé en `settings/production.py`

### 5.2 Corrections bugs

- [x] Formulaire création utilisateur `/utilisateurs/nouveau/` — `VariableDoesNotExist` sur `sexe` (template + `user_obj`)
- [x] Sélecteur année scolaire — `has_session_year()` pour ne pas auto-rediriger sans choix utilisateur
- [x] Finance — onglets `?tableau=minerval` / `?tableau=etat` restaurés
- [x] `year_context.py` — restauration `get_selected_year_id()`
- [x] Horaires pointage QR — commande `ensure_attendance_schedules` + seed auto

### 5.3 Données de démonstration (local SQLite)

Commande exécutée : `python manage.py seed_platform_demo`

Contenu approximatif :

- Années 2024-2025 → **2026-2027 active**
- ~248 élèves, 138 classes, cartes, présences, finance
- 10 profils anglophones (Smith, Johnson, etc.)
- Horaires AM/PM avec fin 23:59 (mode démo pour tests soir)

**Avant production réelle :** `python manage.py purge_for_production` puis configuration école via `.env` et `/setup/` ou admin.

### 5.4 Tests automatisés

- **pytest :** 83 tests OK (`backend/tests/`)
- **smoke_routes.py :** 585 routes GET × 5 rôles sans erreur 500

### 5.5 Fichiers / docs créés ou mis à jour

- `backend/apps/core/branding.py`
- `backend/apps/secretariat/management/commands/seed_platform_demo.py`
- `backend/apps/discipline/management/commands/ensure_attendance_schedules.py`
- `backend/scripts/smoke_routes.py`
- `docs/ENVIRONMENT.md`, `README.md` (partiellement à jour)

---

## 6. Hébergement o2switch — instructions pour l'agent

### ⚠️ Important : nouveau déploiement

L'ancien projet tournait sur **institut-kalunga.net** (compte cPanel type `susc3383`).  
**ELIMU One est un nouveau produit** : tu dois :

1. Choisir avec le client un **domaine ou sous-domaine** (ex. `elimu.one`, `app.elimu.cd`, ou sous-domaine o2switch `*.odns.fr`).
2. Créer une **nouvelle base MySQL** (ex. `cpuser_elimu`) et un **nouvel utilisateur MySQL** avec mot de passe fort.
3. Cloner / déployer le code dans un dossier dédié (ex. `~/elimu-school/` ou réutiliser `~/kalunga-school/` après backup).
4. **Ne pas** pointer la prod ELIMU vers l'ancienne base `susc3383_kalunga` sans migration planifiée.

### Guide existant

Lire et adapter : **`docs/DEPLOYMENT.md`** et **`docs/ENVIRONMENT.md`**.

### Checklist déploiement autonome

#### A. cPanel — MySQL

1. MySQL Databases → créer base `elimu` (nom complet préfixé cpanel).
2. Créer utilisateur + mot de passe → ALL PRIVILEGES sur la base.
3. Noter : `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` (souvent `localhost`).

#### B. cPanel — Python App (Passenger)

1. Setup Python App → Python 3.10+.
2. Application root : `…/kalunga-school/backend` (ou nouveau chemin).
3. Startup file : `passenger_wsgi.py`.
4. Domaine : celui choisi par le client.

#### C. Fichier `.env` production (racine dépôt, à côté de `backend/`)

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=<générer une clé longue unique>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<domaine>,<www>,<url-temporaire.odns.fr>
CSRF_TRUSTED_ORIGINS=https://<domaine>,https://www.<domaine>,https://<odns.fr>

DB_ENGINE=django.db.backends.mysql
DB_NAME=<cpuser_elimu>
DB_USER=<cpuser_elimu_user>
DB_PASSWORD=<secret>
DB_HOST=localhost
DB_PORT=3306

PLATFORM_NAME=ELIMU One
PLATFORM_TAGLINE=Système de gestion scolaire
SCHOOL_NAME=
SCHOOL_SLOGAN=

STATIC_ROOT=/home/<CPANELUSER>/<projet>/backend/staticfiles
MEDIA_ROOT=/home/<CPANELUSER>/<projet>/backend/media
DJANGO_LOG_DIR=/home/<CPANELUSER>/<projet>/backend/logs

CORS_ALLOWED_ORIGINS=https://<domaine>
DJANGO_SECURE_SSL_REDIRECT=True
```

#### D. Commandes sur le serveur (venv activé)

```bash
cd ~/kalunga-school/backend
pip install -r requirements.txt
cd .. && npm ci && npm run build   # ou uploader backend/static/dist/ si npm indispo
cd backend
python manage.py migrate --noinput
python manage.py initialize_roles
python manage.py initialize_secretariat
python manage.py collectstatic --noinput
python manage.py check --deploy
python manage.py ensure_open_academic_year
python manage.py ensure_attendance_schedules --strict-hours
touch tmp/restart.txt
```

#### E. SSL & DNS

1. cPanel → Zone Editor : enregistrements A/CNAME vers IP o2switch.
2. SSL/TLS Status → Run AutoSSL.
3. Vérifier `https://<domaine>/api/v1/health/` puis `/setup/` ou `/connexion/`.

#### F. Médias

```bash
ln -s ~/kalunga-school/backend/media ~/public_html/media
```

(Si refusé par o2switch → ticket support comme indiqué dans DEPLOYMENT.md.)

#### G. Premier admin

- Si base vierge : **`https://<domaine>/setup/`** une seule fois.
- Ne pas réutiliser les comptes de démo locaux.

---

## 7. Mobile ELIMU Go — branchement API

### Fichier central

`mobile/kalunga_parents/lib/config/api_config.dart`

```dart
static const ApiEnvironment environment = ApiEnvironment.production;
static const String productionHost = 'https://<DOMAINE-ELIMU-ONE>';
```

### Travail restant (branding + build, pas de logique métier)

1. Mettre à jour `productionHost` avec l'URL HTTPS finale.
2. Vérifier thème : `lib/core/theme/app_colors.dart` (déjà `#002858` / `#40a040`).
3. Régénérer icônes launcher : `mobile/kalunga_parents/tool/generate_app_icons.py` (source `ELIMU/elimu_logo.png`).
4. Tester login téléphone parent sur API prod (`/api/v1/parents/...`).
5. **Tiger Protect o2switch** : certains POST API peuvent être bloqués hors navigateur — voir `parents_auth.py`, `PUSH_SETUP.md`, scripts `cpanel_paste_*` si présents.
6. Build APK :

```bash
cd mobile/kalunga_parents
flutter pub get
flutter build apk --release
```

APK : `build/app/outputs/flutter-apk/app-release.apk`

### Firebase / notifications push

- Ancien projet FCM : `institut-kalunga` — **à migrer** vers un projet Firebase ELIMU si push requis en prod.
- Voir `mobile/kalunga_parents/PUSH_SETUP.md` et variable `FCM_PROJECT_ID` dans settings.

---

## 8. GitHub — dépôt et livraison APK

État git (août 2026) : dépôt dans `kalunga-school/`, branche `master`, **nombreux fichiers modifiés/non commités**, pas de remote vérifié à la racine CS-Elimu.

### Actions pour l'agent

1. Demander au client l'URL du repo GitHub (ou en créer un **privé** ELIMU-One).
2. `.gitignore` doit exclure : `.env`, `db.sqlite3`, `media/`, `staticfiles/`, `node_modules/`, `.venv/`, `tools/flutter/`.
3. Commit message clair : rebrand ELIMU + fixes + docs handoff.
4. Pousser le code ; attacher l'APK en **Release GitHub** ou dans `mobile/kalunga_parents/build/` (ne pas versionner l'APK binaire dans git — utiliser Releases).

---

## 9. Base de données — situation

| Environnement | Moteur | Fichier / serveur |
|---------------|--------|-------------------|
| Dev local | SQLite | `backend/db.sqlite3` (~2 Mo, contient démo) |
| Tests pytest | SQLite | base éphémère |
| Prod o2switch | MySQL 8 | **à créer** — base dédiée ELIMU |

### Commandes données

| Commande | Usage |
|----------|-------|
| `seed_platform_demo` | Démo complète (local) |
| `purge_for_production` | Vider données métier avant vraie prod |
| `ensure_open_academic_year` | Créer année ouverte si absente |
| `ensure_attendance_schedules` | Horaires QR ( `--strict-hours` en prod ) |

---

## 10. Références « Kalunga » encore présentes (dette technique)

Le code interne conserve des noms hérités — **ne pas confondre avec la marque** :

- Dossier `kalunga-school/`, package Flutter `kalunga_parents`
- Préfixe matricule / QR `KAL-CARD-`, `MATRICULE_PREFIX=KAL`
- CSS classes `kalunga-id-card__*`
- `institut-kalunga.net` dans `api_config.dart`, `DEPLOYMENT.md`, `production.py` defaults
- Android `net.institutkalunga.parents`

L'agent peut **nettoyer progressivement** les defaults hardcodés vers des variables d'environnement une fois le domaine ELIMU fixé.

---

## 11. Points d'attention connus

1. **Vite build OOM** sur machine client Windows — build sur serveur o2switch ou CI ; fallback dev sert `static/src/` si pas de manifest.
2. **Année scolaire en session** obligatoire pour secrétariat/finance/discipline — choisir 2026-2027 après login.
3. **Pointage QR** nécessite horaires configurés ; après 18h refusé si `--strict-hours`.
4. **README.md** section « Non développé » est **obsolète** — tous les modules existent.
5. **`tools/flutter/`** dans workspace = SDK vendored — ignorer, ne pas committer.

---

## 12. Validation post-déploiement (checklist agent)

- [ ] HTTPS actif, pas d'erreur 400 DisallowedHost
- [ ] `/setup/` ou login admin OK
- [ ] Sélection année scolaire OK
- [ ] Upload photo élève + génération carte
- [ ] Pointage QR test (horaires configurés)
- [ ] API health `/api/v1/health/`
- [ ] Login parent Flutter sur URL prod
- [ ] APK installé sur téléphone test
- [ ] Release GitHub publiée avec notes

---

## 13. Contacts & secrets (à remplir par le client)

| Élément | Valeur |
|---------|--------|
| Compte o2switch / cPanel | _à compléter_ |
| Préfixe cPanel (ex. susc3383) | _à compléter_ |
| Domaine ELIMU visé | _à compléter_ |
| GitHub repo URL | _à compléter_ |
| Compte admin prod créé | _à compléter après setup_ |

---

## 14. Message direct à l'agent IA

Tu as **toute la autonomie** pour :

- Lire le code, exécuter les commandes, te connecter au serveur via les accès fournis par le client.
- Corriger les docs obsolètes (institut-kalunga → domaine ELIMU).
- Finaliser le thème mobile et produire l'APK.
- Déployer sur o2switch avec **nouvelle base MySQL**, SSL et DNS.

Tu **t'arrêtes et tu demandes** uniquement pour :

- Choix du nom de domaine définitif.
- Identifiants cPanel / MySQL / GitHub.
- Validation de supprimer l'ancien site Kalunga.

**Le travail de la session précédente s'arrête ici.** La suite = hébergement + mobile + GitHub + APK.

---

*Document généré pour passation agent IA — projet ELIMU One / ELIMU Go.*
