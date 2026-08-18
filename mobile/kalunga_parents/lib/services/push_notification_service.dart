import 'dart:async';
import 'dart:convert';

import 'package:audioplayers/audioplayers.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../constants/api_endpoints.dart';
import '../core/network/api_service.dart';
import '../firebase_options.dart';
import '../models/home_models.dart';
import '../models/notification_models.dart';
import '../providers/auth_providers.dart';
import '../providers/dependency_providers.dart';
import '../providers/home_providers.dart';
import '../providers/notifications_providers.dart';

/// Canal Android — doit matcher MainActivity.kt / KalungaParentsApplication.
const kParentsAlertChannelId = 'elimu_go_alerts_v2';
const kParentsAlertChannelName = 'Alertes ELIMU Go';
const _kNativeAlertsChannel = 'net.institutkalunga.parents/alerts';

class InAppAlert {
  const InAppAlert({required this.title, required this.body});
  final String title;
  final String body;
}

final inAppAlertProvider = StateProvider<InAppAlert?>((ref) => null);

/// Notification à ouvrir après un toucher sur une alerte FCM.
final pendingPushNotificationProvider =
    StateProvider<ParentNotificationItem?>((ref) => null);

/// Anti-doublon FCM + polling (même alerte en < 90 s).
final Map<String, DateTime> _recentAlertKeys = {};

ActivityType _activityTypeForSource(String source) {
  if (source == 'finance_payment') return ActivityType.fees;
  if (source == 'discipline_summons') return ActivityType.meeting;
  if (source == 'secretariat_communication') return ActivityType.bulletin;
  if (source == 'discipline_attendance') return ActivityType.info;
  if (source == 'student_linked' ||
      source == 'student_removed' ||
      source == 'secretariat_enrollment' ||
      source == 'secretariat_student') {
    return ActivityType.info;
  }
  if (source == 'discipline_incident' ||
      source == 'discipline_measure' ||
      source == 'discipline_exit' ||
      source == 'discipline_justification') {
    return ActivityType.info;
  }
  return ActivityType.info;
}

ParentNotificationItem? _notificationItemFromData(
  Map<String, dynamic> data, {
  String? notificationTitle,
  String? notificationBody,
  DateTime? occurredAt,
}) {
  final source = (data['type'] ?? data['source'])?.toString().trim() ?? '';
  final sourceId = data['source_id']?.toString().trim() ?? '';
  if (source.isEmpty || sourceId.isEmpty) return null;

  final title =
      notificationTitle ?? data['title']?.toString() ?? 'ELIMU Go';
  final body = notificationBody ?? data['body']?.toString() ?? '';
  return ParentNotificationItem(
    id: '$source:$sourceId',
    title: title,
    subtitle: data['subtitle']?.toString() ?? body,
    timestampLabel: '',
    type: _activityTypeForSource(source),
    body: body,
    isRead: false,
    studentId: data['student_id']?.toString() ?? '',
    studentName: data['student_name']?.toString() ?? '',
    source: source,
    sourceId: sourceId,
    occurredAt: occurredAt ?? DateTime.now(),
  );
}

ParentNotificationItem? _notificationItemFromMessage(RemoteMessage message) {
  return _notificationItemFromData(
    message.data,
    notificationTitle: message.notification?.title,
    notificationBody: message.notification?.body,
    occurredAt: message.sentTime?.toLocal(),
  );
}

String _notificationPayload(ParentNotificationItem item) {
  return jsonEncode({
    'source': item.source,
    'source_id': item.resolvedSourceId,
    'student_id': item.studentId,
    'student_name': item.studentName,
    'title': item.title,
    'body': item.body,
    'subtitle': item.subtitle,
    'occurred_at': item.occurredAt?.toIso8601String(),
  });
}

bool _claimAlertKey(String key) {
  final now = DateTime.now();
  _recentAlertKeys.removeWhere(
    (_, at) => now.difference(at) > const Duration(seconds: 90),
  );
  if (key.isEmpty) return true;
  if (_recentAlertKeys.containsKey(key)) return false;
  _recentAlertKeys[key] = now;
  return true;
}

