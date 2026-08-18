import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../constants/app_constants.dart';
import '../../core/l10n/app_strings.dart';
import '../../core/theme/app_colors.dart';
import '../../providers/auth_providers.dart';
import '../../providers/home_providers.dart';
import '../../providers/profile_photo_provider.dart';
import '../../providers/settings_providers.dart';
import '../about/about_screen.dart';
import 'help_support_screen.dart';
import 'personal_info_screen.dart';

/// Onglet Mon Compte — maquette écran 5 (layout identique).
class AccountScreen extends ConsumerWidget {
  const AccountScreen({super.key});

  static const _logoutRed = Color(0xFFD32F2F);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(authSessionProvider);
    final language = ref.watch(appLanguageProvider);
    final themeMode = ref.watch(themeModeProvider);
    final s = ref.watch(appStringsProvider);
    final themeLabel = switch (themeMode) {
      ThemeMode.dark => s.themeDark,
      ThemeMode.system => s.themeSystem,
      ThemeMode.light => s.themeLight,
    };

    final name = switch (session) {
      AuthSessionAuthenticated(:final identity)
          when identity.displayName.isNotEmpty =>
        identity.displayName,
      _ => 'Parent',
    };
    final phone = switch (session) {
      AuthSessionAuthenticated(:final identity) => identity.phone.trim(),
      _ => '',
    };
    final email = switch (session) {
      AuthSessionAuthenticated(:final identity) => identity.email.trim(),
      _ => '',
    };

    final isDark = Theme.of(context).brightness == Brightness.dark;
    final pageBg = isDark ? const Color(0xFF121412) : const Color(0xFFF5F5F5);
    final cardBg = isDark ? const Color(0xFF1C211D) : Colors.white;
    final textPrimary =
        isDark ? const Color(0xFFF1F3F1) : const Color(0xFF212121);
    final textSecondary =
        isDark ? const Color(0xFFA7B0A9) : const Color(0xFF757575);
    final divider =
        isDark ? const Color(0xFF2C332E) : const Color(0xFFEEEEEE);

