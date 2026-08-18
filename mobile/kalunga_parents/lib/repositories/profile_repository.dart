import '../models/parent_identity.dart';
import '../models/parent_profile.dart';
import '../services/auth_service.dart';
import '../services/profile_service.dart';

class ProfileRepository {
  ProfileRepository({
    required ProfileService profileService,
    required AuthService authService,
  })  : _profile = profileService,
        _auth = authService;

  final ProfileService _profile;
  final AuthService _auth;

  Future<ParentProfile> loadProfile() async {
    final ParentIdentity? session = await _auth.readParentSession();
    final guardianId = session?.guardianPublicId ?? '';
    final fallback = ParentProfile.fromSession(
      guardianPublicId: guardianId,
      displayName: session?.displayName ?? '',
      phone: session?.phone ?? '',
      email: session?.email ?? '',
    );

    if (guardianId.isEmpty) return fallback;

    try {
      return await _profile.fetchProfile(guardianPublicId: guardianId);
    } catch (_) {
      return fallback;
    }
  }
}