@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // App tuée / arrière-plan : si FCM n’a envoyé que `data`, Android n’affiche
  // rien tout seul — on publie une notif locale (icône EL).
  try {
    if (Firebase.apps.isEmpty) {
      await Firebase.initializeApp(
        options: DefaultFirebaseOptions.currentPlatform,
      );
    }
  } catch (_) {}

  if (message.notification != null) return;

  final title = message.data['title']?.toString() ?? 'ELIMU Go';
  final body = message.data['body']?.toString() ??
      'Vous avez une nouvelle notification.';
  try {
    final plugin = FlutterLocalNotificationsPlugin();
    const androidInit =
        AndroidInitializationSettings('@drawable/ic_stat_notify');
    await plugin.initialize(
      const InitializationSettings(android: androidInit),
    );
    await plugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(
      const AndroidNotificationChannel(
        kParentsAlertChannelId,
        kParentsAlertChannelName,
        importance: Importance.max,
        playSound: true,
        enableVibration: true,
        showBadge: true,
      ),
    );
    await plugin.show(
      DateTime.now().millisecondsSinceEpoch.remainder(100000),
      title,
      body,
      const NotificationDetails(
        android: AndroidNotificationDetails(
          kParentsAlertChannelId,
          kParentsAlertChannelName,
          importance: Importance.max,
          priority: Priority.max,
          icon: '@drawable/ic_stat_notify',
          color: Color(0xFF002858),
          largeIcon: DrawableResourceAndroidBitmap('@mipmap/ic_launcher'),
        ),
      ),
    );
  } catch (_) {}
}

/// Publie de VRAIES notifications système Android (son + bannière).
class PushNotificationService {
  PushNotificationService({
    required ApiService api,
    required this.onNotificationTap,
  }) : _api = api;

  final ApiService _api;
  final void Function(ParentNotificationItem item) onNotificationTap;
  final FlutterLocalNotificationsPlugin _local =
      FlutterLocalNotificationsPlugin();
  final AudioPlayer _player = AudioPlayer();

  bool _ready = false;
  bool _fcmReady = false;
  bool _audioConfigured = false;
  StreamSubscription<RemoteMessage>? _foregroundMessageSubscription;
  StreamSubscription<String>? _tokenRefreshSubscription;
  String _tokenGuardianId = '';

  Future<void> init() async {
    if (_ready || kIsWeb) return;

    const androidInit =
        AndroidInitializationSettings('@drawable/ic_stat_notify');
    const iosInit = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestSoundPermission: true,
      requestBadgePermission: true,
    );
    await _local.initialize(
      settings:
          const InitializationSettings(android: androidInit, iOS: iosInit),
      onDidReceiveNotificationResponse: _handleLocalNotificationResponse,
    );

    final vibration = Int64List.fromList([0, 500, 200, 500, 200, 500]);

    final androidPlugin = _local.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    await androidPlugin?.createNotificationChannel(
      AndroidNotificationChannel(
        kParentsAlertChannelId,
        kParentsAlertChannelName,
        description: 'Messages école, présences, finances — avec son',
        importance: Importance.max,
        playSound: true,
        enableVibration: true,
        vibrationPattern: vibration,
        showBadge: true,
        enableLights: true,
        audioAttributesUsage: AudioAttributesUsage.notificationRingtone,
      ),
    );
    await androidPlugin?.requestNotificationsPermission();

    final iosPlugin = _local.resolvePlatformSpecificImplementation<
        IOSFlutterLocalNotificationsPlugin>();
    await iosPlugin?.requestPermissions(alert: true, badge: true, sound: true);

    if (defaultTargetPlatform == TargetPlatform.android) {
      try {
        const channel = MethodChannel(_kNativeAlertsChannel);
        await channel.invokeMethod<void>('ensureChannel');
      } catch (_) {}
    }

