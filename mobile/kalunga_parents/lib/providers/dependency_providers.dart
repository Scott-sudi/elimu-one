import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/network/api_service.dart';
import '../core/storage/secure_storage_service.dart';
import '../repositories/auth_repository.dart';
import '../repositories/child_modules_repository.dart';
import '../repositories/children_repository.dart';
import '../repositories/home_repository.dart';
import '../repositories/notifications_repository.dart';
import '../services/auth_service.dart';
import '../services/child_modules_service.dart';
import '../services/children_service.dart';
import '../services/home_service.dart';
import '../services/login_service.dart';
import '../services/notifications_service.dart';
import '../services/notification_detail_service.dart';
import '../services/phone_auth_service.dart';
import '../services/user_service.dart';

/// Injection des dépendances (Clean Architecture + Riverpod).
///
/// [secureStorageProvider] est surchargé dans `main()` après initialisation
/// asynchrone (SharedPreferences sur web / Keystore sur mobile).

final secureStorageProvider = Provider<SecureStorageService>((ref) {
  throw StateError(
    'secureStorageProvider doit être initialisé dans main() via overrideWithValue.',
  );
});

final apiServiceProvider = Provider<ApiService>((ref) {
  final secure = ref.watch(secureStorageProvider);
  return ApiService(
    storage: secure.storage,
    onSessionExpired: () {},
  );
});

final phoneAuthServiceProvider = Provider<PhoneAuthService>((ref) {
  return PhoneAuthService(api: ref.watch(apiServiceProvider));
});

final loginServiceProvider = Provider<LoginService>((ref) {
  return LoginService(
    api: ref.watch(apiServiceProvider),
    storage: ref.watch(secureStorageProvider),
  );
});

final authServiceProvider = Provider<AuthService>((ref) {
  return AuthService(
    api: ref.watch(apiServiceProvider),
    storage: ref.watch(secureStorageProvider),
  );
});

final userServiceProvider = Provider<UserService>((ref) {
  return UserService(api: ref.watch(apiServiceProvider));
});

final homeServiceProvider = Provider<HomeService>((ref) {
  return HomeService(
    api: ref.watch(apiServiceProvider),
    useMockData: false,
  );
});

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(
    phoneAuthService: ref.watch(phoneAuthServiceProvider),
    loginService: ref.watch(loginServiceProvider),
    authService: ref.watch(authServiceProvider),
    userService: ref.watch(userServiceProvider),
  );
});

final homeRepositoryProvider = Provider<HomeRepository>((ref) {
  return HomeRepository(
    homeService: ref.watch(homeServiceProvider),
    authService: ref.watch(authServiceProvider),
  );
});

final childrenServiceProvider = Provider<ChildrenService>((ref) {
  return ChildrenService(
    api: ref.watch(apiServiceProvider),
    useMockData: false,
  );
});

final childrenRepositoryProvider = Provider<ChildrenRepository>((ref) {
  return ChildrenRepository(
    childrenService: ref.watch(childrenServiceProvider),
    authService: ref.watch(authServiceProvider),
  );
});

final childModulesServiceProvider = Provider<ChildModulesService>((ref) {
  return ChildModulesService(api: ref.watch(apiServiceProvider));
});

final childModulesRepositoryProvider = Provider<ChildModulesRepository>((ref) {
  return ChildModulesRepository(
    modulesService: ref.watch(childModulesServiceProvider),
    authService: ref.watch(authServiceProvider),
  );
});

final notificationsServiceProvider = Provider<NotificationsService>((ref) {
  return NotificationsService(api: ref.watch(apiServiceProvider));
});

final notificationsRepositoryProvider = Provider<NotificationsRepository>((ref) {
  return NotificationsRepository(
    notificationsService: ref.watch(notificationsServiceProvider),
    authService: ref.watch(authServiceProvider),
  );
});

final notificationDetailServiceProvider = Provider<NotificationDetailService>((ref) {
  return NotificationDetailService(
    api: ref.watch(apiServiceProvider),
    auth: ref.watch(authServiceProvider),
  );
});
