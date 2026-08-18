import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/push_notification_service.dart';
import 'auth_providers.dart';
import 'home_providers.dart';
import 'notifications_providers.dart';

const _liveRefreshInterval = Duration(seconds: 8);

/// Garde Accueil + Notifications à jour et déclenche **une** alerte système.
class LiveRefreshController extends StateNotifier<int>
    with WidgetsBindingObserver {
  LiveRefreshController(this._ref) : super(0) {
    WidgetsBinding.instance.addObserver(this);
    _syncWithAuth(_ref.read(authSessionProvider));
    _authSub = _ref.listen<AuthSessionState>(authSessionProvider, (_, next) {
      _syncWithAuth(next);
    });
  }

  final Ref _ref;
  Timer? _timer;
  ProviderSubscription<AuthSessionState>? _authSub;
  Set<String>? _knownIds;
  final Set<String> _alertedIds = {};
  bool _refreshing = false;
  bool _baselineReady = false;

  void _syncWithAuth(AuthSessionState session) {
    if (session is AuthSessionAuthenticated) {
      _start();
      unawaited(refreshNow());
    } else {
      _stop();
      _knownIds = null;
      _alertedIds.clear();
      _baselineReady = false;
    }
  }

  void _start() {
    _timer?.cancel();
    _timer = Timer.periodic(_liveRefreshInterval, (_) {
      unawaited(refreshNow());
    });
  }

  void _stop() {
    _timer?.cancel();
    _timer = null;
  }

  Future<void> refreshNow() async {
    if (_ref.read(authSessionProvider) is! AuthSessionAuthenticated) return;
    if (_refreshing) return;
    _refreshing = true;
    state++;

    try {
      _ref.invalidate(homeDashboardProvider);
      _ref.invalidate(parentNotificationsProvider);

      try {
        await _ref.read(homeDashboardProvider.future);
      } catch (_) {}

      final inbox = await _ref.read(parentNotificationsProvider.future);
      final ids =
          inbox.items.map((e) => e.id).where((id) => id.isNotEmpty).toSet();

      final prevIds = _knownIds;
      _knownIds = ids;

      // 1er passage : mémoriser sans alerter.
      if (!_baselineReady || prevIds == null) {
        _baselineReady = true;
        _alertedIds.addAll(ids);
        return;
      }

      final newcomers = ids.difference(prevIds);
      // Uniquement les vrais nouveaux ids, jamais déjà alertés.
      final toAlert = newcomers.difference(_alertedIds);
      if (toAlert.isEmpty) return;

      final newest = inbox.items.firstWhere(
        (e) => toAlert.contains(e.id),
        orElse: () => inbox.items.first,
      );
      _alertedIds.addAll(toAlert);

      final title =
          newest.title.isNotEmpty ? newest.title : 'ELIMU Go';
      final body = newest.subtitle.isNotEmpty
          ? newest.subtitle
          : 'Vous avez une nouvelle notification.';

      // Une seule notification système (pas de 2e bandeau « test »).
      await _ref.read(pushNotificationServiceProvider).showLocalAlert(
            title: title,
            body: body,
            dedupeKey: newest.id,
            showInAppBanner: false,
          );
    } catch (_) {
      // Réseau / 429 : prochain tick.
    } finally {
      _refreshing = false;
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState lifecycle) {
    if (lifecycle == AppLifecycleState.resumed) {
      unawaited(refreshNow());
      _start();
    }
  }

  void tearDown() {
    _stop();
    _authSub?.close();
    WidgetsBinding.instance.removeObserver(this);
  }
}

final liveRefreshProvider =
    StateNotifierProvider<LiveRefreshController, int>((ref) {
  final controller = LiveRefreshController(ref);
  ref.onDispose(controller.tearDown);
  return controller;
});