    await _configureAudio();
    _ready = true;
    await _initFirebaseMessaging();
  }

  Future<void> _configureAudio() async {
    if (_audioConfigured) return;
    try {
      if (defaultTargetPlatform == TargetPlatform.android) {
        await AudioPlayer.global.setAudioContext(
          AudioContext(
            android: const AudioContextAndroid(
              isSpeakerphoneOn: true,
              stayAwake: true,
              contentType: AndroidContentType.sonification,
              usageType: AndroidUsageType.notificationRingtone,
              audioFocus: AndroidAudioFocus.gainTransientMayDuck,
            ),
          ),
        );
      }
      await _player.setReleaseMode(ReleaseMode.stop);
      await _player.setVolume(1.0);
      _audioConfigured = true;
    } catch (_) {}
  }

  Future<void> _initFirebaseMessaging() async {
    if (kIsWeb || _fcmReady) return;
    try {
      if (Firebase.apps.isEmpty) {
        await Firebase.initializeApp(
          options: DefaultFirebaseOptions.currentPlatform,
        );
      }
    } catch (e, st) {
      debugPrint('Firebase.initializeApp failed: $e\n$st');
      return;
    }

    final messaging = FirebaseMessaging.instance;
    await messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
    );

    await messaging.setForegroundNotificationPresentationOptions(
      alert: true,
      badge: true,
      sound: true,
    );

    // Android 13+ : sans cette permission, FCM n’affiche rien app fermée.
    if (defaultTargetPlatform == TargetPlatform.android) {
      await Permission.notification.request();
    }

    await _foregroundMessageSubscription?.cancel();
    _foregroundMessageSubscription =
        FirebaseMessaging.onMessage.listen((RemoteMessage message) async {
      final title = message.notification?.title ??
          message.data['title']?.toString() ??
          'ELIMU Go';
      final body = message.notification?.body ??
          message.data['body']?.toString() ??
          'Vous avez une nouvelle notification.';
      final dedupe = message.data['source_id']?.toString() ??
          '$title|$body|${message.messageId ?? ''}';
      // En foreground FCM affiche rarement la notif système → on la publie.
      await showLocalAlert(
        title: title,
        body: body,
        dedupeKey: dedupe,
        showInAppBanner: false,
        notificationItem: _notificationItemFromMessage(message),
      );
    });

    _fcmReady = true;
  }

  Future<void> _playAlertTone() async {
    await _configureAudio();
    try {
      await _player.stop();
      await _player.play(AssetSource('sounds/kalunga_alert.wav'), volume: 1.0);
    } catch (_) {}
    try {
      await HapticFeedback.heavyImpact();
      await SystemSound.play(SystemSoundType.alert);
    } catch (_) {}
  }

  Future<void> _postSystemNotification({
    required String title,
    required String body,
    String? icon,
    ParentNotificationItem? notificationItem,
  }) async {
    final vibration = Int64List.fromList([0, 500, 200, 500, 200, 500]);
    final androidDetails = AndroidNotificationDetails(
      kParentsAlertChannelId,
      kParentsAlertChannelName,
      channelDescription: 'Messages école, présences, finances — avec son',
      importance: Importance.max,
      priority: Priority.max,
      playSound: true,
      enableVibration: true,
      vibrationPattern: vibration,
      category: AndroidNotificationCategory.message,
      visibility: NotificationVisibility.public,
      ticker: 'Alerte ELIMU Go',
      styleInformation: BigTextStyleInformation(body, contentTitle: title),
      audioAttributesUsage: AudioAttributesUsage.notificationRingtone,
      icon: icon ?? '@drawable/ic_stat_notify',
      largeIcon: const DrawableResourceAndroidBitmap('@mipmap/ic_launcher'),
      color: const Color(0xFF002858),
      channelShowBadge: true,
      onlyAlertOnce: false,
      silent: false,
    );
    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentSound: true,
      presentBadge: true,
      interruptionLevel: InterruptionLevel.timeSensitive,
    );

    await _local.show(
      id: DateTime.now().millisecondsSinceEpoch.remainder(100000),
      title: title,
      body: body,
      notificationDetails: NotificationDetails(
        android: androidDetails,
        iOS: iosDetails,
      ),
      payload: notificationItem == null
          ? null
          : _notificationPayload(notificationItem),
    );
  }

  void _handleLocalNotificationResponse(NotificationResponse response) {
    final payload = response.payload?.trim() ?? '';
    if (payload.isEmpty) return;
    try {
      final raw = jsonDecode(payload);
      if (raw is! Map) return;
      final data = Map<String, dynamic>.from(raw);
      final occurredAt = DateTime.tryParse(
        data['occurred_at']?.toString() ?? '',
      )?.toLocal();
      final item = _notificationItemFromData(
        data,
        notificationTitle: data['title']?.toString(),
        notificationBody: data['body']?.toString(),
        occurredAt: occurredAt,
      );
      if (item != null) onNotificationTap(item);
    } catch (_) {}
  }

  /// Une seule notification système (style WhatsApp).
  Future<bool> showLocalAlert({
    required String title,
    required String body,
    void Function(InAppAlert alert)? onInApp,
    String? dedupeKey,
    bool showInAppBanner = false,
    ParentNotificationItem? notificationItem,
  }) async {
    if (kIsWeb) return false;
    if (!_ready) await init();

    final key = (dedupeKey ?? '$title|$body').trim();
    if (!_claimAlertKey(key)) return false;

    if (showInAppBanner) {
      final alert = InAppAlert(title: title, body: body);
      onInApp?.call(alert);
    }

    if (defaultTargetPlatform == TargetPlatform.android &&
        notificationItem == null) {
      try {
        await Permission.notification.request();
        const channel = MethodChannel(_kNativeAlertsChannel);
        await channel.invokeMethod<void>('ensureChannel');
        final posted = await channel.invokeMethod<bool>('showAlert', {
          'title': title,
          'body': body,
        });
        if (posted == true) return true;
      } catch (_) {}
    }

    await _playAlertTone();
    try {
      await _postSystemNotification(
        title: title,
        body: body,
        notificationItem: notificationItem,
      );
      return true;
    } catch (_) {
      try {
        await _postSystemNotification(
          title: title,
          body: body,
          icon: '@mipmap/ic_launcher',
          notificationItem: notificationItem,
        );
        return true;
      } catch (_) {
        return false;
      }
    }
  }

  Future<bool> areSystemNotificationsEnabled() async {
    if (kIsWeb) return false;
    if (defaultTargetPlatform != TargetPlatform.android) return true;
    try {
      const channel = MethodChannel(_kNativeAlertsChannel);
      return await channel.invokeMethod<bool>('areNotificationsEnabled') ??
          false;
    } catch (_) {
      return false;
    }
  }

  Future<void> syncDeviceToken(String guardianPublicId) async {
    if (kIsWeb || guardianPublicId.isEmpty) return;
    if (!_ready) await init();
    if (!_fcmReady) {
      await _initFirebaseMessaging();
    }
    if (!_fcmReady) {
      debugPrint('FCM sync skipped: Firebase not ready');
      return;
    }

    try {
      // Laisse le temps au Play Services / FCM de fournir un jeton.
      String? token;
      for (var attempt = 0; attempt < 5; attempt++) {
        token = await FirebaseMessaging.instance.getToken();
        if (token != null && token.isNotEmpty) break;
        await Future<void>.delayed(Duration(milliseconds: 400 * (attempt + 1)));
      }
      if (token == null || token.isEmpty) {
        debugPrint('FCM getToken: vide après retries');
        return;
      }
      debugPrint('FCM token …${token.substring(token.length - 8)}');
      await registerDeviceToken(
        guardianPublicId: guardianPublicId,
        token: token,
      );

      if (_tokenGuardianId != guardianPublicId ||
          _tokenRefreshSubscription == null) {
        await _tokenRefreshSubscription?.cancel();
        _tokenGuardianId = guardianPublicId;
        _tokenRefreshSubscription =
            FirebaseMessaging.instance.onTokenRefresh.listen((newToken) {
          registerDeviceToken(
            guardianPublicId: guardianPublicId,
            token: newToken,
          );
        });
      }
    } catch (e, st) {
      debugPrint('FCM syncDeviceToken failed: $e\n$st');
    }
  }

  Future<void> clearGuardian() async {
    _tokenGuardianId = '';
    await _tokenRefreshSubscription?.cancel();
    _tokenRefreshSubscription = null;
  }

  Future<void> dispose() async {
    await clearGuardian();
    await _foregroundMessageSubscription?.cancel();
    _foregroundMessageSubscription = null;
    await _player.dispose();
  }

  Future<void> registerDeviceToken({
    required String guardianPublicId,
    required String token,
    String? platform,
  }) async {
    if (guardianPublicId.isEmpty || token.isEmpty) return;
    final plat = platform ??
        (defaultTargetPlatform == TargetPlatform.iOS ? 'ios' : 'android');
    try {
      await _api.post<Map<String, dynamic>>(
        ApiEndpoints.parentDeviceRegister,
        data: {
          'guardian_public_id': guardianPublicId,
          'token': token,
          'platform': plat,
        },
        parser: (raw) => Map<String, dynamic>.from(raw as Map? ?? const {}),
      );
      debugPrint('FCM device registered for $guardianPublicId');
    } catch (e, st) {
      debugPrint('FCM registerDeviceToken failed: $e\n$st');
    }
  }
}

