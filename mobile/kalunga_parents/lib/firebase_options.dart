// Généré à partir de android/app/google-services.json (projet elimu-go).
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
    apiKey: 'AIzaSyClv5QrIONW0CWjgvdT_jWZGGVOpPrSdE0',
    appId: '1:49648016490:android:409f0bbc545e51c394fe13',
    messagingSenderId: '49648016490',
    projectId: 'elimu-go',
    storageBucket: 'elimu-go.firebasestorage.app',
  );
}
