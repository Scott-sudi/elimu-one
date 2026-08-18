import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme_colors.dart';
import '../../models/notification_models.dart';
import '../../providers/home_providers.dart';
import '../../providers/live_refresh_provider.dart';
import '../../services/push_notification_service.dart';
import '../../widgets/in_app_alert_host.dart';
import '../../widgets/navigation/custom_bottom_navbar.dart';
import '../account/account_screen.dart';
import '../children/children_screen.dart';
import '../home/home_screen.dart';
import '../notifications/notification_detail_router.dart';
import '../notifications/notifications_screen.dart';

/// Coquille principale : Accueil + onglets navigables (4).
class MainShell extends ConsumerWidget {
  const MainShell({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Active l'actualisation auto + canal notifications.
    ref.watch(liveRefreshProvider);
    ref.watch(pushBootstrapProvider);

    final index = ref.watch(bottomNavIndexProvider);
    // Ancien index « À propos » (3) → Mon Compte (3 maintenant).
    final safeIndex = index.clamp(0, 3);
    if (safeIndex != index) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(bottomNavIndexProvider.notifier).state = safeIndex;
      });
    }

    final dashboard = ref.watch(homeDashboardProvider);
    final serverUnread = dashboard.maybeWhen(
      data: (d) => d.overview.unreadNotificationsBadge,
      orElse: () => 0,
    );
    final badge = visibleNotificationsBadge(ref, serverUnread);

    // Dès que l'onglet Notifications est actif → marquer comme lu.
    ref.listen<int>(bottomNavIndexProvider, (prev, next) {
      if (next == 2 && prev != 2) {
        markNotificationsAsSeen(ref);
      }
    });
    ref.listen<ParentNotificationItem?>(pendingPushNotificationProvider,
        (previous, next) {
      if (next == null || next == previous) return;
      ref.read(pendingPushNotificationProvider.notifier).state = null;
      ref.read(bottomNavIndexProvider.notifier).state = 2;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (context.mounted) {
          openNotificationDetail(context, next);
        }
      });
    });

    return InAppAlertHost(
      child: Scaffold(
        backgroundColor: context.appBackground,
        body: SafeArea(
          bottom: false,
          child: IndexedStack(
            index: safeIndex,
            children: [
              HomeScreen(
                onOpenNotifications: () async {
                  ref.read(bottomNavIndexProvider.notifier).state = 2;
                  await markNotificationsAsSeen(ref);
                },
              ),
              const ChildrenScreen(),
              const NotificationsScreen(),
              const AccountScreen(),
            ],
          ),
        ),
        bottomNavigationBar: CustomBottomNavbar(
          currentIndex: safeIndex,
          notificationBadge: badge,
          onTap: (value) async {
            ref.read(bottomNavIndexProvider.notifier).state = value;
            if (value == 2) {
              await markNotificationsAsSeen(ref);
            }
          },
        ),
      ),
    );
  }
}
