# Filtres BI — Kalunga

Les filtres sont des paramètres **GET** normalisés par `apps.bi.filters.parse_bi_filters` en `BiFilters`.

Ils ne s’appliquent que si le modèle / sélecteur le permet.

## Paramètres

| Paramètre GET | Alias | Champ `BiFilters` | Usage typique |
|---------------|-------|-------------------|---------------|
| `date_from` | `debut`, `from` | `date_from` | Début de période |
| `date_to` | `fin`, `to` | `date_to` | Fin de période |
| `level` | `level_id` | `level_id` | Niveau |
| `section` | `section_id` | `section_id` | Section |
| `option` | `option_id` | `option_id` | Option |
| `class_id` | `classe`, `school_class` | `class_id` | Classe |
| `gender` | `sexe` | `gender` | `M` / `F` / `O` |
| `fee_id` | `fee` | `fee_id` | Frais |
| `enrollment_status` | `status` | `enrollment_status` | Statut inscription |
| `enrollment_type` | `type` | `enrollment_type` | Type inscription |
| `payment_method` | `mode` | `payment_method` | Mode de paiement |
| `payment_status` | — | `payment_status` | Statut paiement |
| `attendance_status` | — | `attendance_status` | Statut présence |
| `severity` | `incident_severity` | `incident_severity` | Gravité incident |
| `incident_status` | — | `incident_status` | Statut incident |
| `category_id` | `category` | `category_id` | Catégorie discipline |
| `summons_status` | — | `summons_status` | Statut convocation |

Formats de date acceptés : `YYYY-MM-DD`, `DD/MM/YYYY`.

## UI

Barre commune : `templates/bi/partials/filters.html` (`data-bi-filters`).

- Soumission GET native (recharge KPI + graphiques + tableaux)
- Domaines : champs additionnels selon `bi_domain` (`enrollments`, `finance`, `attendance`, `discipline`)
- Réinitialisation via `data-bi-filter-reset` → URL de la page sans query

L’année scolaire principale reste celle du **contexte Secrétariat** (session), pas un simple champ de la barre BI.

## API

Les mêmes query params sont acceptés sur `/api/v1/bi/<domaine>/summary|trends|classes/`.

## Règle produit

Un changement de filtre doit faire évoluer **ensemble** les KPI, graphiques et tableaux du domaine (recalcul serveur).
