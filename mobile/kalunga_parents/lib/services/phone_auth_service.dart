import '../constants/api_endpoints.dart';
import '../core/errors/api_exception.dart';
import '../core/network/api_service.dart';
import '../models/parent_identity.dart';

/// Vérification téléphone + n° d'identification (`POST parents/auth/verify-phone/`).
class PhoneAuthService {
  PhoneAuthService({required ApiService api}) : _api = api;

  final ApiService _api;

  static const _defaultFailure =
      "Identifiants incorrects. Vérifiez le téléphone et le numéro "
      "d'identification, puis réessayez.";

  Future<PhoneVerificationResult> verifyCredentials({
    required String telephone,
    required String numeroIdentification,
  }) async {
    try {
      // GET : Tiger Protect o2switch bloque actuellement les POST API hors navigateur.
      // La comparaison reste 100 % côté Django / base (telephone + numero_identification).
      final response = await _api.get<Map<String, dynamic>>(
        ApiEndpoints.parentVerifyPhone,
        queryParameters: {
          'telephone': telephone.trim(),
          'numero_identification': numeroIdentification.trim(),
        },
        skipAuth: true,
        parser: (raw) => Map<String, dynamic>.from(raw as Map),
      );

      final data = response.data ?? const <String, dynamic>{};
      final recognized = data['recognized'] == true;

      if (!recognized) {
        final message = response.message.trim().isNotEmpty
            ? response.message
            : _defaultFailure;
        return PhoneVerificationResult.unknown(message: message);
      }

      final identity = ParentIdentity.fromVerifyJson(
        data,
        phone: telephone.trim(),
      );
      if (identity.guardianPublicId.isEmpty) {
        return const PhoneVerificationResult.unknown(message: _defaultFailure);
      }
      return PhoneVerificationResult.recognized(identity);
    } on UnauthorizedException {
      return const PhoneVerificationResult.unknown(message: _defaultFailure);
    } on ApiException catch (e) {
      final msg = e.message.trim();
      if (e.statusCode == 400) {
        throw PhoneValidationException(
          msg.isNotEmpty ? msg : 'Identifiants invalides.',
        );
      }
      if (e.statusCode == 405) {
        throw const PhoneNetworkException(
          "L'API de connexion n'est pas à jour sur le serveur. "
          "Collez le script de déploiement o2switch (parents_auth), puis réessayez.",
        );
      }
      if (msg.isNotEmpty && (e.statusCode == 503 || e.statusCode == 502)) {
        throw PhoneNetworkException(msg);
      }
      throw const PhoneNetworkException();
    } catch (e) {
      if (e is PhoneValidationException || e is PhoneNetworkException) {
        rethrow;
      }
      throw const PhoneNetworkException();
    }
  }
}

/// Erreurs contrôlées pour l'UI (textes fixes, jamais techniques).
class PhoneValidationException implements Exception {
  const PhoneValidationException([
    this.message = 'Identifiants invalides.',
  ]);

  final String message;
}

class PhoneNetworkException implements Exception {
  const PhoneNetworkException([
    this.message =
        'Impossible de vérifier vos identifiants. Vérifiez votre connexion et réessayez.',
  ]);

  final String message;
}