    return ColoredBox(
      color: pageBg,
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          // Bandeau vert + titre (maquette).
          ColoredBox(
            color: AppColors.primary,
            child: Column(
              children: [
                const SizedBox(height: 8),
                SizedBox(
                  height: 44,
                  child: Center(
                    child: Text(
                      s.accountTitle,
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                        fontSize: 18,
                      ),
                    ),
                  ),
                ),
                // Espace pour que la carte profil chevauche le vert.
                const SizedBox(height: 52),
              ],
            ),
          ),
          // Carte profil centrée chevauchant le bandeau.
          Transform.translate(
            offset: const Offset(0, -44),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Material(
                color: cardBg,
                elevation: isDark ? 0 : 3,
                shadowColor: Colors.black26,
                borderRadius: BorderRadius.circular(AppConstants.radiusLarge),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(20, 20, 20, 18),
                  child: _ProfileBlock(
                    name: name,
                    phone: phone,
                    email: email,
                    roleLabel: s.parentTutor,
                    textPrimary: textPrimary,
                    textSecondary: textSecondary,
                    sheetBg: cardBg,
                  ),
                ),
              ),
            ),
          ),
          Transform.translate(
            offset: const Offset(0, -28),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _SectionTitle(s.accountSettings, color: textSecondary),
                  const SizedBox(height: 8),
                  _SettingsGroup(
                    color: cardBg,
                    divider: divider,
                    children: [
                      _SettingsRow(
                        icon: Icons.person_outline,
                        label: s.personalInfo,
                        textPrimary: textPrimary,
                        textSecondary: textSecondary,
                        onTap: () {
                          Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) => const PersonalInfoScreen(),
                            ),
                          );
                        },
                      ),
                      _SettingsRow(
                        icon: Icons.language,
                        label: s.languageMenu,
                        trailingValue: language.label,
                        textPrimary: textPrimary,
                        textSecondary: textSecondary,
                        onTap: () => _pickLanguage(context, ref, s, cardBg),
                      ),
                      _SettingsRow(
                        icon: Icons.wb_sunny_outlined,
                        label: s.theme,
                        trailingValue: themeLabel,
                        textPrimary: textPrimary,
                        textSecondary: textSecondary,
                        onTap: () => _pickTheme(context, ref, s, cardBg),
                      ),
                    ],
                  ),
                  const SizedBox(height: 22),
                  _SectionTitle(s.others, color: textSecondary),
                  const SizedBox(height: 8),
                  _SettingsGroup(
                    color: cardBg,
                    divider: divider,
                    children: [
                      _SettingsRow(
                        icon: Icons.info_outline,
                        label: s.aboutTitle,
                        textPrimary: textPrimary,
                        textSecondary: textSecondary,
                        onTap: () {
                          Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) => const AboutScreen(),
                            ),
                          );
                        },
                      ),
                      _SettingsRow(
                        icon: Icons.help_outline,
                        label: s.helpSupport,
                        textPrimary: textPrimary,
                        textSecondary: textSecondary,
                        onTap: () {
                          Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) => const HelpSupportScreen(),
                            ),
                          );
                        },
                      ),
                      _SettingsRow(
                        icon: Icons.logout,
                        label: s.logout,
                        textPrimary: _logoutRed,
                        textSecondary: textSecondary,
                        iconColor: _logoutRed,
                        showChevron: false,
                        onTap: () =>
                            _confirmLogout(context, ref, s, cardBg),
                      ),
                    ],
                  ),
                  const SizedBox(height: 28),
                  _DeveloperCredit(
                    label: s.developedBy,
                    muted: textSecondary,
                  ),
                  const SizedBox(height: 32),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  static Future<void> _pickLanguage(
    BuildContext context,
    WidgetRef ref,
    AppStrings s,
    Color sheetBg,
  ) async {
    final current = ref.read(appLanguageProvider);
    final selected = await showModalBottomSheet<AppLanguage>(
      context: context,
      backgroundColor: sheetBg,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                child: Text(
                  s.languageMenu,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              for (final lang in AppLanguage.values)
                ListTile(
                  title: Text(lang.label),
                  trailing: lang == current
                      ? const Icon(Icons.check, color: AppColors.primary)
                      : null,
                  onTap: () => Navigator.pop(ctx, lang),
                ),
              const SizedBox(height: 8),
            ],
          ),
        );
      },
    );
    if (selected != null) {
      await ref.read(appLanguageProvider.notifier).setLanguage(selected);
    }
  }

  static Future<void> _pickTheme(
    BuildContext context,
    WidgetRef ref,
    AppStrings s,
    Color sheetBg,
  ) async {
    final current = ref.read(themeModeProvider);
    final options = <(ThemeMode, String, IconData)>[
      (ThemeMode.light, s.themeLight, Icons.wb_sunny_outlined),
      (ThemeMode.dark, s.themeDark, Icons.dark_mode_outlined),
      (ThemeMode.system, s.themeSystem, Icons.settings_suggest_outlined),
    ];
    final selected = await showModalBottomSheet<ThemeMode>(
      context: context,
      backgroundColor: sheetBg,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                child: Text(
                  s.theme,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              for (final opt in options)
                ListTile(
                  leading: Icon(opt.$3, color: AppColors.primaryLight),
                  title: Text(opt.$2),
                  trailing: opt.$1 == current
                      ? const Icon(Icons.check, color: AppColors.primary)
                      : null,
                  onTap: () => Navigator.pop(ctx, opt.$1),
                ),
              const SizedBox(height: 8),
            ],
          ),
        );
      },
    );
    if (selected != null) {
      await ref.read(themeModeProvider.notifier).setThemeMode(selected);
    }
  }

  static Future<void> _confirmLogout(
    BuildContext context,
    WidgetRef ref,
    AppStrings s,
    Color dialogBg,
  ) async {
    final ok = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        backgroundColor: dialogBg,
        title: Text(s.logoutConfirmTitle),
        content: Text(s.logoutConfirmBody),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text(s.cancel),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: _logoutRed),
            child: Text(s.logout),
          ),
        ],
      ),
    );
    if (ok == true) {
      ref.read(notificationsBadgeOptimisticZeroProvider.notifier).state = false;
      await ref.read(authSessionProvider.notifier).logout();
    }
  }
}

