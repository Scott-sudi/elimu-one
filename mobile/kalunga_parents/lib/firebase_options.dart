// Généré à partir de android/app/google-services.json (projet institut-kalunga).
import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, kIsWeb, TargetPlatform;

class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) {
      throw UnsupportedError('Firebase web non configuré pour cette app.');
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      case TargetPlatform.iOS:
        throw UnsupportedError('Firebase iOS non configuré pour cette app.');
      default:
        throw UnsupportedError(
          'Firebase non supporté sur ${defaultTargetPlatform.name}.',
        );
    }
  }

  static const FirebaseOptions android = FirebaseOptions(
    apiKey: 'AIzaSyDhlCbF8dxBYI59CsdM8kno2flvuRqNzoY',
    appId: '1:897069046002:android:783f48e8ef7405e7a3986b',
    messagingSenderId: '897069046002',
    projectId: 'institut-kalunga',
    storageBucket: 'institut-kalunga.firebasestorage.app',
  );
}
