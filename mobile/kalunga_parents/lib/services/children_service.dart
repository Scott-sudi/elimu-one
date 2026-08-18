import '../constants/api_endpoints.dart';
import '../core/errors/api_exception.dart';
import '../core/network/api_service.dart';
import '../models/child_models.dart';

/// Service « Mes Enfants » — consomme l'API Django parents.
class ChildrenService {
  ChildrenService({
    required ApiService api,
    this.useMockData = false,
  }) : _api = api;

  final ApiService _api;

  /// Mettre à `true` uniquement pour UI hors-ligne.
  final bool useMockData;

  Future<List<ChildSummary>> fetchChildren({
    required String guardianPublicId,
  }) async {
    if (useMockData) return _mockChildren();

    if (guardianPublicId.isEmpty) {
      return const [];
    }

    try {
      final response = await _api.get<List<ChildSummary>>(
        ApiEndpoints.children,
        queryParameters: {'guardian_public_id': guardianPublicId},
        parser: (raw) {
          final map = Map<String, dynamic>.from(raw as Map);
          final list = map['enfants'] as List<dynamic>? ?? const [];
          return list
              .map(
                (e) => ChildSummary.fromJson(
                  Map<String, dynamic>.from(e as Map),
                ),
              )
              .toList();
        },
      );
      return response.data ?? const [];
    } on ApiException {
      rethrow;
    } catch (_) {
      throw const NetworkException();
    }
  }

  List<ChildSummary> _mockChildren() {
    return const [
      ChildSummary(
        id: '1',
        displayName: 'Jean KALUNGA',
        classLabel: '4ème Scientifique',
        matricule: '2025/00125',
        isActive: true,
      ),
      ChildSummary(
        id: '2',
        displayName: 'Grâce KALUNGA',
        classLabel: '2ème Commerciale',
        matricule: '2025/00358',
        isActive: true,
      ),
      ChildSummary(
        id: '3',
        displayName: 'Emmanuel KALUNGA',
        classLabel: '6ème Primaire',
        matricule: '2025/01045',
        isActive: true,
      ),
      ChildSummary(
        id: '4',
        displayName: 'David KALUNGA',
        classLabel: '3ème Secondaire',
        matricule: '2024/00987',
        isActive: false,
      ),
    ];
  }
}
