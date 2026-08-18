import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'constants/app_constants.dart';
import 'core/storage/secure_storage_service.dart';
import 'core/theme/app_theme.dart';
import 'firebase_options.dart';
import 'providers/dependency_providers.dart';
import 'providers/settings_providers.dart';
import 'screens/auth/auth_gate.dart';
import 'services/push_notification_service.dart';
import 'widgets/startup_permissions_gate.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // FCM app fermée / tuée : le handler DOIT être enregistré avant runApp.
  if (!kIsWeb) {
    try {
      await Firebase.initializeApp(
        options: DefaultFirebaseOptions.currentPlatform,
      );
      FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);
    } catch (e, st) {
      debugPrint('Firebase init (main): $e\n$st');
    }
  }

  // Sur web, évite le blocage de flutter_secure_storage au démarrage.
  final storage = await SecureStorageService.create();

  runApp(
    ProviderScope(
      overrides: [
        secureStorageProvider.overrideWithValue(storage),
      ],
      child: const KalungaParentsApp(),
    ),
  );
}

/// Application mobile parents — ELIMU Go.
class KalungaParentsApp extends ConsumerWidget {
  const KalungaParentsApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final themeMode = ref.watch(themeModeProvider);
    final language = ref.watch(appLanguageProvider);

    return MaterialApp(
      title: AppConstants.appName,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: themeMode,
      locale: language.materialLocale,
      supportedLocales: const [
        Locale('fr'),
        Locale('en'),
      ],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      home: const StartupPermissionsGate(
        child: AuthGate(),
      ),
    );
  }
}
