import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_theme_colors.dart';
import '../../models/child_models.dart';
import '../../providers/child_modules_providers.dart';

/// Présences ou absences d'un enfant (données DailyAttendance Django).
class ChildAttendanceScreen extends ConsumerWidget {
  const ChildAttendanceScreen({
    super.key,
    required this.child,
    required this.kind,
  });

  final ChildSummary child;
  /// `present` ou `absent`
  final String kind;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final title = kind == 'absent' ? 'Absences' : 'Présence';
    final asyncData = ref.watch(
      childAttendanceProvider((studentId: child.id, kind: kind)),
    );

    return Scaffold(
      backgroundColor: context.appBackground,
      appBar: AppBar(
        backgroundColor: context.appPrimary,
        foregroundColor: Colors.white,
        title: Text(title),
      ),
      body: asyncData.when(
        loading: () => Center(
          child: CircularProgressIndicator(color: context.appPrimary),
        ),
        error: (e, _) => _CenteredMessage(
          message: e.toString(),
          onRetry: () => ref.invalidate(
            childAttendanceProvider((studentId: child.id, kind: kind)),
          ),
        ),
        data: (result) {
          if (result.days.isEmpty) {
            return _CenteredMessage(
              message: kind == 'absent'
                  ? 'Aucune absence enregistrée pour le moment.'
                  : 'Aucune présence enregistrée pour le moment.',
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: result.days.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (context, index) {
              final day = result.days[index];
              return Material(
                color: context.appCard,
                borderRadius: BorderRadius.circular(12),
                child: ListTile(
                  leading: Icon(
                    kind == 'absent'
                        ? Icons.event_busy_outlined
                        : Icons.event_available_outlined,
                    color: kind == 'absent'
                        ? AppColors.activityMeeting
                        : AppColors.primaryLight,
                  ),
                  title: Text(
                    day.dateLabel,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  subtitle: Text(
                    [
                      day.statusLabel,
                      if (day.note.isNotEmpty) day.note,
                    ].join(' — '),
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}

class _CenteredMessage extends StatelessWidget {
  const _CenteredMessage({required this.message, this.onRetry});

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              message,
              textAlign: TextAlign.center,
              style: TextStyle(color: context.appTextSecondary),
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 16),
              ElevatedButton(onPressed: onRetry, child: const Text('Réessayer')),
            ],
          ],
        ),
      ),
    );
  }
}
