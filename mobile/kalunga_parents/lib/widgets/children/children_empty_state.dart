import 'package:flutter/material.dart';

import '../../core/theme/app_theme_colors.dart';

/// État vide — maquette « Mes Enfants ».
class ChildrenEmptyState extends StatelessWidget {
  const ChildrenEmptyState({super.key});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.people_outline,
              size: 72,
              color: context.appPrimary.withOpacity(0.45),
            ),
            const SizedBox(height: 16),
            Text(
              'Aucun enfant trouvé',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: context.appTextPrimary,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Vous n\'avez aucun enfant lié à ce numéro.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 14,
                color: context.appTextSecondary,
                height: 1.4,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
