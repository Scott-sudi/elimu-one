import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../constants/app_constants.dart';
import '../../core/l10n/app_strings.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_theme_colors.dart';
import '../../models/notification_models.dart';
import '../../providers/home_providers.dart';
import '../../providers/notifications_providers.dart';
import '../../providers/settings_providers.dart';
import '../../utils/friendly_error.dart';
import '../../utils/notification_sort.dart';
import '../../utils/notification_time.dart';
import 'notification_detail_router.dart';

/// Onglet Notifications — filtres Toutes / Générales / Scolaires / Financières.
class NotificationsScreen extends ConsumerStatefulWidget {
  const NotificationsScreen({super.key});

  @override
  ConsumerState<NotificationsScreen> createState() =>
      _NotificationsScreenState();
}

class _NotificationsScreenState extends ConsumerState<NotificationsScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs;
  bool _markingRead = false;
  int _visibleCount = _pageSize;

  static const _pageSize = 10;
  static const _filterKeys = ['toutes', 'generales', 'scolaires', 'financieres'];

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: _filterKeys.length, vsync: this);
    _tabs.addListener(() {
      if (!_tabs.indexIsChanging) {
        setState(() => _visibleCount = _pageSize);
      }
    });
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  List<({String key, String label})> _filters(WidgetRef ref) {
    final s = ref.watch(appStringsProvider);
    return [
      (key: 'toutes', label: s.filterAll),
      (key: 'generales', label: s.filterGeneral),
      (key: 'scolaires', label: s.filterSchool),
      (key: 'financieres', label: s.filterFinance),
    ];
  }

  List<ParentNotificationItem> _filtered(
    List<ParentNotificationItem> items,
    String key,
  ) {
    final list = key == 'toutes'
        ? List<ParentNotificationItem>.from(items)
        : items.where((e) => e.filterBucket == key).toList();
    // Même tri date pour Toutes / Générale / Scolaire / Financière.
    sortParentNotificationsNewestFirst(list);
    return list;
  }

  Future<void> _markAllAsRead(AppStrings s) async {
    if (_markingRead) return;
    setState(() => _markingRead = true);
    try {
      await markNotificationsAsSeen(ref);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(s.markedAllAsRead)),
      );
    } finally {
      if (mounted) setState(() => _markingRead = false);
    }
  }

  Future<void> _openFilterSheet(
    BuildContext context,
    AppStrings s,
    List<({String key, String label})> filters,
  ) async {
    final selected = await showModalBottomSheet<int>(
      context: context,
      backgroundColor: context.appCard,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                child: Text(
                  s.filterNotifications,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              for (var i = 0; i < filters.length; i++)
                ListTile(
                  title: Text(filters[i].label),
                  trailing: i == _tabs.index
                      ? Icon(Icons.check, color: context.appPrimary)
                      : null,
                  onTap: () => Navigator.pop(ctx, i),
                ),
              const SizedBox(height: 8),
            ],
          ),
        );
      },
    );
    if (selected != null && selected != _tabs.index) {
      _tabs.animateTo(selected);
      setState(() => _visibleCount = _pageSize);
    }
  }

  @override
  Widget build(BuildContext context) {
    final asyncData = ref.watch(parentNotificationsProvider);
    final s = ref.watch(appStringsProvider);
    final filters = _filters(ref);
    final currentKey = filters[_tabs.index].key;
    final hasUnread = asyncData.maybeWhen(
      data: (r) => r.items.any((e) => !e.isRead) || r.unreadCount > 0,
      orElse: () => false,
    );

    return Scaffold(
      backgroundColor: context.appBackground,
      appBar: AppBar(
        backgroundColor: context.appCard,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: true,
        automaticallyImplyLeading: false,
        title: Text(
          s.notificationsTitle,
          style: TextStyle(
            color: context.appTextPrimary,
            fontWeight: FontWeight.w700,
            fontSize: 18,
          ),
        ),
        actions: [
          if (hasUnread || _markingRead)
            IconButton(
              tooltip: s.markAllAsRead,
              onPressed: _markingRead ? null : () => _markAllAsRead(s),
              icon: _markingRead
                  ? SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: context.appPrimary,
                      ),
                    )
                  : Icon(
                      Icons.done_all,
                      color: context.appPrimary,
                    ),
            ),
          IconButton(
            tooltip: s.filterNotifications,
            onPressed: () => _openFilterSheet(context, s, filters),
            icon: Icon(Icons.filter_list, color: context.appTextPrimary),
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(48),
          child: Container(
            alignment: Alignment.centerLeft,
            decoration: BoxDecoration(
              color: context.appCard,
              border: Border(
                bottom: BorderSide(color: context.appDivider, width: 1),
              ),
            ),
            child: TabBar(
              controller: _tabs,
              isScrollable: true,
              tabAlignment: TabAlignment.start,
              labelColor: context.appPrimary,
              unselectedLabelColor: context.appTextSecondary,
              labelStyle: const TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 14,
              ),
              unselectedLabelStyle: const TextStyle(
                fontWeight: FontWeight.w500,
                fontSize: 14,
              ),
              indicatorColor: context.appPrimary,
              indicatorWeight: 3,
              dividerColor: Colors.transparent,
              tabs: [for (final f in filters) Tab(text: f.label)],
            ),
          ),
        ),
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
                Text(
                  friendlyErrorMessage(e),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                ElevatedButton(
                  onPressed: () =>
                      ref.invalidate(parentNotificationsProvider),
                  child: Text(s.retry),
                ),
              ],
            ),
          ),
        ),
        data: (result) {
          final items = _filtered(result.items, currentKey);
          if (items.isEmpty) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      result.items.isEmpty
                          ? s.noNotifications
                          : s.noNotificationsIn(filters[_tabs.index].label),
                      textAlign: TextAlign.center,
                      style: TextStyle(color: context.appTextSecondary),
                    ),
                    if (currentKey == 'scolaires') ...[
                      const SizedBox(height: 10),
                      Text(
                        s.scolairesHint,
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: context.appTextSecondary.withOpacity(0.9),
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            );
          }

          final shown = items.take(_visibleCount).toList();
          final hasMore = shown.length < items.length;

          return RefreshIndicator(
            color: AppColors.primary,
            onRefresh: () async {
              setState(() => _visibleCount = _pageSize);
              ref.invalidate(parentNotificationsProvider);
              await ref.read(parentNotificationsProvider.future);
            },
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
              itemCount: shown.length + (hasMore ? 1 : 0),
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (context, index) {
                if (index >= shown.length) {
                  return Padding(
                    padding: const EdgeInsets.only(top: 4, bottom: 8),
                    child: Center(
                      child: TextButton(
                        onPressed: () {
                          setState(() {
                            _visibleCount += _pageSize;
                          });
                        },
                        child: Text(
                          s.seeMore,
                          style: TextStyle(
                            color: context.appPrimary,
                            fontWeight: FontWeight.w700,
                            fontSize: 14.5,
                          ),
                        ),
                      ),
                    ),
                  );
                }
                return _NotificationCard(item: shown[index]);
              },
            ),
          );
        },
      ),
    );
  }
}

