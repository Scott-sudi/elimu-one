# Rapport final — Module Comptabilité Kalunga
# Date: 2026-07-27

## Livré

Module Comptabilité dans `apps.finance` (pas de 2ᵉ app), intégré au shell existant.

### Accès & année
- `User.is_comptable()`, `AccountantRequiredMixin`, permission API `IsAccountant`
- Redirection login/dashboard COMPTABLE → sélection d’année ou `finance:dashboard`
- Même session d’année que le Secrétariat (`secretariat_academic_year_id`) pour SECRETAIRE + COMPTABLE
- Menu navbar COMPTABLE complet (frais, demandes, classes, situation élèves, paiements, reçus, impayés, rapports)
- Extension Secrétariat : « Validation des frais »

### Domaine
- Modèles : FeeCategory, SchoolFee, FeeTarget, FeeApprovalHistory, FeeRevisionRequest (préparé, UI inactive), StudentFeeObligation, Payment, PaymentAllocation, ReceiptSequence
- Workflow frais : BROUILLON → EN_ATTENTE → APPROUVE / REJETE (+ archive)
- Obligations à l’approbation + hook inscription + sync transfert
- Paiements avec allocations, reçus `REC-{année}-{seq}`, PDF reportlab, annulation + restauration soldes
- Impayés, rapports, exports CSV / XLSX / PDF
- API DRF `/api/v1/finance/` (dashboard, catégories, frais, paiements ; approve/reject côté secrétaire)

### Technique MySQL
- Les tables `accounts_*` étaient en MyISAM : conversion InnoDB nécessaire pour les FK finance
- Migrations `finance.0001` + `0002_feerevisionrequest` appliquées

## Hors scope (respecté)
Discipline, Flutter, notifications mobiles, BI, salaires, fournisseurs, paie, activation UI des remises/exonérations/révisions.

## Tests
- Suite dédiée : `tests/test_finance_module.py` (workflow frais, obligations, paiements/annulation, API, UI)
- Non-régression : admin, secrétariat, réinscription, téléphone responsable, année — **58 tests OK**
- Base de tests : SQLite en mémoire (`config.settings.test`)
