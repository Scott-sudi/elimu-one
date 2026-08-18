import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../constants/app_constants.dart';
import '../../core/theme/app_colors.dart';
import '../../providers/settings_providers.dart';

/// Onglet À propos — maquette écran 4 : blocs séparés + infos Kalunga.
class AboutScreen extends ConsumerWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = ref.watch(appStringsProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final pageBg = isDark ? const Color(0xFF121412) : const Color(0xFFF5F5F5);
    final cardBg = isDark ? const Color(0xFF1C211D) : Colors.white;
    final textPrimary =
        isDark ? const Color(0xFFF1F3F1) : const Color(0xFF212121);
    final textSecondary =
        isDark ? const Color(0xFFA7B0A9) : const Color(0xFF757575);

    return Scaffold(
      backgroundColor: pageBg,
      appBar: AppBar(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
        title: Text(
          s.aboutTitle,
          style: const TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w700,
            fontSize: 18,
          ),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
        children: [
                // Bloc identité
                _Block(
                  color: cardBg,
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      ClipOval(
                        child: Image.asset(
                          AppConstants.logoAsset,
                          width: 68,
                          height: 68,
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) => Container(
                            width: 68,
                            height: 68,
                            color: AppColors.lightGreen,
                            alignment: Alignment.center,
                            child: const Text(
                              'IK',
                              style: TextStyle(
                                color: AppColors.primary,
                                fontWeight: FontWeight.w800,
                                fontSize: 20,
                              ),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              AppConstants.appName.toUpperCase(),
                              style: TextStyle(
                                color: textPrimary,
                                fontSize: 17,
                                fontWeight: FontWeight.w800,
                                height: 1.15,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              AppConstants.appTagline,
                              style: TextStyle(
                                color: textSecondary,
                                fontSize: 13,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),

                // Bloc présentation
                _Block(
                  color: cardBg,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _GreenTitle(s.presentation),
                      const SizedBox(height: 10),
                      Text(
                        AppConstants.schoolPresentation,
                        textAlign: TextAlign.justify,
                        style: TextStyle(
                          color: textSecondary,
                          fontSize: 13.5,
                          height: 1.45,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),

                // Bloc options (grille 2×2)
                _Block(
                  color: cardBg,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _GreenTitle(s.ourOptions),
                      const SizedBox(height: 14),
                      _OptionsGrid(
                        options: AppConstants.schoolOptions,
                        textColor: textPrimary,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),

                // Bloc niveaux
                _Block(
                  color: cardBg,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _GreenTitle(s.ourLevels),
                      const SizedBox(height: 14),
                      Row(
                        children: [
                          Expanded(
                            child: _LevelItem(
                              icon: Icons.child_care_outlined,
                              label: s.levelNursery,
                              textColor: textPrimary,
                            ),
                          ),
                          Expanded(
                            child: _LevelItem(
                              icon: Icons.school_outlined,
                              label: s.levelPrimary,
                              textColor: textPrimary,
                            ),
                          ),
                          Expanded(
                            child: _LevelItem(
                              icon: Icons.menu_book_outlined,
                              label: s.levelSecondary,
                              textColor: textPrimary,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),

                // Bloc contact
                _Block(
                  color: cardBg,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _GreenTitle(s.contactUs),
                      const SizedBox(height: 12),
                      _ContactPhone(
                        phone: AppConstants.schoolPhonePrimary,
                        textColor: textPrimary,
                        onTap: () => _copy(
                          context,
                          AppConstants.schoolPhonePrimary,
                          s.copied,
                        ),
                      ),
                      const SizedBox(height: 10),
                      _ContactPhone(
                        phone: AppConstants.schoolPhoneSecondary,
                        textColor: textPrimary,
                        onTap: () => _copy(
                          context,
                          AppConstants.schoolPhoneSecondary,
                          s.copied,
                        ),
                      ),
                    ],
                  ),
                ),
        ],
      ),
    );
  }

  static Future<void> _copy(
    BuildContext context,
    String value,
    String copiedMsg,
  ) async {
    await Clipboard.setData(ClipboardData(text: value));
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(copiedMsg)),
    );
  }
}

class _Block extends StatelessWidget {
  const _Block({required this.child, required this.color});

  final Widget child;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Material(
      color: color,
      elevation: isDark ? 0 : 1.5,
      shadowColor: Colors.black26,
      borderRadius: BorderRadius.circular(AppConstants.radiusLarge),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 16),
        child: child,
      ),
    );
  }
}

class _GreenTitle extends StatelessWidget {
  const _GreenTitle(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        color: AppColors.primary,
        fontSize: 15.5,
        fontWeight: FontWeight.w700,
        decoration: TextDecoration.none,
        decorationThickness: 0,
      ),
    );
  }
}

class _OptionsGrid extends StatelessWidget {
  const _OptionsGrid({required this.options, required this.textColor});

  final List<String> options;
  final Color textColor;

  @override
  Widget build(BuildContext context) {
    // Grille 2 colonnes (données fiche identification).
    final left = <String>[];
    final right = <String>[];
    for (var i = 0; i < options.length; i++) {
      if (i.isEven) {
        left.add(options[i]);
      } else {
        right.add(options[i]);
      }
    }

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(child: _OptionColumn(items: left, textColor: textColor)),
        const SizedBox(width: 12),
        Expanded(child: _OptionColumn(items: right, textColor: textColor)),
      ],
    );
  }
}

class _OptionColumn extends StatelessWidget {
  const _OptionColumn({required this.items, required this.textColor});

  final List<String> items;
  final Color textColor;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (var i = 0; i < items.length; i++) ...[
          if (i > 0) const SizedBox(height: 12),
          Row(
            children: [
              const Icon(
                Icons.check_circle,
                color: AppColors.primary,
                size: 18,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  items[i],
                  style: TextStyle(
                    color: textColor,
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }
}

class _LevelItem extends StatelessWidget {
  const _LevelItem({
    required this.icon,
    required this.label,
    required this.textColor,
  });

  final IconData icon;
  final String label;
  final Color textColor;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: 40,
          height: 40,
          decoration: const BoxDecoration(
            color: AppColors.primary,
            shape: BoxShape.circle,
          ),
          child: Icon(icon, color: Colors.white, size: 20),
        ),
        const SizedBox(height: 8),
        Text(
          label,
          textAlign: TextAlign.center,
          style: TextStyle(
            color: textColor,
            fontSize: 12.5,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

class _ContactPhone extends StatelessWidget {
  const _ContactPhone({
    required this.phone,
    required this.textColor,
    required this.onTap,
  });

  final String phone;
  final Color textColor;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          children: [
            const Icon(Icons.phone, color: AppColors.primary, size: 20),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                phone,
                style: TextStyle(
                  color: textColor,
                  fontSize: 14.5,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
