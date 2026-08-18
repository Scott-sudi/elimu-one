import '../constants/api_endpoints.dart';
import '../core/errors/api_exception.dart';
import '../core/network/api_service.dart';
import '../models/parent_profile.dart';

class ProfileService {
  ProfileService({required ApiService api}) : _api = api;

  final ApiService _api;

  Future<ParentProfile> fetchProfile({required String guardianPublicId}) async {
    if (guardianPublicId.isEmpty) {
      throw const ServerException('Session parent invalide.');
    }
    try {
      final response = await _api.get<ParentProfile>(
        ApiEndpoints.parentProfile,
        queryParameters: {'guardian_public_id': guardianPublicId},
        parser: (raw) => ParentProfile.fromJson(
          Map<String, dynamic>.from(raw as Map),
        ),
      );
      return response.data ??
          ParentProfile(
            guardianPublicId: guardianPublicId,
            displayName: '',
          );
    } on ApiException {
      rethrow;
    } catch (_) {
      throw const NetworkException();
    }
  }
}
