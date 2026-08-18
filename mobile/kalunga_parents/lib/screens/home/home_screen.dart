import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../constants/app_constants.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_theme_colors.dart';
import '../../models/home_models.dart';
import '../../models/notification_models.dart';
import '../../providers/auth_providers.dart';
import '../../providers/home_providers.dart';
import '../../providers/notifications_providers.dart';
import '../../providers/settings_providers.dart';
import '../../utils/friendly_error.dart';
import '../../utils/notification_sort.dart';
import '../../widgets/home/activity_item.dart';
import '../../widgets/home/home_header.dart';
import '../../widgets/home/overview_card.dart';
import '../notifications/notification_detail_router.dart';

/// Page Accueil — reproduction fidèle de la maquette.
class HomeScreen extends ConsumerWidget {
  const HomeScreen({
    super.key,
    this.onOpenNotifications,
  });

  final VoidCallback? onOpenNotifications;

  /// Activités récentes = top 3 de la même inbox triée que « Toutes ».
  List<RecentActivity> _recentActivities(
    HomeDashboard dashboard,
    AsyncValue<ParentNotificationsResult> inbox,
  ) {
    final fromInbox = inbox.maybeWhen(
      data: (result) {
        final items = List<ParentNotificationItem>.from(result.items);
        sortParentNotificationsNewestFirst(items);
        return items.take(3).map((e) => e.asActivity).toList();
      },
      orElse: () => null,
    );
    if (fromInbox != null && fromInbox.isNotEmpty) {
      return fromInbox;
    }
    final fallback = List<RecentActivity>.from(dashboard.activities);
    sortRecentActivitiesNewestFirst(fallback);
    return fallback.take(3).toList();
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncDashboard = ref.watch(homeDashboardProvider);
    final asyncInbox = ref.watch(parentNotificationsProvider);
    final session = ref.watch(authSessionProvider);
    final s = ref.watch(appStringsProvider);
    final sessionName = switch (session) {
      AuthSessionAuthenticated(:final identity) => identity.displayName.trim(),
      _ => '',
    };

    return ColoredBox(
      color: context.appBackground,
      child: asyncDashboard.when(
        loading: () => Center(
          child: CircularProgressIndicator(color: context.appPrimary),
        ),
        error: (error, _) => _ErrorView(
          message: friendlyErrorMessage(error),
          retryLabel: s.retry,
          onRetry: () {
            ref.invalidate(homeDashboardProvider);
            ref.invalidate(parentNotificationsProvider);
          },
        ),
        data: (dashboard) => _HomeBody(
          dashboard: dashboard,
          recentActivities: _recentActivities(dashboard, asyncInbox),
          greetingName: sessionName.isNotEmpty
              ? sessionName
              : dashboard.parentDisplayName,
          notificationCount: visibleNotificationsBadge(
            ref,
            dashboard.overview.unreadNotificationsBadge,
          ),
          onOpenNotifications: onOpenNotifications,
          helloLabel: s.hello,
          welcomeLabel: s.welcomeSchool,
          notificationsTooltip: s.navNotifications,
          overviewTitle: s.overview,
          childrenLabel: s.children,
          notificationsLabel: s.navNotifications,
          averageLabel: s.paidBalance,
          balanceLabel: s.unpaidBalance,
          recentTitle: s.recentActivities,
          seeAllLabel: s.seeAll,
          emptyActivities: s.noRecentActivity,
          onRefresh: () async {
            ref.invalidate(homeDashboardProvider);
            ref.invalidate(parentNotificationsProvider);
            await Future.wait([
              ref.read(homeDashboardProvider.future),
              ref.read(parentNotificationsProvider.future),
            ]);
          },
        ),
      ),
    );
  }
}

