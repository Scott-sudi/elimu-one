import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../constants/app_constants.dart';
import '../../core/theme/app_theme_colors.dart';
import '../../models/child_models.dart';
import '../../providers/children_providers.dart';
import '../../utils/friendly_error.dart';
import '../../widgets/children/child_card.dart';
import '../../widgets/children/children_empty_state.dart';
import 'child_attendance_screen.dart';
import 'child_discipline_screen.dart';
import 'child_finance_screen.dart';
import 'student_id_card_screen.dart';

/// Écran « Mes Enfants » — maquette (sans Devoirs ; Voir conservé).
class ChildrenScreen extends ConsumerWidget {
  const ChildrenScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncChildren = ref.watch(childrenListProvider);

    return Scaffold(
      backgroundColor: context.appBackground,
      appBar: AppBar(
        backgroundColor: context.appPrimary,
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
        title: const Text(
          'Mes Enfants',
          style: TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      body: asyncChildren.when(
        loading: () => Center(
          child: CircularProgressIndicator(color: context.appPrimary),
        ),
        error: (error, _) => _ErrorState(
          message: friendlyErrorMessage(error),
          onRetry: () => ref.invalidate(childrenListProvider),
        ),
        data: (children) {
          if (children.isEmpty) {
            return RefreshIndicator(
              color: context.appPrimary,
              onRefresh: () async {
                ref.invalidate(childrenListProvider);
                await ref.read(childrenListProvider.future);
              },
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                children: [
                  SizedBox(
                    height: MediaQuery.sizeOf(context).height * 0.55,
                    child: const ChildrenEmptyState(),
                  ),
                ],
              ),
            );
          }

          return RefreshIndicator(
            color: context.appPrimary,
            onRefresh: () async {
              ref.invalidate(childrenListProvider);
              await ref.read(childrenListProvider.future);
            },
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(
                AppConstants.pagePadding,
                16,
                AppConstants.pagePadding,
                24,
              ),
              itemCount: children.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (context, index) {
                final child = children[index];
                return ChildCard(
                  child: child,
                  onOpenProfile: () => _openDetail(context, child),
                  onAction: (action) => _openAction(context, child, action),
                );
              },
            ),
          );
        },
      ),
    );
  }

  void _openDetail(BuildContext context, ChildSummary child) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => StudentIdCardScreen(child: child),
      ),
    );
  }

  void _openAction(
    BuildContext context,
    ChildSummary child,
    ChildQuickAction action,
  ) {
    final Widget screen = switch (action) {
      ChildQuickAction.presence => ChildAttendanceScreen(
          child: child,
          kind: 'present',
        ),
      ChildQuickAction.absences => ChildAttendanceScreen(
          child: child,
          kind: 'absent',
        ),
      ChildQuickAction.discipline => ChildDisciplineScreen(child: child),
      ChildQuickAction.payments => ChildFinanceScreen(child: child),
    };
    Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => screen),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({
    required this.message,
    required this.onRetry,
  });

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.wifi_off_outlined,
              size: 48,
              color: context.appPrimary,
            ),
            const SizedBox(height: 12),
            Text(
              message,
              textAlign: TextAlign.center,
              style: TextStyle(color: context.appTextSecondary),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: onRetry,
              child: const Text('Réessayer'),
            ),
          ],
        ),
      ),
    );
  }
}
