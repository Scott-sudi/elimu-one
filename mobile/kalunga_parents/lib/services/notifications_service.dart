import '../constants/api_endpoints.dart';
import '../core/errors/api_exception.dart';
import '../core/network/api_service.dart';
import '../models/notification_models.dart';

/// Inbox notifications parents — API Django.
class NotificationsService {
  NotificationsService({required ApiService api}) : _api = api;

  final ApiService _api;

  Future<ParentNotificationsResult> fetchNotifications({
    required String guardianPublicId,
    int limit = 40,
  }) async {
    try {
      final response = await _api.get<ParentNotificationsResult>(
        ApiEndpoints.parentNotifications,
        queryParameters: {
          'guardian_public_id': guardianPublicId,
          'limit': '$limit',
        },
        parser: (raw) => ParentNotificationsResult.fromJson(
          Map<String, dynamic>.from(raw as Map),
        ),
      );
      return response.data ??
          const ParentNotificationsResult(items: []);
    } on ApiException {
      rethrow;
    } catch (_) {
      throw const NetworkException();
    }
  }

  /// Marque toute l'inbox comme lue côté serveur (badge persistant).
  Future<ParentNotificationsResult> markAllRead({
    required String guardianPublicId,
  }) async {
    try {
      final response = await _api.post<ParentNotificationsResult>(
        ApiEndpoints.parentNotificationsMarkRead,
        data: {'guardian_public_id': guardianPublicId},
        parser: (raw) => ParentNotificationsResult.fromJson(
          Map<String, dynamic>.from(raw as Map),
        ),
      );
      return response.data ??
          const ParentNotificationsResult(items: []);
    } on ApiException {
      rethrow;
    } catch (_) {
      throw const NetworkException();
    }
  }
}
