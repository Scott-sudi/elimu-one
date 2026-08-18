import '../constants/api_endpoints.dart';
import '../core/network/api_service.dart';
import '../core/storage/secure_storage_service.dart';
import '../models/auth_tokens.dart';

/// Connexion JWT auprès de Django (`POST /auth/token/`).
class LoginService {
  LoginService({
    required ApiService api,
    required SecureStorageService storage,
  })  : _api = api,
        _storage = storage;

  final ApiService _api;
  final SecureStorageService _storage;

  Future<AuthTokens> login({
    required String username,
    required String password,
  }) async {
    final response = await _api.post<AuthTokens>(
      ApiEndpoints.token,
      data: {
        'username': username,
        'password': password,
      },
      skipAuth: true,
      parser: (raw) => AuthTokens.fromJson(
        Map<String, dynamic>.from(raw as Map),
      ),
    );

    final tokens = response.data;
    if (tokens == null || tokens.access.isEmpty) {
      throw StateError('Jetons manquants dans la réponse.');
    }

    await _storage.saveTokens(
      access: tokens.access,
      refresh: tokens.refresh,
    );
    return tokens;
  }
}
