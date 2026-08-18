import '../models/home_models.dart';
import '../models/parent_identity.dart';
import '../services/auth_service.dart';
import '../services/home_service.dart';

/// Repository Accueil : charge le tableau de bord live et rafraîchit le nom.
class HomeRepository {
  HomeRepository({
    required HomeService homeService,
    required AuthService authService,
  })  : _home = homeService,
        _auth = authService;

  final HomeService _home;
  final AuthService _auth;

  /// Charge Accueil depuis Django et met à jour le nom en session locale.
  Future<HomeDashboard> loadDashboard() async {
    final parent = await _auth.readParentSession();
    final guardianId = parent?.guardianPublicId ?? '';

    final dashboard = await _home.fetchDashboard(
      guardianPublicId: guardianId,
    );

    final liveName = dashboard.parentDisplayName.trim();
    if (parent != null &&
        liveName.isNotEmpty &&
        liveName != parent.displayName) {
      await _auth.persistPhoneVerifiedSession(
        parent.copyWith(displayName: liveName),
      );
    }

    if (liveName.isNotEmpty) {
      return dashboard;
    }

    if (parent != null && parent.displayName.trim().isNotEmpty) {
      return HomeDashboard(
        parentDisplayName: parent.displayName,
        overview: dashboard.overview,
        activities: dashboard.activities,
      );
    }

    return dashboard;
  }
}
