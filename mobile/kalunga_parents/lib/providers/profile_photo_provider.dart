import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'auth_providers.dart';

/// Clé SharedPreferences pour la photo locale du parent (base64).
String _photoKey(String userKey) => 'kalunga_profile_photo_$userKey';

String _sessionUserKey(AuthSessionState session) {
  return switch (session) {
    AuthSessionAuthenticated(:final identity) =>
      identity.guardianPublicId.trim().isNotEmpty
          ? identity.guardianPublicId.trim()
          : (identity.phone.trim().isNotEmpty
              ? identity.phone.trim()
              : 'default'),
    _ => 'default',
  };
}

/// Photo de profil locale (galerie / appareil), indépendante du serveur.
class ProfilePhotoNotifier extends StateNotifier<Uint8List?> {
  ProfilePhotoNotifier(this._userKey) : super(null) {
    _restore();
  }

  final String _userKey;
  final ImagePicker _picker = ImagePicker();

  Future<void> _restore() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_photoKey(_userKey));
    if (raw == null || raw.isEmpty) {
      state = null;
      return;
    }
    try {
      state = base64Decode(raw);
    } catch (_) {
      state = null;
    }
  }

  Future<void> _persist(Uint8List? bytes) async {
    final prefs = await SharedPreferences.getInstance();
    final key = _photoKey(_userKey);
    if (bytes == null || bytes.isEmpty) {
      await prefs.remove(key);
      state = null;
      return;
    }
    await prefs.setString(key, base64Encode(bytes));
    state = bytes;
  }

  Future<bool> pickFromGallery() => _pick(ImageSource.gallery);

  Future<bool> pickFromCamera() => _pick(ImageSource.camera);

  Future<bool> _pick(ImageSource source) async {
    try {
      final file = await _picker.pickImage(
        source: source,
        maxWidth: 720,
        maxHeight: 720,
        imageQuality: 85,
      );
      if (file == null) return false;
      final bytes = await file.readAsBytes();
      if (bytes.isEmpty) return false;
      await _persist(bytes);
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<void> clear() => _persist(null);
}

final profilePhotoProvider =
    StateNotifierProvider<ProfilePhotoNotifier, Uint8List?>((ref) {
  final session = ref.watch(authSessionProvider);
  return ProfilePhotoNotifier(_sessionUserKey(session));
});
