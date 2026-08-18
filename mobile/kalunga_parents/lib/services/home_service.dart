import '../constants/api_endpoints.dart';
import '../core/errors/api_exception.dart';
import '../core/network/api_service.dart';
import '../models/home_models.dart';
import '../utils/notification_sort.dart';

/// Données Accueil parents (API Django).
class HomeService {
  HomeService({
    required ApiService api,
    this.useMockData = false,
  }) : _api = api;

  final ApiService _api;

  /// Mettre à `true` uniquement pour UI hors-ligne / démo.
  final bool useMockData;

  Future<HomeDashboard> fetchDashboard({
    required String guardianPublicId,
  }) async {
    if (useMockData) {
      return _mockDashboard();
    }

    if (guardianPublicId.isEmpty) {
      throw const ServerException('Session parent invalide.');
    }

    try {
      final response = await _api.get<HomeDashboard>(
        ApiEndpoints.parentHomeOverview,
        queryParameters: {'guardian_public_id': guardianPublicId},
        parser: (raw) {
          final map = Map<String, dynamic>.from(raw as Map);
          final overview = HomeOverview.fromJson(map);
          final activitiesRaw = map['activities'] as List<dynamic>? ?? const [];
          final activities = activitiesRaw
              .map(
                (e) => RecentActivity.fromJson(
                  Map<String, dynamic>.from(e as Map),
                ),
              )
              .toList();
          sortRecentActivitiesNewestFirst(activities);
          return HomeDashboard(
            parentDisplayName: map['display_name']?.toString() ?? '',
            overview: overview,
            activities: activities,
          );
        },
      );
      return response.data ??
          const HomeDashboard(
            parentDisplayName: '',
            overview: HomeOverview(
              schoolYearLabel: '',
              childrenCount: 0,
              notificationsCount: 0,
              paidBalanceLabel: 'Aucun',
              unpaidBalanceLabel: 'Aucun',
            ),
            activities: [],
          );
    } on ApiException {
      rethrow;
    } catch (_) {
      throw const NetworkException();
    }
  }

  /// Jeu de données aligné sur la maquette Accueil (hors-ligne).
  HomeDashboard _mockDashboard() {
    return const HomeDashboard(
      parentDisplayName: 'Jean KABASELE',
      overview: HomeOverview(
        schoolYearLabel: 'Année scolaire 2025-2026',
        childrenCount: 2,
        notificationsCount: 5,
        paidBalanceLabel: '450 000 CDF',
        unpaidBalanceLabel: 'Aucun',
        unreadNotificationsBadge: 3,
      ),
      activities: [
        RecentActivity(
          id: '1',
          title: 'Nouveau bulletin disponible',
          subtitle: 'Jean Kalunga - 4ème Chimie',
          timestampLabel: "Aujourd'hui, 08:30",
          type: ActivityType.bulletin,
        ),
        RecentActivity(
          id: '2',
          title: 'Réunion Parents-Professeurs',
          subtitle: 'Samedi 14 Juin 2025 à 09:00',
          timestampLabel: 'Hier, 16:45',
          type: ActivityType.meeting,
        ),
        RecentActivity(
          id: '3',
          title: 'Frais scolaires',
          subtitle: 'Paiement du 2ème trimestre',
          timestampLabel: '10 Juin 2025',
          type: ActivityType.fees,
        ),
      ],
    );
  }
}
