import '../constants/api_endpoints.dart';
import '../core/network/api_service.dart';
import '../core/storage/secure_storage_service.dart';
import '../models/parent_identity.dart';

/// Déconnexion et gestion de session côté API + stockage local.
class AuthService {
  AuthService({
    required ApiService api,
    required SecureStorageService storage,
  })  : _api = api,
        _storage = storage;

  final ApiService _api;
  final SecureStorageService _storage;

  Future<bool> hasJwtSession() => _storage.hasJwtSession();

  Future<bool> hasSession() => _storage.hasSession();

  Future<ParentIdentity?> readParentSession() =>
      _storage.readParentSession();

  Future<void> persistPhoneVerifiedSession(ParentIdentity identity) =>
      _storage.saveParentSession(identity);

  Future<void> logout() async {
    final refresh = await _storage.readRefreshToken();
    try {
      if (refresh != null && refresh.isNotEmpty) {
        await _api.post(
          ApiEndpoints.logout,
          data: {'refresh': refresh},
        );
      }
    } catch (_) {
      // On efface quand même la session locale.
    } finally {
      await _storage.clearAllSessions();
    }
  }

  Future<void> clearLocalSession() => _storage.clearAllSessions();
}
