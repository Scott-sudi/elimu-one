# Référence visuelle BI — Kalunga

Informations alignées sur le code actuel (pas un second design system).

## Layout

- Shell : `layouts/app.html` (navbar + sidebar + content)
- Pages : `backend/templates/bi/**/index.html`
- Conteneur page : `.bi-page` + `data-page="bi-*"`
- Cartes : composant `.card` existant
- KPI : `.dashboard__stats` + `.stat-card` (dashboard.css), affinés par `pages/bi/kpis.css`

## Fichiers CSS

| Fichier | Rôle |
|---------|------|
| `static/src/css/pages/bi.css` | Agrégat `@import` |
| `pages/bi/layout.css` | Structure page, alertes |
| `pages/bi/filters.css` | Barre `data-bi-filters` |
| `pages/bi/charts.css` | Conteneurs Plotly, empty state |
| `pages/bi/kpis.css` | Ajustements stat-cards BI |
| `pages/bi/drillthrough.css` | Tables sous graphiques |
| `pages/bi/print.css` | Impression |

Importés depuis `main.css` via `@import url("./pages/bi.css")`.

## Couleurs

Source : `tokens/colors.css`

- Vert primaire `#0d5a22` / succès `#167033`
- Info `#3f76b5`
- Warning `#c4922e`
- Danger `#c0392b`
- Neutres texte / grille / bordures

Palette Plotly : `plotly-config.js` (`BI_PALETTE`, `BI_COLORS`).

## Interdictions

- Pas de dégradés décoratifs
- Pas de boutons pilule (`border-radius` ≈ 4px)
- Pas de glassmorphism / néon / ombres lourdes
- Pas de thème type Power BI / dépendance Microsoft

## Filtres

- `.bi-filters` + `form-input form-input--sm` + `btn btn--secondary btn--sm`
- Partial : `templates/bi/partials/filters.html`

## Graphiques

- Conteneur : `[data-bi-chart]` + `.bi-chart` (min-height 280px)
- Type : `data-bi-chart-type` (`bar` | `line` | `donut` | `hbar` | `pie`)
- Empty : `.bi-chart__empty` injecté / géré par `chart-manager.js`

## Tooltips

Style Plotly `hoverlabel` dans `defaultPlotlyLayout` (fond surface, bordure token, texte primaire).

## Espacements

Tokens `--space-*` ; sections `.bi-section` avec `margin-top`.

## Responsive

- KPI : 2 colonnes &lt; 720px, 1 colonne &lt; 480px
- Filtres : actions en pleine largeur sur mobile
- Plotly : `responsive: true` + `ResizeObserver`

## Impression

`print.css` masque navbar / sidebar / filtres / modebar ; évite les coupures dans cartes et charts.
