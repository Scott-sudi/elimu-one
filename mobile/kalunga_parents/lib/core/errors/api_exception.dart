/// Exceptions réseau / métier remontées depuis [ApiService].
sealed class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode, this.errors});

  final String message;
  final int? statusCode;
  final Map<String, dynamic>? errors;

  /// Message utilisateur uniquement (jamais "ApiException(null): ...").
  @override
  String toString() => message;
}

class NetworkException extends ApiException {
  const NetworkException([
    super.message = 'Vérifiez votre connexion.',
  ]);
}

class TimeoutException extends ApiException {
  const TimeoutException([
    super.message = 'Le serveur met trop de temps à répondre. Réessayez.',
  ]);
}

class UnauthorizedException extends ApiException {
  const UnauthorizedException([
    String message = 'Session expirée. Veuillez vous reconnecter.',
  ]) : super(message, statusCode: 401);
}

class ServerException extends ApiException {
  const ServerException(
    super.message, {
    super.statusCode,
    super.errors,
  });
}

class ParsingException extends ApiException {
  const ParsingException([
    super.message = 'Réponse serveur invalide.',
  ]);
}
