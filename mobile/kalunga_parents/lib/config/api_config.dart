/// Configuration centralisée des URLs API Django (ELIMU Go).
///
/// Build release : passer l'hôte prod via `--dart-define=ELIMU_API_HOST=https://votre-domaine`
/// Voir `scripts/build_apk.ps1` et `.github/workflows/build-apk.yml`.
library;

import 'package:flutter/foundation.dart';

/// Environnement d'exécution de l'API.
enum ApiEnvironment {
  /// Domaine HTTPS de ELIMU One (o2switch).
  production,

  /// Émulateur / appareil local → Django `runserver` sur la machine de dev.
  local,

  /// URL o2switch temporaire (*.odns.fr) pendant propagation DNS.
  staging,
}

/// Point d'entrée unique pour l'API REST ELIMU One.
abstract final class ApiConfig {
  /// Environnement actif (release CI : production).
  static const ApiEnvironment environment = ApiEnvironment.production;

  /// Hôte production — surchargeable à la compilation.
  /// Ex. `flutter build apk --dart-define=ELIMU_API_HOST=https://app.elimu.cd`
  static const String productionHost = String.fromEnvironment(
    'ELIMU_API_HOST',
    defaultValue: 'https://REMPLACER-PAR-VOTRE-DOMAINE-ELIMU',
  );

  /// Django local (Android émulateur : 10.0.2.2 = localhost PC).
  static const String localHost = 'http://10.0.2.2:8000';

  /// Hôte staging o2switch — surchargeable à la compilation.
  static const String stagingHost = String.fromEnvironment(
    'ELIMU_STAGING_HOST',
    defaultValue: 'http://REMPLACER.odns.fr',
  );

  /// Proxy local anti-CORS pour Flutter Web (`tool/dev_cors_proxy.py`).
  static const String webDevProxyHost = 'http://127.0.0.1:8788';

  /// Préfixe versionné de l'API Django.
  static const String apiPrefix = '/api/v1';

  /// Hôte selon l'environnement (sans slash final).
  static String get host {
    switch (environment) {
      case ApiEnvironment.production:
        return productionHost;
      case ApiEnvironment.local:
        if (kIsWeb) return webDevProxyHost;
        return localHost;
      case ApiEnvironment.staging:
        if (kIsWeb) return webDevProxyHost;
        return stagingHost;
    }
  }

  /// Base URL complète de l'API (ex. `https://…/api/v1`).
  static String get baseUrl => '$host$apiPrefix';

  /// Réécrit les URLs média pour Flutter Web (CORS via proxy local).
  static String? resolveMediaUrl(String? url) {
    if (url == null || url.trim().isEmpty) return null;
    if (!kIsWeb || environment == ApiEnvironment.production) {
      return url;
    }
    final uri = Uri.tryParse(url);
    if (uri == null || !uri.hasScheme) return url;
    final host = uri.host.toLowerCase();
    final known = {
      Uri.parse(productionHost).host.toLowerCase(),
      Uri.parse(stagingHost).host.toLowerCase(),
    };
    if (!known.contains(host) && !host.contains('odns.fr')) return url;
    return Uri(
      scheme: 'http',
      host: '127.0.0.1',
      port: 8788,
      path: uri.path,
      query: uri.hasQuery ? uri.query : null,
    ).toString();
  }

  /// Timeouts réseau (secondes).
  static const Duration connectTimeout = Duration(seconds: 20);
  static const Duration receiveTimeout = Duration(seconds: 30);
  static const Duration sendTimeout = Duration(seconds: 30);

  /// En-têtes HTTP communs.
  static const Map<String, String> defaultHeaders = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
  };
}