class _NotificationCard extends StatelessWidget {
  const _NotificationCard({required this.item});

  final ParentNotificationItem item;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: context.appCard,
      borderRadius: BorderRadius.circular(AppConstants.radiusLarge),
      elevation: context.isDarkTheme ? 0 : 1,
      shadowColor: AppColors.shadow,
      child: InkWell(
        onTap: () => openNotificationDetail(context, item),
        borderRadius: BorderRadius.circular(AppConstants.radiusLarge),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: item.iconBackground,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(item.icon, color: Colors.white, size: 24),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.title,
                      style: TextStyle(
                        color: context.appTextPrimary,
                        fontSize: 14.5,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      item.subtitle,
                      style: TextStyle(
                        color: context.appTextSecondary,
                        fontSize: 12.5,
                        height: 1.35,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      notificationTimeLabel(
                        item.occurredAt,
                        item.timestampLabel,
                      ),
                      style: TextStyle(
                        color: context.appTextSecondary.withOpacity(0.85),
                        fontSize: 11.5,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: item.isRead
                    ? Icon(
                        Icons.chevron_right,
                        color: context.appTextSecondary,
                        size: 22,
                      )
                    : Container(
                        width: 9,
                        height: 9,
                        decoration: BoxDecoration(
                          color: context.appPrimary,
                          shape: BoxShape.circle,
                        ),
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
