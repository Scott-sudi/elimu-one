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
| POST | `/api/v1/auth/logout/` | JWT | Déconnexion client |
| GET | `/api/v1/auth/me/` | JWT | Profil courant |
| POST | `/api/v1/auth/change-password/` | JWT | Changer le mot de passe |

Exemple token :

```json
POST /api/v1/auth/token/
{ "username": "admin.kalunga", "password": "********" }
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
