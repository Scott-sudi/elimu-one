import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/theme/app_theme_colors.dart';
import '../services/app_permissions_service.dart';
import '../services/push_notification_service.dart';

/// Au premier lancement : autorisations + enregistrement du canal Android.
class StartupPermissionsGate extends ConsumerStatefulWidget {
  const StartupPermissionsGate({super.key, required this.child});

  final Widget child;

  @override
  ConsumerState<StartupPermissionsGate> createState() =>
      _StartupPermissionsGateState();
}

class _StartupPermissionsGateState
    extends ConsumerState<StartupPermissionsGate> {
  bool _ready = kIsWeb;

  @override
  void initState() {
    super.initState();
    if (!kIsWeb) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _bootstrap());
    }
  }

  Future<void> _bootstrap() async {
    if (!mounted) return;
    final already = await AppPermissionsService.wasPrompted();
    if (!mounted) return;

    if (!already) {
      await showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (ctx) {
          return AlertDialog(
            title: const Text('Autorisations'),
            content: const Text(
              'Pour bien fonctionner, ELIMU Go a besoin d’accéder aux '
              'notifications (alertes école), à la caméra et aux photos/fichiers '
              '(photo de profil).\n\n'
              'Autorisez ces accès sur les écrans suivants.',
            ),
            actions: [
              FilledButton(
                onPressed: () => Navigator.of(ctx).pop(),
                child: const Text('Continuer'),
              ),
            ],
          );
        },
      );
      if (!mounted) return;
      await AppPermissionsService.requestStartupPermissions();
    }

    // Crée le canal Android dès le démarrage (sinon Réglages dit
    // « aucune notification publiée » et pas de son système).
    try {
      await ref.read(pushNotificationServiceProvider).init();
    } catch (_) {}

    if (mounted) setState(() => _ready = true);
  }

  @override
  Widget build(BuildContext context) {
    if (!_ready) {
      return Scaffold(
        backgroundColor: context.appBackground,
        body: Center(
          child: CircularProgressIndicator(color: context.appPrimary),
        ),
      );
    }
    return widget.child;
  }
}
