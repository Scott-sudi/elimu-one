import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../constants/app_constants.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_theme_colors.dart';
import '../../models/child_models.dart';

/// Actions rapides sur une carte enfant (sans Devoirs — professeurs pas encore connectés).
enum ChildQuickAction { presence, absences, discipline, payments }

/// Carte élève — maquette « Mes Enfants » (Voir conservé via chevron / tap fiche).
class ChildCard extends StatelessWidget {
  const ChildCard({
    super.key,
    required this.child,
    this.onOpenProfile,
    this.onAction,
  });

  final ChildSummary child;
  final VoidCallback? onOpenProfile;
  final void Function(ChildQuickAction action)? onAction;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: context.appCard,
      borderRadius: BorderRadius.circular(AppConstants.radiusLarge),
      elevation: context.isDarkTheme ? 0 : 1.5,
      shadowColor: AppColors.shadow,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 14, 10, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            InkWell(
              onTap: onOpenProfile,
              borderRadius: BorderRadius.circular(AppConstants.radiusMedium),
              child: Row(
                children: [
                  _Avatar(child: child),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          child.displayName,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: context.appTextPrimary,
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          child.classLabel,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: context.appTextSecondary,
                            fontSize: 13,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Matricule : ${child.matricule}',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: context.appTextSecondary,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  _StatusBadge(isActive: child.isActive),
                  IconButton(
                    tooltip: 'Voir',
                    onPressed: onOpenProfile,
                    icon: Icon(
                      Icons.chevron_right,
                      color: context.appTextSecondary,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: _QuickActionTile(
                    label: 'Présence',
                    icon: Icons.event_available_outlined,
                    background: context.isDarkTheme
                        ? const Color(0xFF243028)
                        : AppColors.actionPresenceBg,
                    iconColor: context.appPrimary,
                    onTap: () => onAction?.call(ChildQuickAction.presence),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _QuickActionTile(
                    label: 'Absences',
                    icon: Icons.person_off_outlined,
                    background: context.isDarkTheme
                        ? const Color(0xFF2A2420)
                        : AppColors.actionAbsenceBg,
                    iconColor: AppColors.activityMeeting,
                    onTap: () => onAction?.call(ChildQuickAction.absences),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _QuickActionTile(
                    label: 'Discipline',
                    icon: Icons.folder_outlined,
                    background: context.isDarkTheme
                        ? const Color(0xFF2A2030)
                        : AppColors.actionDisciplineBg,
                    iconColor: const Color(0xFF7B1FA2),
                    onTap: () => onAction?.call(ChildQuickAction.discipline),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _QuickActionTile(
                    label: 'Paiements',
                    icon: Icons.account_balance_wallet_outlined,
                    background: context.isDarkTheme
                        ? const Color(0xFF243028)
                        : AppColors.actionPaymentBg,
                    iconColor: context.appPrimary,
                    onTap: () => onAction?.call(ChildQuickAction.payments),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _QuickActionTile extends StatelessWidget {
  const _QuickActionTile({
    required this.label,
    required this.icon,
    required this.background,
    required this.iconColor,
    this.onTap,
  });

  final String label;
  final IconData icon;
  final Color background;
  final Color iconColor;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: background,
      borderRadius: BorderRadius.circular(10),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, color: iconColor, size: 22),
              const SizedBox(height: 4),
              Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: context.appTextPrimary,
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Avatar extends StatelessWidget {
  const _Avatar({required this.child});

  final ChildSummary child;

  @override
  Widget build(BuildContext context) {
    final url = child.photoUrl;
    final initials = Text(
      child.initials,
      style: TextStyle(
        color: context.appPrimary,
        fontWeight: FontWeight.w700,
        fontSize: 16,
      ),
    );

    return ClipOval(
      child: Container(
        width: 56,
        height: 56,
        color: context.appAvatarBg,
        alignment: Alignment.center,
        child: (url == null || url.isEmpty)
            ? initials
            : Image.network(
                url,
                key: ValueKey(url),
                fit: BoxFit.cover,
                width: 56,
                height: 56,
                webHtmlElementStrategy: kIsWeb
                    ? WebHtmlElementStrategy.prefer
                    : WebHtmlElementStrategy.never,
                filterQuality: FilterQuality.medium,
                errorBuilder: (_, __, ___) => initials,
                loadingBuilder: (context, childWidget, progress) {
                  if (progress == null) return childWidget;
                  return SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: context.appPrimary,
                    ),
                  );
                },
              ),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.isActive});

  final bool isActive;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: isActive
            ? context.appAvatarBg
            : (context.isDarkTheme
                ? const Color(0xFF2C332E)
                : AppColors.inactiveBadgeBg),
        borderRadius: BorderRadius.circular(AppConstants.radiusSmall),
      ),
      child: Text(
        isActive ? 'Actif' : 'Inactif',
        style: TextStyle(
          color: isActive
              ? context.appPrimary
              : (context.isDarkTheme
                  ? context.appTextSecondary
                  : AppColors.inactiveBadge),
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
