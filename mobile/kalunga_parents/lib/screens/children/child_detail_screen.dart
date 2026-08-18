import 'package:flutter/material.dart';

import '../../core/theme/app_theme_colors.dart';
import '../../models/child_models.dart';

/// Détail enfant — placeholder jusqu'au module suivant.
class ChildDetailScreen extends StatelessWidget {
  const ChildDetailScreen({
    super.key,
    required this.child,
  });

  final ChildSummary child;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: context.appBackground,
      appBar: AppBar(
        backgroundColor: context.appPrimary,
        foregroundColor: Colors.white,
        title: Text(child.displayName),
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              child.displayName,
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w700,
                color: context.appTextPrimary,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              child.classLabel,
              style: TextStyle(
                fontSize: 15,
                color: context.appTextSecondary,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Matricule: ${child.matricule}',
              style: TextStyle(
                fontSize: 14,
                color: context.appTextSecondary,
              ),
            ),
            const SizedBox(height: 24),
            Text(
              'Le dossier complet de l’élève sera développé dans un prochain module.',
              style: TextStyle(
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
