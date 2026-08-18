import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_theme_colors.dart';
import '../../providers/settings_providers.dart';

/// Barre de navigation inférieure à 4 onglets (À propos est dans Mon Compte).
class CustomBottomNavbar extends ConsumerWidget {
  const CustomBottomNavbar({
    super.key,
    required this.currentIndex,
    required this.onTap,
    this.notificationBadge = 0,
  });

  final int currentIndex;
  final ValueChanged<int> onTap;
  final int notificationBadge;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = ref.watch(appStringsProvider);
    final card = context.appCard;
    final selected = context.appPrimary;
    final unselected = context.appTextSecondary;

    return Container(
      decoration: BoxDecoration(
        color: card,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(context.isDarkTheme ? 0.35 : 0.06),
            blurRadius: 10,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: BottomNavigationBar(
          currentIndex: currentIndex,
          onTap: onTap,
          type: BottomNavigationBarType.fixed,
          backgroundColor: card,
          elevation: 0,
          selectedItemColor: selected,
          unselectedItemColor: unselected,
          selectedFontSize: 12.5,
          unselectedFontSize: 12,
          iconSize: 26,
          selectedLabelStyle: const TextStyle(fontWeight: FontWeight.w700),
          unselectedLabelStyle: const TextStyle(fontWeight: FontWeight.w500),
          items: [
            BottomNavigationBarItem(
              icon: const Icon(Icons.home_outlined),
              activeIcon: const Icon(Icons.home),
              label: s.navHome,
            ),
            BottomNavigationBarItem(
              icon: const Icon(Icons.people_outline),
              activeIcon: const Icon(Icons.people),
              label: s.navChildren,
            ),
            BottomNavigationBarItem(
              icon: _NavBadgeIcon(
                icon: Icons.notifications_none_outlined,
                count: notificationBadge,
                selected: false,
              ),
              activeIcon: _NavBadgeIcon(
                icon: Icons.notifications,
                count: notificationBadge,
                selected: true,
              ),
              label: s.navNotifications,
            ),
            BottomNavigationBarItem(
              icon: const Icon(Icons.person_outline),
              activeIcon: const Icon(Icons.person),
              label: s.navAccount,
            ),
          ],
        ),
      ),
    );
  }
}

class _NavBadgeIcon extends StatelessWidget {
  const _NavBadgeIcon({
    required this.icon,
    required this.count,
    required this.selected,
  });

  final IconData icon;
  final int count;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    return Badge(
      isLabelVisible: count > 0,
      backgroundColor: AppColors.badge,
      label: Text(
        '$count',
        style: const TextStyle(fontSize: 10, color: Colors.white),
      ),
      child: Icon(
        icon,
        size: 26,
        color: selected ? context.appPrimary : context.appTextSecondary,
      ),
    );
  }
}