class _HomeBody extends StatelessWidget {
  const _HomeBody({
    required this.dashboard,
    required this.recentActivities,
    required this.greetingName,
    required this.notificationCount,
    required this.onRefresh,
    required this.helloLabel,
    required this.welcomeLabel,
    required this.notificationsTooltip,
    required this.overviewTitle,
    required this.childrenLabel,
    required this.notificationsLabel,
    required this.averageLabel,
    required this.balanceLabel,
    required this.recentTitle,
    required this.seeAllLabel,
    required this.emptyActivities,
    this.onOpenNotifications,
  });

  final HomeDashboard dashboard;
  final List<RecentActivity> recentActivities;
  final String greetingName;
  final int notificationCount;
  final Future<void> Function() onRefresh;
  final VoidCallback? onOpenNotifications;
  final String helloLabel;
  final String welcomeLabel;
  final String notificationsTooltip;
  final String overviewTitle;
  final String childrenLabel;
  final String notificationsLabel;
  final String averageLabel;
  final String balanceLabel;
  final String recentTitle;
  final String seeAllLabel;
  final String emptyActivities;

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      color: AppColors.primary,
      onRefresh: onRefresh,
      child: CustomScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: [
          SliverToBoxAdapter(
            child: HomeHeader(
              parentName: greetingName,
              notificationCount: notificationCount,
              onNotificationTap: onOpenNotifications,
              helloLabel: helloLabel,
              welcomeLabel: welcomeLabel,
              notificationsTooltip: notificationsTooltip,
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(
              AppConstants.pagePadding,
              4,
              AppConstants.pagePadding,
              8,
            ),
            sliver: SliverToBoxAdapter(
              child: OverviewCard(
                overview: dashboard.overview,
                overviewTitle: overviewTitle,
                childrenLabel: childrenLabel,
                notificationsLabel: notificationsLabel,
                averageLabel: averageLabel,
                balanceLabel: balanceLabel,
              ),
            ),
          ),
          const SliverToBoxAdapter(child: SizedBox(height: 8)),
          SliverPadding(
            padding: const EdgeInsets.symmetric(
              horizontal: AppConstants.pagePadding,
            ),
            sliver: SliverToBoxAdapter(
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      recentTitle,
                      style: TextStyle(
                        color: context.appTextPrimary,
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  TextButton(
                    onPressed: onOpenNotifications,
                    style: TextButton.styleFrom(
                      foregroundColor: context.appPrimaryLight,
                      padding: EdgeInsets.zero,
                      minimumSize: const Size(0, 36),
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),
                    child: Text(
                      seeAllLabel,
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 13,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SliverToBoxAdapter(child: SizedBox(height: 8)),
          if (recentActivities.isEmpty)
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(
                AppConstants.pagePadding,
                0,
                AppConstants.pagePadding,
                24,
              ),
              sliver: SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  child: Text(
                    emptyActivities,
                    style: TextStyle(
                      color: context.appTextSecondary,
                      fontSize: 13,
                    ),
                  ),
                ),
              ),
            )
          else
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(
                AppConstants.pagePadding,
                0,
                AppConstants.pagePadding,
                24,
              ),
              sliver: SliverList.separated(
                itemCount: recentActivities.length,
                separatorBuilder: (_, __) => const SizedBox(height: 10),
                itemBuilder: (context, index) {
                  final activity = recentActivities[index];
                  return ActivityItem(
                    activity: activity,
                    onTap: () => openNotificationDetail(
                      context,
                      ParentNotificationItem.fromRecentActivity(activity),
                    ),
                  );
                },
              ),
            ),
        ],
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({
    required this.message,
    required this.retryLabel,
    required this.onRetry,
  });

  final String message;
  final String retryLabel;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline, color: context.appPrimary, size: 40),
            const SizedBox(height: 12),
            Text(
              message,
              textAlign: TextAlign.center,
              style: TextStyle(color: context.appTextSecondary),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: onRetry,
              child: Text(retryLabel),
            ),
          ],
        ),
      ),
    );
  }
}
