# Tests BI — Kalunga

## Objectifs

- Vérifier les formules documentées dans `docs/BI_METRICS.md`
- Garantir l’exclusion des paiements `ANNULE` des encaissements
- Garantir l’effectif sur inscriptions `VALIDEE` uniquement
- Non-régression des modules Administrateur, Secrétariat, Finance, Discipline

## Emplacement

`backend/apps/bi/tests/`

Exemples attendus :

- `test_overview.py` — KPI vue générale + alertes
- Tests domaine : effectifs, finances, assiduité, discipline, classes, comparaisons
- Tests permissions / rôle Préfet (accès autorisé, autres rôles refusés)
- Tests API envelope `/api/v1/bi/...`
- Tests filtres (`parse_bi_filters`, application sélecteurs)

## Cas critiques

1. **Finances** : `Payment.status = ANNULE` n’entre pas dans `montant_encaisse`
2. **Effectifs** : `Enrollment.status != VALIDEE` exclu du total
3. **Présence** : `(PRESENT + RETARD) / total`
4. **Comparaisons** : pas de mélange d’années hors page / API Comparaisons
5. **Année clôturée** : pages BI toujours accessibles en lecture

## Frontend

Pas de suite Jest obligatoire pour Plotly. Vérifications manuelles / smoke :

- Charts vides → empty state
- `json_script#bi-charts-data` rendu
- Filtres GET rechargent les KPI
- `npm run build` sans erreur (bundle Vite + Plotly)

## Commandes

```bash
# depuis backend, avec venv projet
python manage.py test apps.bi
```

Après modification partagée (menu, auth, année) : relancer aussi les tests des apps touchées.