class _ProfileBlock extends ConsumerWidget {
  const _ProfileBlock({
    required this.name,
    required this.phone,
    required this.email,
    required this.roleLabel,
    required this.textPrimary,
    required this.textSecondary,
    required this.sheetBg,
  });

  final String name;
  final String phone;
  final String email;
  final String roleLabel;
  final Color textPrimary;
  final Color textSecondary;
  final Color sheetBg;

  String get _initials {
    final parts = name
        .trim()
        .split(RegExp(r'\s+'))
        .where((p) => p.isNotEmpty)
        .toList();
    if (parts.isEmpty) return '?';
    if (parts.length == 1) {
      final s = parts.first;
      return s.substring(0, s.length >= 2 ? 2 : 1).toUpperCase();
    }
    return ('${parts.first[0]}${parts.last[0]}').toUpperCase();
  }

  Future<void> _openPhotoSheet(BuildContext context, WidgetRef ref) async {
    final s = ref.read(appStringsProvider);
    final hasPhoto = ref.read(profilePhotoProvider) != null;
    final action = await showModalBottomSheet<_PhotoAction>(
      context: context,
      backgroundColor: sheetBg,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                child: Text(
                  s.changeProfilePhoto,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              ListTile(
                leading: const Icon(Icons.photo_library_outlined),
                title: Text(s.chooseFromGallery),
                onTap: () => Navigator.pop(ctx, _PhotoAction.gallery),
              ),
              ListTile(
                leading: const Icon(Icons.photo_camera_outlined),
                title: Text(s.takePhoto),
                onTap: () => Navigator.pop(ctx, _PhotoAction.camera),
              ),
              if (hasPhoto)
                ListTile(
                  leading: const Icon(
                    Icons.delete_outline,
                    color: Color(0xFFD32F2F),
                  ),
                  title: Text(
                    s.removePhoto,
                    style: const TextStyle(color: Color(0xFFD32F2F)),
                  ),
                  onTap: () => Navigator.pop(ctx, _PhotoAction.remove),
                ),
              ListTile(
                title: Text(s.cancel),
                onTap: () => Navigator.pop(ctx),
              ),
              const SizedBox(height: 8),
            ],
          ),
        );
      },
    );
    if (action == null || !context.mounted) return;

    final notifier = ref.read(profilePhotoProvider.notifier);
    var ok = true;
    switch (action) {
      case _PhotoAction.gallery:
        ok = await notifier.pickFromGallery();
      case _PhotoAction.camera:
        ok = await notifier.pickFromCamera();
      case _PhotoAction.remove:
        await notifier.clear();
        return;
    }
    if (!ok && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(s.photoPickFailed)),
      );
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final photoBytes = ref.watch(profilePhotoProvider);

    return Column(
      children: [
        GestureDetector(
          onTap: () => _openPhotoSheet(context, ref),
          child: Stack(
            clipBehavior: Clip.none,
            children: [
              CircleAvatar(
                radius: 44,
                backgroundColor: AppColors.lightGreen,
                backgroundImage: photoBytes != null
                    ? MemoryImage(photoBytes)
                    : null,
                child: photoBytes == null
                    ? Text(
                        _initials,
                        style: const TextStyle(
                          color: AppColors.primary,
                          fontSize: 28,
                          fontWeight: FontWeight.w700,
                        ),
                      )
                    : null,
              ),
              Positioned(
                right: -2,
                bottom: -2,
                child: Material(
                  color: AppColors.primary,
                  shape: const CircleBorder(),
                  elevation: 2,
                  child: const Padding(
                    padding: EdgeInsets.all(7),
                    child: Icon(
                      Icons.camera_alt_outlined,
                      size: 16,
                      color: Colors.white,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Text(
          name,
          textAlign: TextAlign.center,
          style: TextStyle(
            color: textPrimary,
            fontSize: 18,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          roleLabel,
          style: TextStyle(
            color: textSecondary,
            fontSize: 13,
            fontWeight: FontWeight.w400,
          ),
        ),
        if (phone.isNotEmpty) ...[
          const SizedBox(height: 14),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.phone, size: 15, color: textSecondary),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  phone,
                  style: TextStyle(color: textSecondary, fontSize: 13.5),
                ),
              ),
            ],
          ),
        ],
        if (email.isNotEmpty) ...[
          const SizedBox(height: 6),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.email_outlined, size: 15, color: textSecondary),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  email,
                  style: TextStyle(color: textSecondary, fontSize: 13.5),
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }
}

enum _PhotoAction { gallery, camera, remove }

class _DeveloperCredit extends StatelessWidget {
  const _DeveloperCredit({
    required this.label,
    required this.muted,
  });

  final String label;
  final Color muted;

  Future<void> _openSite() async {
    final uri = Uri.parse(AppConstants.developerUrl);
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        child: Text.rich(
          TextSpan(
            style: TextStyle(
              color: muted,
              fontSize: 12.5,
              fontWeight: FontWeight.w400,
              height: 1.35,
            ),
            children: [
              TextSpan(text: '$label '),
              WidgetSpan(
                alignment: PlaceholderAlignment.baseline,
                baseline: TextBaseline.alphabetic,
                child: GestureDetector(
                  onTap: _openSite,
                  child: Text(
                    AppConstants.developerName,
                    style: TextStyle(
                      color: AppColors.primary,
                      fontSize: 12.5,
                      fontWeight: FontWeight.w600,
                      decoration: TextDecoration.underline,
                      decorationColor: AppColors.primary.withOpacity(0.55),
                    ),
                  ),
                ),
              ),
            ],
          ),
          textAlign: TextAlign.center,
        ),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.text, {required this.color});

  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: TextStyle(
        color: color,
        fontSize: 13,
        fontWeight: FontWeight.w600,
      ),
    );
  }
}

class _SettingsGroup extends StatelessWidget {
  const _SettingsGroup({
    required this.children,
    required this.color,
    required this.divider,
  });

  final List<Widget> children;
  final Color color;
  final Color divider;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: color,
      borderRadius: BorderRadius.circular(AppConstants.radiusLarge),
      child: Column(
        children: [
          for (var i = 0; i < children.length; i++) ...[
            children[i],
            if (i < children.length - 1)
              Divider(height: 1, thickness: 1, indent: 52, color: divider),
          ],
        ],
      ),
    );
  }
}

class _SettingsRow extends StatelessWidget {
  const _SettingsRow({
    required this.icon,
    required this.label,
    required this.onTap,
    required this.textPrimary,
    required this.textSecondary,
    this.trailingValue,
    this.iconColor,
    this.showChevron = true,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final Color textPrimary;
  final Color textSecondary;
  final String? trailingValue;
  final Color? iconColor;
  final bool showChevron;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppConstants.radiusLarge),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 15),
        child: Row(
          children: [
            Icon(icon, color: iconColor ?? textSecondary, size: 22),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                label,
                style: TextStyle(
                  color: textPrimary,
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
            if (trailingValue != null) ...[
              Text(
                trailingValue!,
                style: TextStyle(color: textSecondary, fontSize: 13.5),
              ),
              const SizedBox(width: 4),
            ],
            if (showChevron)
              Icon(Icons.chevron_right, color: textSecondary, size: 22),
          ],
        ),
      ),
    );
  }
}
