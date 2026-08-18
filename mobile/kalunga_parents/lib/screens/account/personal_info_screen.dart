import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../constants/app_constants.dart';
import '../../core/l10n/app_strings.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_theme_colors.dart';
import '../../models/parent_profile.dart';
import '../../providers/settings_providers.dart';

/// Fiche identité — lecture seule (données secrétariat).
class PersonalInfoScreen extends ConsumerWidget {
  const PersonalInfoScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncProfile = ref.watch(parentProfileProvider);
    final s = ref.watch(appStringsProvider);

    return Scaffold(
      backgroundColor: context.appBackground,
      appBar: AppBar(
        backgroundColor: AppColors.primary,
        foregroundColor: AppColors.textOnPrimary,
        title: Text(
          s.personalInfo,
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 17),
        ),
      ),
      body: asyncProfile.when(
        loading: () => Center(
          child: CircularProgressIndicator(color: context.appPrimary),
        ),
        error: (e, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(e.toString(), textAlign: TextAlign.center),
                const SizedBox(height: 12),
                ElevatedButton(
                  onPressed: () => ref.invalidate(parentProfileProvider),
                  child: Text(s.retry),
                ),
              ],
            ),
          ),
        ),
        data: (profile) {
          final rows = _rows(profile, s);
          return RefreshIndicator(
            color: AppColors.primary,
            onRefresh: () async {
              ref.invalidate(parentProfileProvider);
              await ref.read(parentProfileProvider.future);
            },
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              children: [
                Material(
                  color: context.appCard,
                  borderRadius:
                      BorderRadius.circular(AppConstants.radiusLarge),
                  elevation: context.isDarkTheme ? 0 : 1,
                  shadowColor: AppColors.shadow,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    child: Column(
                      children: [
                        for (var i = 0; i < rows.length; i++) ...[
                          if (i > 0)
                            Divider(
                              height: 1,
                              indent: 16,
                              endIndent: 16,
                              color: context.appDivider,
                            ),
                          _InfoRow(label: rows[i].$1, value: rows[i].$2),
                        ],
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  s.personalInfoHint,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: context.appTextSecondary,
                    fontSize: 12.5,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  List<(String, String)> _rows(ParentProfile p, AppStrings s) {
    return <(String, String)>[
      (s.fullName, _orDash(p.displayName)),
      if (p.prenom.isNotEmpty) (s.firstName, p.prenom),
      if (p.nom.isNotEmpty) (s.lastName, p.nom),
      if (p.postnom.isNotEmpty) (s.postName, p.postnom),
      if (p.sexe.isNotEmpty) (s.gender, p.sexe),
      (s.phone, _orDash(p.telephone)),
      if (p.telephoneSecondaire.isNotEmpty)
        (s.phoneSecondary, p.telephoneSecondaire),
      (s.email, _orDash(p.email)),
      if (p.profession.isNotEmpty) (s.profession, p.profession),
      if (p.adresse.isNotEmpty) (s.address, p.adresse),
      if (p.numeroIdentification.isNotEmpty)
        (s.idNumber, p.numeroIdentification),
    ];
  }

  String _orDash(String value) => value.trim().isEmpty ? '—' : value.trim();
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: TextStyle(
                color: context.appTextSecondary,
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: TextStyle(
                color: context.appTextPrimary,
                fontSize: 14.5,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
