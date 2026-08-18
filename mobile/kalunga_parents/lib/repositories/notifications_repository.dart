import '../models/notification_models.dart';
import '../services/auth_service.dart';
import '../services/notifications_service.dart';

class NotificationsRepository {
  NotificationsRepository({
    required NotificationsService notificationsService,
    required AuthService authService,
  })  : _notifications = notificationsService,
        _auth = authService;

  final NotificationsService _notifications;
  final AuthService _auth;

  Future<String> _guardianId() async {
    final parent = await _auth.readParentSession();
    return parent?.guardianPublicId ?? '';
  }

  Future<ParentNotificationsResult> load() async {
    return _notifications.fetchNotifications(
      guardianPublicId: await _guardianId(),
      limit: 80,
    );
  }

  Future<ParentNotificationsResult> markAllRead() async {
    return _notifications.markAllRead(
      guardianPublicId: await _guardianId(),
    );
  }
}
