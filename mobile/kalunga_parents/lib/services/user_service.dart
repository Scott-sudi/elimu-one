import '../constants/api_endpoints.dart';
import '../core/network/api_service.dart';
import '../models/user_model.dart';

/// Profil utilisateur courant (`GET /auth/me/`).
class UserService {
  UserService({required ApiService api}) : _api = api;

  final ApiService _api;

  Future<UserModel> fetchCurrentUser() async {
    final response = await _api.get<UserModel>(
      ApiEndpoints.me,
      parser: (raw) => UserModel.fromJson(
        Map<String, dynamic>.from(raw as Map),
      ),
    );
    final user = response.data;
    if (user == null) {
      throw StateError('Profil utilisateur vide.');
    }
    return user;
  }

  Future<void> changePassword({
    required String oldPassword,
    required String newPassword,
  }) async {
    await _api.post(
      ApiEndpoints.changePassword,
      data: {
        'old_password': oldPassword,
        'new_password': newPassword,
      },
    );
  }
}
