# Permissions BI — Kalunga (Préfet)

## Rôle

- Code rôle : `PREFET`
- Accès web : `PrefetRequiredMixin` / `BiViewMixin`
- Accès API : `IsAuthenticated` + `IsPrefet`
- Posture : **lecture seule** sur le module BI (pas de saisie opérationnelle Secrétariat / Finance / Discipline depuis BI)

## Codenames

Définis dans `apps.bi.permissions` et alignés sur `User.Meta.permissions` :

| Codename | Usage |
|----------|--------|
| `view_bi_dashboard` | Vue générale |
| `view_enrollment_analytics` | Effectifs |
| `view_financial_analytics` | Finances |
| `view_attendance_analytics` | Assiduité |
| `view_discipline_analytics` | Discipline |
| `view_class_analytics` | Analyse des classes |
| `view_student_summary` | Synthèse élève (si exposée) |
| `compare_academic_years` | Comparaisons annuelles |
| `export_bi_reports` | Exports CSV / XLSX |

## Année scolaire

- Sélection via le flux Secrétariat existant (`secretariat:academic-year-select`)
- Années **clôturées** : lisibles en BI (pas de gate « année writable »)
- Absence d’année sélectionnée → redirection vers le sélecteur

## Principes

- Masquer le menu ne suffit pas : protéger vues et API
- Ne pas octroyer automatiquement toutes les interfaces métier à l’Administrateur via le menu Préfet
- Exports soumis à `export_bi_reports` / contrôle vue export
