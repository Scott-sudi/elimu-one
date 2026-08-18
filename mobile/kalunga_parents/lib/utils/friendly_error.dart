import '../core/errors/api_exception.dart';

/// Message lisible pour l'utilisateur (jamais "ApiException...").
String friendlyErrorMessage(
  Object? error, {
  String fallback = 'Vérifiez votre connexion.',
}) {
  if (error == null) return fallback;

  if (error is NetworkException) {
    final msg = error.message.trim();
    return msg.isNotEmpty ? msg : fallback;
  }
  if (error is TimeoutException) {
    final msg = error.message.trim();
    return msg.isNotEmpty ? msg : fallback;
  }

  if (error is ApiException) {
    final msg = error.message.trim();
    if (msg.isEmpty) return fallback;
    final lower = msg.toLowerCase();
    if (lower.contains('exception') ||
        lower.contains('traceback') ||
        lower.contains('dio') ||
        lower.contains('socket')) {
      return fallback;
    }
    return msg;
  }

  final raw = error.toString().trim();
  if (raw.isEmpty) return fallback;
  final lower = raw.toLowerCase();
  if (raw.startsWith('Exception: ')) {
    return raw.substring('Exception: '.length);
  }
  if (lower.startsWith('apiexception') ||
      lower.contains('exception:') ||
      (lower.contains('null') && lower.contains('joindre'))) {
    return fallback;
  }
  return raw;
}
