import 'package:flutter/foundation.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _kPermissionsPromptedKey = 'kalunga_permissions_prompted_v1';

/// Demande les autorisations système (notifications, caméra, photos/fichiers).
abstract final class AppPermissionsService {
  /// `true` si la boîte système a déjà été proposée une fois.
  static Future<bool> wasPrompted() async {
    if (kIsWeb) return true;
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_kPermissionsPromptedKey) ?? false;
  }

  static Future<void> markPrompted() async {
    if (kIsWeb) return;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kPermissionsPromptedKey, true);
  }

  /// Enchaîne les demandes Android / iOS (une boîte après l’autre).
  static Future<void> requestStartupPermissions() async {
    if (kIsWeb) return;

    try {
      await Permission.notification.request();
    } catch (_) {}

    try {
      await Permission.camera.request();
    } catch (_) {}

    // Photos / galerie (Android 13+ & iOS).
    try {
      await Permission.photos.request();
    } catch (_) {}

    // Fichiers / stockage (Android ≤ 12).
    try {
      if (defaultTargetPlatform == TargetPlatform.android) {
        await Permission.storage.request();
      }
    } catch (_) {}

    await markPrompted();
  }
}