final pushNotificationServiceProvider =
    Provider<PushNotificationService>((ref) {
  final service = PushNotificationService(
    api: ref.watch(apiServiceProvider),
    onNotificationTap: (item) {
      ref.read(bottomNavIndexProvider.notifier).state = 2;
      ref.read(pendingPushNotificationProvider.notifier).state = item;
    },
  );
  ref.onDispose(service.dispose);
  return service;
});

final pushBootstrapProvider = Provider<void>((ref) {
  void openFromMessage(RemoteMessage message) {
    ref.invalidate(homeDashboardProvider);
    ref.invalidate(parentNotificationsProvider);
    final item = _notificationItemFromMessage(message);
    if (item != null) {
      ref.read(bottomNavIndexProvider.notifier).state = 2;
      ref.read(pendingPushNotificationProvider.notifier).state = item;
    }
  }

  StreamSubscription<RemoteMessage>? openedSubscription;
  if (!kIsWeb) {
    openedSubscription =
        FirebaseMessaging.onMessageOpenedApp.listen(openFromMessage);
  }
  ref.onDispose(() => openedSubscription?.cancel());

  var initialMessageHandled = false;
  ref.listen<AuthSessionState>(
    authSessionProvider,
    (prev, next) async {
      if (kIsWeb) return;
      final push = ref.read(pushNotificationServiceProvider);
      if (next is! AuthSessionAuthenticated) {
        await push.clearGuardian();
        return;
      }
      await push.init();
      await push.syncDeviceToken(next.identity.guardianPublicId);

      if (!initialMessageHandled) {
        initialMessageHandled = true;
        try {
          final initial = await FirebaseMessaging.instance.getInitialMessage();
          if (initial != null) {
            openFromMessage(initial);
          }
        } catch (_) {}
      }
    },
    fireImmediately: true,
  );
});
