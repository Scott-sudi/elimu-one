import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../models/parent_identity.dart';
import '../auth/auth_step.dart';
import '../network/auth_interceptor.dart';

/// Clés de session parent (provisoire jusqu'au JWT complet).
abstract final class ParentSessionKeys {
  static const guardianId = 'kalunga_parent_guardian_id';
  static const displayName = 'kalunga_parent_display_name';
  static const phone = 'kalunga_parent_phone';
  static const email = 'kalunga_parent_email';
  static const authStep = 'kalunga_parent_auth_step';
  static const phoneVerified = 'kalunga_parent_phone_verified';
}

/// Abstraction de stockage (secure sur mobile, SharedPreferences sur web).
///
/// `flutter_secure_storage` peut bloquer indéfiniment sur Flutter Web →
/// écran blanc. Sur le web on utilise SharedPreferences.
abstract class TokenStore {
  Future<void> write({required String key, required String? value});
  Future<String?> read({required String key});
  Future<void> delete({required String key});
}

class SecureTokenStore implements TokenStore {
  SecureTokenStore([FlutterSecureStorage? storage])
      : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(encryptedSharedPreferences: true),
            );

  final FlutterSecureStorage _storage;

  /// Exposé pour Dio / AuthInterceptor.
  FlutterSecureStorage get flutterSecureStorage => _storage;

  @override
  Future<void> write({required String key, required String? value}) {
    if (value == null) return _storage.delete(key: key);
    return _storage.write(key: key, value: value);
  }

  @override
  Future<String?> read({required String key}) => _storage.read(key: key);

  @override
  Future<void> delete({required String key}) => _storage.delete(key: key);
}

class PreferencesTokenStore implements TokenStore {
  PreferencesTokenStore(this._prefs);

  final SharedPreferences _prefs;

  @override
  Future<void> write({required String key, required String? value}) async {
    if (value == null) {
      await _prefs.remove(key);
    } else {
      await _prefs.setString(key, value);
    }
  }

  @override
  Future<String?> read({required String key}) async => _prefs.getString(key);

  @override
  Future<void> delete({required String key}) async {
    await _prefs.remove(key);
  }
}

/// Accès sécurisé aux jetons JWT + session parent provisoire.
class SecureStorageService {
  SecureStorageService({
    required TokenStore store,
    FlutterSecureStorage? secureStorageForDio,
  })  : _store = store,
        storage = secureStorageForDio ??
            (store is SecureTokenStore
                ? store.flutterSecureStorage
                : const FlutterSecureStorage());

  final TokenStore _store;

  /// Instance partagée avec [ApiService] / intercepteurs Dio (mobile).
  /// Sur web, l'intercepteur lit aussi via [TokenStore] indirectement
  /// tant que les clés JWT sont synchronisées — le Dio interceptor
  /// utilise encore FlutterSecureStorage ; on expose donc une instance
  /// (peu utilisée sur web tant qu'il n'y a pas de JWT).
  final FlutterSecureStorage storage;

  /// Factory recommandée (web-safe).
  static Future<SecureStorageService> create() async {
    if (kIsWeb) {
      final prefs = await SharedPreferences.getInstance();
      return SecureStorageService(store: PreferencesTokenStore(prefs));
    }
    final secure = SecureTokenStore();
    return SecureStorageService(
      store: secure,
      secureStorageForDio: secure.flutterSecureStorage,
    );
  }

  Future<void> saveTokens({
    required String access,
    required String refresh,
  }) async {
    await _store.write(key: TokenStorageKeys.access, value: access);
    await _store.write(key: TokenStorageKeys.refresh, value: refresh);
  }

  Future<String?> readAccessToken() =>
      _store.read(key: TokenStorageKeys.access);

  Future<String?> readRefreshToken() =>
      _store.read(key: TokenStorageKeys.refresh);

  Future<bool> hasJwtSession() async {
    final access = await readAccessToken();
    return access != null && access.isNotEmpty;
  }

  Future<bool> hasSession() async {
    if (await hasJwtSession()) return true;
    return hasPhoneVerifiedSession();
  }

  Future<bool> hasPhoneVerifiedSession() async {
    final flag = await _store.read(key: ParentSessionKeys.phoneVerified);
    return flag == '1';
  }

  Future<void> saveParentSession(ParentIdentity identity) async {
    await _store.write(
      key: ParentSessionKeys.guardianId,
      value: identity.guardianPublicId,
    );
    await _store.write(
      key: ParentSessionKeys.displayName,
      value: identity.displayName,
    );
    await _store.write(
      key: ParentSessionKeys.phone,
      value: identity.phone,
    );
    await _store.write(
      key: ParentSessionKeys.email,
      value: identity.email,
    );
    await _store.write(
      key: ParentSessionKeys.authStep,
      value: AuthStep.completed.apiValue,
    );
    await _store.write(key: ParentSessionKeys.phoneVerified, value: '1');
  }

  Future<ParentIdentity?> readParentSession() async {
    if (!await hasPhoneVerifiedSession()) return null;
    final id = await _store.read(key: ParentSessionKeys.guardianId);
    final name = await _store.read(key: ParentSessionKeys.displayName);
    final phone = await _store.read(key: ParentSessionKeys.phone);
    final email = await _store.read(key: ParentSessionKeys.email);
    if (id == null || id.isEmpty) return null;
    return ParentIdentity(
      guardianPublicId: id,
      displayName: name ?? '',
      phone: phone ?? '',
      email: email ?? '',
      nextAuthStep: AuthStep.completed,
    );
  }

  Future<void> clearTokens() async {
    await _store.delete(key: TokenStorageKeys.access);
    await _store.delete(key: TokenStorageKeys.refresh);
  }

  Future<void> clearParentSession() async {
    await _store.delete(key: ParentSessionKeys.guardianId);
    await _store.delete(key: ParentSessionKeys.displayName);
    await _store.delete(key: ParentSessionKeys.phone);
    await _store.delete(key: ParentSessionKeys.email);
    await _store.delete(key: ParentSessionKeys.authStep);
    await _store.delete(key: ParentSessionKeys.phoneVerified);
  }

  Future<void> clearAllSessions() async {
    await clearTokens();
    await clearParentSession();
  }
}
