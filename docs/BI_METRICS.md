# Dictionnaire des indicateurs BI — Kalunga (Préfet)

Ce document décrit les formules **telles qu’implémentées** dans `apps.bi`.
Les calculs sont réalisés dans les services / sélecteurs (jamais dans les templates).
Aucun résultat scolaire / note n’est inventé.

## Statuts modèles (référence)

| Domaine | Champ | Valeurs utilisées |
|---------|-------|-------------------|
| Inscription | `Enrollment.status` | `VALIDEE` (effectif), `BROUILLON`, `ANNULEE`, `CLOTUREE` |
| Élève | `Student.sexe` | `M`, `F`, `O` |
| Obligation | `StudentFeeObligation.status` | hors `ANNULE` pour le dû |
| Paiement | `Payment.status` | `VALIDE` = encaissé ; `ANNULE` **exclu** |
| Présence | `DailyAttendance.status` | `PRESENT`, `RETARD`, `ABSENT`, `ABSENCE_JUSTIFIEE`, … |
| Incident | `DisciplinaryIncident.status` | ouverts : `SIGNALE`, `EN_EXAMEN`, `CONFIRME` |
| Convocation | `ParentSummons.status` | en attente : `PROGRAMMEE`, `TRANSMISE`, `RECUE`, `CONFIRMEE` |

## Vue d’ensemble (`overview_service.build_overview`)

| Indicateur | Formule |
|------------|---------|
| Effectif total | `COUNT(Enrollment)` où `academic_year` + `status = VALIDEE` |
| Classes actives | `COUNT(SchoolClass)` où `academic_year` + `is_active = True` |
| Occupation moyenne (%) | moyenne de `(effectif_validé / max_capacity × 100)` sur les classes avec `max_capacity > 0` |
| Montant attendu | `SUM(amount_due)` sur obligations de l’année, **hors** `status = ANNULE` |
| Montant encaissé | `SUM(amount_total)` sur `Payment` où `status = VALIDE` (les `ANNULE` sont exclus) |
| Solde | `max(montant_attendu − montant_encaisse, 0)` |
| Taux de recouvrement (%) | `montant_encaisse / montant_attendu × 100` (1 décimale) ; `None` si attendu = 0 |
| Taux de présence (%) | `(PRESENT + RETARD) / total_pointages × 100` |
| Retards | `COUNT` où `status = RETARD` |
| Incidents ouverts | incidents non archivés en `SIGNALE` / `EN_EXAMEN` / `CONFIRME` |
| Convocations en attente | convocations en `PROGRAMMEE` / `TRANSMISE` / `RECUE` / `CONFIRMEE` |

### Alertes

- Capacité dépassée : `effectif_validé > max_capacity`
- Recouvrement faible : taux &lt; 50 %
- Incidents graves ouverts : gravité `GRAVE` ou `TRES_GRAVE` encore ouverts

## Effectifs (`enrollment_analytics_service`)

- Effectif = inscriptions `VALIDEE` (filtres optionnels : dates, niveau, section, option, classe, sexe).
- Nouvelles / réinscriptions / transferts = `enrollment_type` (`NOUVELLE_INSCRIPTION`, `REINSCRIPTION`, `TRANSFERT_ENTRANT`).
- Répartition sexe = `student.sexe`.
- Occupation classe = `effectif / max_capacity × 100`.

### Statuts d’occupation

| Statut | Seuil |
|--------|-------|
| Faiblement occupée | &lt; 50 % |
| Occupation normale | 50 % ≤ x &lt; 85 % |
| Presque complète | 85 % ≤ x &lt; 100 % |
| Complète | = 100 % |
| Capacité dépassée | effectif &gt; capacité |

## Finances (`financial_analytics_service`)

| Indicateur | Formule |
|------------|---------|
| Montant attendu | Σ `amount_due` obligations hors `ANNULE` |
| Montant encaissé | Σ `Payment.amount_total` où `status = VALIDE` |
| Solde | `max(attendu − encaissé, 0)` |
| Taux de recouvrement | `encaissé / attendu × 100` |
| Encaissement du jour / mois | même somme filtrée sur `payment_date` |
| Paiements annulés | `COUNT` où `status = ANNULE` (informatif, **non** inclus dans l’encaissé) |
| Élèves en ordre | inscription validée dont Σ `amount_paid` ≥ Σ `amount_due` (obligations hors annulées) |
| Élèves partiels | 0 &lt; payé &lt; dû |
| Élèves sans paiement | payé = 0 et dû &gt; 0 |

Devise : montants en `Decimal` (CDF).

## Assiduité (`attendance_analytics_service`)

| Indicateur | Formule |
|------------|---------|
| Taux de présence | `(PRESENT + RETARD) / total × 100` |
| Absences injustifiées | `status = ABSENT` |
| Absences justifiées | `ABSENCE_JUSTIFIEE` + `MALADE` |
| Minutes de retard | Σ `late_minutes` |
| Sorties autorisées | `status = SORTIE_AUTORISEE` |

Suivi : élèves avec ≥ 3 absences ou ≥ 5 retards (liste indicative).

## Discipline (`discipline_analytics_service`)

| Indicateur | Formule |
|------------|---------|
| Incidents ouverts | `SIGNALE` / `EN_EXAMEN` / `CONFIRME`, `is_archived = False` |
| Incidents clôturés | `CLASSE_SANS_SUITE` / `CLOTURE` |
| Observations positives | catégorie `observation_type = POSITIVE` |
| Récidives | élèves avec ≥ 2 incidents (dans le filtre) |
| Mesures | `DisciplinaryMeasure` non annulées (`is_cancelled = False`) liées à l’année via l’incident |

## Classes (`class_analytics_service`)

Par classe active : effectif validé, capacité, occupation, montants attendu/encaissé (VALIDE), taux de présence, retards, incidents ouverts.

## Comparaisons (`comparison_service`)

Snapshots KPI par `AcademicYear` (effectif, classes, occupation, attendu, encaissé VALIDE, recouvrement, présence, incidents ouverts).  
Ne mélange pas les années dans les vues domaine — uniquement page / API Comparaisons.

## Filtres (`apps.bi.filters`)

GET : `date_from`, `date_to`, `level`, `section`, `option`, `class_id`, `gender`/`sexe`, `fee_id`, `enrollment_status`, `enrollment_type`, `payment_method`, `payment_status`, `attendance_status`, `severity`, `incident_status`, `category_id`, `summons_status`.  
Appliqués seulement si le modèle le permet.

## Exports (`export_service`)

CSV / XLSX (même schéma que le secrétariat : `csv` + `openpyxl`), domaines : `enrollments`, `financial`, `attendance`, `discipline`, `classes`, `comparisons`.
