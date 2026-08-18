import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_theme_colors.dart';

/// En-tête Accueil : salutation + badge notifications.
class HomeHeader extends StatelessWidget {
  const HomeHeader({
    super.key,
    required this.parentName,
    required this.notificationCount,
    required this.helloLabel,
    required this.welcomeLabel,
    required this.notificationsTooltip,
    this.onNotificationTap,
  });

  final String parentName;
  final int notificationCount;
  final String helloLabel;
  final String welcomeLabel;
  final String notificationsTooltip;
  final VoidCallback? onNotificationTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 8, 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                RichText(
                  text: TextSpan(
                    style: TextStyle(
                      fontSize: 20,
                      color: context.appTextPrimary,
                      height: 1.25,
                    ),
                    children: [
                      TextSpan(
                        text: '$helloLabel\n',
                        style: const TextStyle(fontWeight: FontWeight.w400),
                      ),
                      TextSpan(
                        text: '$parentName 👋',
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  welcomeLabel,
                  style: TextStyle(
                    color: context.appTextSecondary,
                    fontSize: 13,
                    fontWeight: FontWeight.w400,
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            onPressed: onNotificationTap,
            tooltip: notificationsTooltip,
            icon: Badge(
              isLabelVisible: notificationCount > 0,
              backgroundColor: AppColors.badge,
              label: Text(
                notificationCount > 99 ? '99+' : '$notificationCount',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                ),
              ),
              child: Icon(
                Icons.notifications_none_outlined,
                color: context.appTextPrimary,
                size: 28,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
