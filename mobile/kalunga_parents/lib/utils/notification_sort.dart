import '../models/home_models.dart';
import '../models/notification_models.dart';

DateTime _instantOrEpoch(DateTime? value) =>
    value ?? DateTime.fromMillisecondsSinceEpoch(0);

/// Plus récent en haut (création / modification via occurredAt).
void sortParentNotificationsNewestFirst(List<ParentNotificationItem> items) {
  items.sort((a, b) {
    final cmp = _instantOrEpoch(b.occurredAt).compareTo(_instantOrEpoch(a.occurredAt));
    if (cmp != 0) return cmp;
    return b.id.compareTo(a.id);
  });
}

/// Même règle pour l'accueil (activités récentes).
void sortRecentActivitiesNewestFirst(List<RecentActivity> items) {
  items.sort((a, b) {
    final cmp = _instantOrEpoch(b.occurredAt).compareTo(_instantOrEpoch(a.occurredAt));
    if (cmp != 0) return cmp;
    return b.id.compareTo(a.id);
  });
}
