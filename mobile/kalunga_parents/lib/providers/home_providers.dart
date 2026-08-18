import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/home_models.dart';
import 'auth_providers.dart';
import 'dependency_providers.dart';
import 'notifications_providers.dart';

/// Charge le tableau de bord Accueil (API Django) et synchronise le nom.
final homeDashboardProvider =
    FutureProvider.autoDispose<HomeDashboard>((ref) async {
  final session = ref.watch(authSessionProvider);
  final sessionName = switch (session) {
    AuthSessionAuthenticated(:final identity) => identity.displayName,
    _ => '',
  };

  final repo = ref.watch(homeRepositoryProvider);
  final dashboard = await repo.loadDashboard();

  final liveName = dashboard.parentDisplayName.trim();
  if (liveName.isNotEmpty && liveName != sessionName) {
    await ref.read(authSessionProvider.notifier).syncDisplayName(liveName);
  }

  return dashboard;
});

/// Index de l'onglet actif de la barre de navigation inférieure.
final bottomNavIndexProvider = StateProvider<int>((ref) => 0);

/// Masque optimiste du badge juste après ouverture (avant refresh API).
final notificationsBadgeOptimisticZeroProvider = StateProvider<bool>((ref) => false);

/// Badge = non-lus serveur (persistés en DB après mark-read).
int visibleNotificationsBadge(WidgetRef ref, int serverUnread) {
  if (ref.watch(notificationsBadgeOptimisticZeroProvider)) {
    return 0;
  }
  return serverUnread > 0 ? serverUnread : 0;
}

/// Marque l'inbox comme lue **sur le serveur** puis rafraîchit Accueil / liste.
Future<void> markNotificationsAsSeen(WidgetRef ref) async {
  ref.read(notificationsBadgeOptimisticZeroProvider.notifier).state = true;
  try {
    await ref.read(notificationsRepositoryProvider).markAllRead();
  } catch (_) {
    // Si l'API n'est pas encore déployée, on garde le masque optimiste
    // pour cette session uniquement.
  }
  ref.invalidate(parentNotificationsProvider);
  ref.invalidate(homeDashboardProvider);
  try {
    await Future.wait([
      ref.read(parentNotificationsProvider.future),
      ref.read(homeDashboardProvider.future),
    ]);
  } catch (_) {}
  // Si le serveur confirme unread=0, on peut lâcher le masque optimiste.
  final dash = ref.read(homeDashboardProvider);
  final unread = dash.maybeWhen(
    data: (d) => d.overview.unreadNotificationsBadge,
    orElse: () => -1,
  );
  if (unread == 0) {
    ref.read(notificationsBadgeOptimisticZeroProvider.notifier).state = false;
  }
}
