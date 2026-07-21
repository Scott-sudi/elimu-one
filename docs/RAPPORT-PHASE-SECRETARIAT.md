# Rapport final — Module Secrétariat Kalunga

Date : 21 juillet 2026  
Projet : `kalunga-school`  
Base MySQL : `kalunga_school`  
Phase : Secrétariat terminé — Comptabilité / Discipline / Flutter non démarrés

---

## 1. Résumé de l’architecture existante

- Stack : Python 3.13.12, Django 5.2.16, DRF, MySQL (Wamp), Templates + HTMX + Alpine + Vite
- Apps : `core`, `accounts`, `dashboard`, `audit`, `api`, `secretariat` (développé), stubs `finance` / `discipline`
- Auth : `accounts.User` + rôles système (`ADMINISTRATEUR`, `SECRETAIRE`, `COMPTABLE`, `DISCIPLINE`)
- Contrôle d’accès opérationnel : codes de rôle (`is_administrateur()`, `is_secretaire()`), mixins web et permissions DRF
- Shell UI actif : `layouts/app.html` + `components/navbar.html` (sidebar/topbar dormants)
- Design tokens : verts unis `#1f6f4a` / `#0d5a22`, fond cahier, faibles rayons

## 2. Applications Django touchées

| App | Nature |
|-----|--------|
| `apps.secretariat` | Nouveau domaine complet |
| `apps.accounts` | Helpers rôle + profil staff |
| `apps.core` | Mixins `RoleRequired` / `SecretaryRequired` |
| `apps.api` | `IsSecretary`, montage routes secretariat + card resolve |
| `apps.audit` | Nouvelles actions d’audit |
| `apps.dashboard` | Redirection secrétaire → `/secretariat/` |
| `config` | Include URLs web secrétariat |

## 3. Nouveaux modèles (principaux)

- `AcademicYear`, `SchoolLevel`, `Section`, `Option`, `SchoolClass`
- `Student`, `Guardian`, `StudentGuardian`
- `Enrollment`, `ClassTransfer`
- `DocumentType`, `StudentDocument`
- `StudentCard`
- `Communication`, `CommunicationTarget`, `CommunicationReceipt`
- `SecretariatSetting`

Champs communs : `public_id` (UUID), timestamps, flags actif/archivé selon entité.  
Relations : PROTECT sur données historiques ; inscription = source de vérité de la classe courante.

## 4. Contraintes / index

- Unicité : matricule, numéro d’inscription, QR, code classe/année, codes niveaux/sections/options
- Check : dates année (`start < end`), capacité classe > 0
- Unicité inscription validée par année : **service** (MySQL ne gère pas correctement les UniqueConstraint conditionnelles)
- Index recherche : noms, statuts, année, classe

## 5. Migrations

| Migration | État |
|-----------|------|
| `secretariat.0001_initial_secretariat` | créée et appliquée (tables présentes) |
| `audit.0002_secretariat_audit_actions` | créée et appliquée |
| `accounts.0003_user_profile_photo` | déjà dans le baseline Admin |

Aucune migration Admin détruite. Pas de flush / reset.

## 6. Services créés

`matricule_service`, `enrollment_number_service`, `academic_service`, `student_service`, `guardian_service`, `enrollment_service`, `reenrollment_service`, `transfer_service`, `document_service`, `card_service` (QR + PDF reportlab), `communication_service`, `dashboard_service`

## 7. Formulaires / vues / routes web

Formulaires : academic, class, student, guardian, enrollment, communication, document.  
Vues : dashboard, années, organisation, classes, élèves, responsables, inscriptions/réinscriptions/transferts, cartes, communications, documents, exports, téléchargement protégé.  

Préfixe : `/secretariat/` (namespace `secretariat:`)

## 8. Routes API

- `/api/v1/secretariat/academic-years|levels|sections|options|classes|students|guardians|enrollments|student-cards|communications/`
- `/api/v1/cards/resolve/<qr_identifier>/` (authentifié, payload minimal)

