# Architecture BI — Kalunga (Préfet)

Vue d’ensemble du module décisionnel intégré à Django.

## Sources de données

| Domaine | App source | Entités lues |
|---------|------------|--------------|
| Effectifs | `apps.secretariat` | `Enrollment`, `Student`, `SchoolClass`, `AcademicYear` |
| Finances | `apps.finance` | `StudentFeeObligation`, `Payment` |
| Assiduité | `apps.discipline` | `DailyAttendance` |
| Discipline | `apps.discipline` | `DisciplinaryIncident`, `DisciplinaryMeasure`, `ParentSummons` |

Aucune table métier BI en doublon : les sélecteurs interrogent les modèles opérationnels.

## Couches

```
Templates bi/*  →  views (BiPageView)  →  services  →  selectors  →  modèles
                         ↕
                  API /api/v1/bi/* (IsPrefet)
                         ↕
            JS Plotly (bi-app.js + chart-manager)
```

- **Selectors** : querysets filtrés (`apps/bi/selectors/`)
- **Services** : KPI, payloads `charts` / `tables`, alertes (`apps/bi/services/`)
- **Filters** : `BiFilters` + `parse_bi_filters` (`apps/bi/filters.py`)
- **Views web** : `PrefetRequiredMixin` + année sélectionnée (`apps/bi/views/`)
- **API** : synthèse / tendances / classes par domaine (`apps/bi/api/`)

## Frontend

| Fichier | Rôle |
|---------|------|
| `static/src/js/pages/bi/bi-app.js` | Boot via `data-page` |
| `static/src/js/components/bi/plotly-config.js` | Config + palette Kalunga |
| `static/src/js/components/bi/chart-manager.js` | `newPlot` / `react`, empty state, resize |
| `static/src/js/pages/bi/bi-charts.js` | Lecture `json_script#bi-charts-data` |
| `static/src/js/pages/bi/bi-filters.js` | Barre GET `data-bi-filters` |
| `static/src/js/pages/bi/bi-api.js` | Fetch AbortController vers `/api/v1/bi/` |
| `static/src/css/pages/bi.css` | Agrégat des styles BI |

Payloads graphiques : `{ labels: [], series: [{ name, data }] }` sérialisés via `{{ charts\|json_script:"bi-charts-data" }}`.

## Plotly

- Package npm : `plotly.js-dist-min`
- Config partagée : `responsive`, `displaylogo: false`, mode bar allégée
- Couleurs : verts / bleu info / warning / danger / neutres (tokens)

## Filtres

GET sur les pages domaine ; mêmes paramètres sur l’API. Voir `docs/BI_FILTERS.md`.

## Cache

Pas de cache décisionnel dédié pour l’instant : calculs à la requête sur la base courante. Un bouton « Actualiser » recharge la page.

## Exports

`export_service` : CSV / XLSX (openpyxl), domaines `enrollments`, `financial`, `attendance`, `discipline`, `classes`, `comparisons`.

## Sécurité

- Rôle `PREFET` + permissions BI (`apps/bi/permissions.py`)
- Lecture seule côté module BI
- CSRF + session Django ; API `IsAuthenticated` + `IsPrefet`
- Voir `docs/BI_PERMISSIONS.md`
