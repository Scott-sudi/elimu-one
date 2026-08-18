import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_theme_colors.dart';
import '../../models/child_models.dart';
import '../../providers/child_modules_providers.dart';

/// Situation financière de l'élève (frais payés / restants — base finance).
class ChildFinanceScreen extends ConsumerWidget {
  const ChildFinanceScreen({super.key, required this.child});

  final ChildSummary child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncData = ref.watch(childFinanceProvider(child.id));

    return Scaffold(
      backgroundColor: context.appBackground,
      appBar: AppBar(
        backgroundColor: context.appPrimary,
        foregroundColor: Colors.white,
        title: const Text('Paiement'),
      ),
      body: asyncData.when(
        loading: () => Center(
          child: CircularProgressIndicator(color: context.appPrimary),
        ),
        error: (e, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(e.toString(), textAlign: TextAlign.center),
                const SizedBox(height: 12),
                ElevatedButton(
                  onPressed: () =>
                      ref.invalidate(childFinanceProvider(child.id)),
                  child: const Text('Réessayer'),
                ),
              ],
            ),
          ),
        ),
        data: (situation) {
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (situation.schoolYearLabel.isNotEmpty)
                Text(
                  'Année scolaire ${situation.schoolYearLabel}',
                  style: TextStyle(color: context.appTextSecondary),
                ),
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFF111111),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Résumé',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 10),
                    _SummaryRow(
                      label: 'Dû',
                      value: situation.amountDueLabel,
                    ),
                    _SummaryRow(
                      label: 'Payé',
                      value: situation.amountPaidLabel,
                    ),
                    _SummaryRow(
                      label: 'Reste',
                      value: situation.amountRemainingLabel,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              const Text(
                'Frais / obligations',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 16,
                ),
              ),
              const SizedBox(height: 8),
              if (situation.obligations.isEmpty)
                Text(
                  'Aucune obligation pour le moment.',
                  style: TextStyle(color: context.appTextSecondary),
                )
              else
                ...situation.obligations.map(
                  (o) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Material(
                      color: context.appCard,
                      borderRadius: BorderRadius.circular(12),
                      child: ListTile(
                        title: Text(
                          o.label,
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                        subtitle: Text(
                          'Payé ${o.amountPaidLabel} · Reste ${o.amountRemainingLabel}',
                        ),
                        trailing: Text(
                          o.amountDueLabel,
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                      ),
                    ),
                  ),
                ),
              const SizedBox(height: 16),
              const Text(
                'Paiements enregistrés',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 16,
                ),
              ),
              const SizedBox(height: 8),
              if (situation.payments.isEmpty)
                Text(
                  'Aucun paiement enregistré.',
                  style: TextStyle(color: context.appTextSecondary),
                )
              else
                ...situation.payments.map(
                  (p) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Material(
                      color: context.appCard,
                      borderRadius: BorderRadius.circular(12),
                      child: ListTile(
                        title: Text(
                          p.receiptNumber,
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                        subtitle: Text('${p.dateLabel} · ${p.statusLabel}'),
                        trailing: Text(
                          p.amountLabel,
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

class _SummaryRow extends StatelessWidget {
  const _SummaryRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: TextStyle(color: Colors.white.withOpacity(0.9)),
            ),
          ),
          Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