Permissions : `IsSecretary` pour le module ; resolve carte = `IsAuthenticated`.

## 9. Templates / HTMX / JS

- 39 templates sous `templates/secretariat/`
- Partials `_table.html` + HTMX filtres/pagination
- JS pages : `static/src/js/pages/secretariat/*.js`
- Composants : `image-preview.js`, `enrollment-wizard.js`
- CSS : `pages/secretariat.css` (sans nouvelle palette)

## 10. Composants réutilisés

Navbar, layout app, boutons, inputs, tables, badges, empty states, pagination, modales, toasts (`Kalunga.toast`), confirmations, Lucide.

## 11. Composants partagés modifiés (non destructifs)

- `navbar.html` : branche SECRETAIRE
- `mixins.py` / `permissions.py` : généralisation rôle
- Profil / MDP : `StaffActiveRequiredMixin`
- `dashboard/views.py` : redirect secrétaire
- `app.js` / `main.css` : boot secrétariat
- Règles Cursor mises à jour

## 12. Mécanismes clés

- **Matricule** : `KAL-YYYY-#####` via `SecretariatSetting`, généré serveur, stable
- **N° inscription** : `INS-YYYY-#####` par année
- **QR** : opaque `KAL-CARD-{hex}` — aucune PII
- **PDF carte** : reportlab, couleurs institutionnelles vertes, logo/slogan depuis settings

## 13. Tests

- Admin : 16 tests (incl. redirect secrétaire + profil)
- Secrétariat : 10 tests (matricule, années, capacité, transfert, carte/QR, permissions, API)
- **Résultat : 26 passed** (`pytest backend/tests -c backend/pytest.ini`)

## 14. Dépendances ajoutées

Python : `qrcode[pil]`, `reportlab`, `openpyxl`  
JavaScript : aucune nouvelle dépendance npm

## 15. Commandes utiles

```powershell
cd C:\Users\Elisée\Desktop\IK\kalunga-school
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "$PWD\backend"
python backend\manage.py migrate
python backend\manage.py initialize_secretariat
npm run build
python backend\manage.py runserver
pytest backend\tests -c backend\pytest.ini
```

Compte secrétaire : à créer via l’Administrateur (rôle SECRETAIRE), puis connexion → redirection `/secretariat/`.

## 16. Vérification Secrétariat (checklist)

1. Connexion secrétaire OK ; comptable/discipline refusés (403)
2. Créer / activer / clôturer année scolaire
3. Niveaux, sections, options, classes
4. Élève + matricule auto + photo
5. Responsable + association principale
6. Inscription / refus doublon / capacité
7. Réinscription / transfert
8. Documents + complétude
9. Génération carte + QR + PDF
10. Communication + ciblage
11. Export CSV/XLSX
12. API `/api/v1/secretariat/...` + resolve QR
13. Admin inchangé (users, rôles, audit, dashboard)

## 17. Limites actuelles

- Unicité inscription active par année : service (pas contrainte partielle MySQL)
- Media encore servi publiquement en DEBUG (téléchargement documents a une vue protégée dédiée)
- Endpoint resolve QR ouvert à tout utilisateur authentifié (prévu pour Discipline plus tard)
- Pas de fausse population d’élèves en base réelle
- Logo/coordonnées inventées évitées ; PDF utilise `SCHOOL_NAME` / `SCHOOL_SLOGAN`

## 18. État Git final

Branche `master`, commits :

1. `chore(admin): baseline validated administrator module`
2. `feat(secretariat): add secretary access foundations`
3. `feat(secretariat): add school structure and student domain models`
4. `feat(secretariat): implement business services and selectors`
5. `feat(secretariat): add web UI workflows with HTMX templates`
6. `feat(secretariat): expose REST API and secure card resolve`
7. `test(secretariat): add module coverage and admin non-regression`

## 19. Arrêt de phase

Module Secrétariat livré.  
**Comptabilité, Discipline et Flutter non démarrés.**
