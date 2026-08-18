# API REST v1 — Kalunga

Base : `/api/v1/`

Format de réponse :

```json
{
  "success": true,
  "message": "Opération effectuée avec succès.",
  "data": {},
  "errors": {}
}
```

## Santé et installation

| Méthode | Route | Auth | Description |
|---------|-------|------|-------------|
| GET | `/api/v1/health/` | Public | Santé du service |
| GET | `/api/v1/setup/status/` | Public | Installation initialisée ? |
| POST | `/api/v1/setup/initialize/` | Public | Créer le premier admin (une seule fois) |

## Authentification JWT (Flutter)

| Méthode | Route | Auth | Description |
|---------|-------|------|-------------|
| POST | `/api/v1/auth/token/` | Public | Obtenir access + refresh |
| POST | `/api/v1/auth/token/refresh/` | Public | Rafraîchir le jeton |
| POST | `/api/v1/auth/logout/` | JWT | Revoque le refresh token |
| GET | `/api/v1/auth/me/` | JWT | Profil courant |
| POST | `/api/v1/auth/change-password/` | JWT | Changer le mot de passe |

Exemple token :

```json
POST /api/v1/auth/token/
{ "username": "admin.kalunga", "password": "********" }
```

La deconnexion exige le token d'acces dans `Authorization: Bearer <access>` et le
refresh token dans le corps de la requete :

```json
{ "refresh": "<refresh-token>" }
```

## Authentification parents (Flutter — téléphone + n° d'identification)

| Méthode | Route | Auth | Description |
|---------|-------|------|-------------|
| POST | `/api/v1/parents/auth/verify-phone/` | Public | Vérifie téléphone + numéro d'identification d'un responsable actif |
| GET | `/api/v1/parents/children/` | Public* | Liste des élèves liés au responsable |
| GET | `/api/v1/parents/home/overview/` | Public* | Accueil : nom, stats, activités (finance + secrétariat + discipline) |
| GET | `/api/v1/parents/notifications/` | Public* | Inbox notifications (paiements, messages secrétariat, convocations, incidents) |
| GET | `/api/v1/parents/children/{id}/attendance/?kind=present\|absent` | Public* | Dates de présence ou d'absence |
| GET | `/api/v1/parents/children/{id}/discipline/` | Public* | Dossier disciplinaire (même builder que le web : identité, stats, incidents, mesures, convocations) |
| GET | `/api/v1/parents/children/{id}/finance/` | Public* | Situation financière (frais / paiements) |

\* Auth provisoire : query `guardian_public_id` ou header `X-Guardian-Public-Id`
(remplacé plus tard par JWT parents).

```json
POST /api/v1/parents/auth/verify-phone/
{
  "telephone": "0991112233",
  "numero_identification": "CD12345678"
}
```

En secours (si Tiger Protect bloque les POST hors navigateur) :

```http
GET /api/v1/parents/auth/verify-phone/?telephone=0991112233&numero_identification=CD12345678
```

Formats téléphone acceptés : `0…` (local RDC) ou `+243…`.
Le numéro d'identification est comparé **à la valeur en base** (`Guardian.numero_identification`), sans espaces et sans distinction de casse.
S'il est vide en base ERP, la connexion est refusée.

Réponse reconnue :

```json
{
  "success": true,
  "message": "Connexion autorisée.",
  "data": {
    "recognized": true,
    "guardian_public_id": "…",
    "display_name": "Jean Kabasele",
    "next_auth_step": "password",
    "available_auth_methods": ["password", "pin", "otp", "biometric"]
  }
}
```

Réponse non reconnue (`recognized: false`, HTTP 200) — message unique :
« Identifiants incorrects. Vérifiez le téléphone et le numéro d'identification, puis réessayez. »
(téléphone inconnu, ID faux, compte inactif, ou ID manquant en base).

Les étapes mot de passe / PIN / OTP / biométrie seront ajoutées ensuite.
Les routes de notifications mobiles restent reservees sous `/api/v1/notifications/`.
Aucun client mobile ne doit acceder directement a MySQL.

```json
GET /api/v1/parents/home/overview/?guardian_public_id=<uuid>
```

Réponse (extrait) :

```json
{
  "success": true,
  "data": {
    "display_name": "Paul Mwamba",
    "school_year_label": "Année scolaire 2025-2026",
    "children_count": 1,
    "notifications_count": 0,
    "general_average_percent": null,
    "unpaid_balance_label": "Aucun",
    "activities": []
  }
}
```

## Administration

| Méthode | Route | Auth | Description |
|---------|-------|------|-------------|
| GET | `/api/v1/admin/dashboard/` | Admin | Statistiques comptes |
| GET/POST | `/api/v1/users/` | Admin | Liste / création |
| GET/PUT | `/api/v1/users/{public_id}/` | Admin | Détail / mise à jour |
| PATCH | `/api/v1/users/{public_id}/status/` | Admin | activate / deactivate / archive |
| POST | `/api/v1/users/{public_id}/reset-password/` | Admin | Mot de passe temporaire |
| DELETE | `/api/v1/users/{public_id}/` | Admin | Archive logique |
| GET | `/api/v1/roles/` | Admin | Rôles système |
| GET | `/api/v1/audit/logins/` | Admin | Tentatives de connexion |
| GET | `/api/v1/audit/actions/` | Admin | Journal d’activités |

L’identifiant public exposé est `public_id` (UUID), pas l’ID numérique interne.

## CORS

Configurer `CORS_ALLOWED_ORIGINS` dans `.env` pour ajouter plus tard l’origine Flutter / portail web.
Ne pas activer `CORS_ALLOW_ALL_ORIGINS` en production.
