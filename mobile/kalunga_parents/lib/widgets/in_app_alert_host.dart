import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/home_providers.dart';
import '../services/push_notification_service.dart';

/// Bannière en haut d’écran quand une alerte arrive (app ouverte).
class InAppAlertHost extends ConsumerStatefulWidget {
  const InAppAlertHost({super.key, required this.child});

  final Widget child;

  @override
  ConsumerState<InAppAlertHost> createState() => _InAppAlertHostState();
}

class _InAppAlertHostState extends ConsumerState<InAppAlertHost>
    with SingleTickerProviderStateMixin {
  Timer? _hideTimer;
  late final AnimationController _anim;
  late final Animation<Offset> _slide;

  @override
  void initState() {
    super.initState();
    _anim = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 280),
    );
    _slide = Tween<Offset>(
      begin: const Offset(0, -1.2),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _anim, curve: Curves.easeOutCubic));
  }

  @override
  void dispose() {
    _hideTimer?.cancel();
    _anim.dispose();
    super.dispose();
  }

  void _present() {
    _hideTimer?.cancel();
    _anim.forward(from: 0);
    _hideTimer = Timer(const Duration(seconds: 5), () async {
      if (!mounted) return;
      await _anim.reverse();
      if (!mounted) return;
      ref.read(inAppAlertProvider.notifier).state = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    ref.listen<InAppAlert?>(inAppAlertProvider, (prev, next) {
      if (next != null) _present();
    });

    final alert = ref.watch(inAppAlertProvider);

    return Stack(
      children: [
        widget.child,
        if (alert != null)
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: SafeArea(
              bottom: false,
              child: SlideTransition(
                position: _slide,
                child: Material(
                  color: Colors.transparent,
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(14),
                      onTap: () {
                        ref.read(inAppAlertProvider.notifier).state = null;
                        ref.read(bottomNavIndexProvider.notifier).state = 2;
                      },
                      child: Ink(
                        decoration: BoxDecoration(
                          color: const Color(0xFF111111),
                          borderRadius: BorderRadius.circular(14),
                          boxShadow: const [
                            BoxShadow(
                              color: Color(0x44000000),
                              blurRadius: 12,
                              offset: Offset(0, 4),
                            ),
                          ],
                        ),
                        padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
                        child: Row(
                          children: [
                            Container(
                              width: 40,
                              height: 40,
                              decoration: const BoxDecoration(
                                color: Color(0xFFE8B923),
                                shape: BoxShape.circle,
                              ),
                              child: const Icon(
                                Icons.notifications_active,
                                color: Colors.black,
                                size: 22,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(
                                    alert.title,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.w700,
                                      fontSize: 14,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    alert.body,
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      color: Color(0xFFDDDDDD),
                                      fontSize: 13,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}
