import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../constants/app_constants.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_theme_colors.dart';
import '../../providers/settings_providers.dart';

/// Aide & support — contacts école + FAQ parents.
class HelpSupportScreen extends ConsumerWidget {
  const HelpSupportScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = ref.watch(appStringsProvider);

    return Scaffold(
      backgroundColor: context.appBackground,
      appBar: AppBar(
        backgroundColor: AppColors.primary,
        foregroundColor: AppColors.textOnPrimary,
        title: Text(
          s.helpSupport,
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 17),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
        children: [
          _SectionTitle(s.contactSchool),
          const SizedBox(height: 8),
          _Card(
            children: [
              _ContactTile(
                icon: Icons.phone_outlined,
                title: s.phone,
                subtitle: AppConstants.schoolPhonePrimary,
                onTap: () => _copy(
                  context,
                  AppConstants.schoolPhonePrimary,
                  s.copied,
                ),
              ),
              Divider(height: 1, indent: 56, color: context.appDivider),
              _ContactTile(
                icon: Icons.phone_outlined,
                title: s.phone,
                subtitle: AppConstants.schoolPhoneSecondary,
                onTap: () => _copy(
                  context,
                  AppConstants.schoolPhoneSecondary,
                  s.copied,
                ),
              ),
              Divider(height: 1, indent: 56, color: context.appDivider),
              _ContactTile(
                icon: Icons.place_outlined,
                title: s.address,
                subtitle:
                    '${AppConstants.schoolAddress} · ${AppConstants.schoolBp}',
              ),
              Divider(height: 1, indent: 56, color: context.appDivider),
              _ContactTile(
                icon: Icons.schedule_outlined,
                title: s.schoolHours,
                subtitle: AppConstants.schoolHours,
              ),
            ],
          ),
          const SizedBox(height: 24),
          _SectionTitle(s.faqTitle),
          const SizedBox(height: 8),
          _Card(
            children: [
              _FaqTile(question: s.faqLoginQ, answer: s.faqLoginA),
              Divider(
                height: 1,
                indent: 16,
                endIndent: 16,
                color: context.appDivider,
              ),
              _FaqTile(question: s.faqModulesQ, answer: s.faqModulesA),
              Divider(
                height: 1,
                indent: 16,
                endIndent: 16,
                color: context.appDivider,
              ),
              _FaqTile(question: s.faqNotifQ, answer: s.faqNotifA),
              Divider(
                height: 1,
                indent: 16,
                endIndent: 16,
                color: context.appDivider,
              ),
              _FaqTile(question: s.faqEditQ, answer: s.faqEditA),
            ],
          ),
          const SizedBox(height: 20),
          Text(
            '${AppConstants.appName} · ${AppConstants.appTagline}',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: context.appTextSecondary,
              fontSize: 12.5,
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

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text.toUpperCase(),
      style: TextStyle(
        color: context.appTextSecondary,
        fontSize: 12,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.6,
      ),
    );
  }
}

class _Card extends StatelessWidget {
  const _Card({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: context.appCard,
      borderRadius: BorderRadius.circular(AppConstants.radiusLarge),
      elevation: context.isDarkTheme ? 0 : 1,
      shadowColor: AppColors.shadow,
      child: Column(children: children),
    );
  }
}

class _ContactTile extends StatelessWidget {
  const _ContactTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      onTap: onTap,
      leading: Icon(icon, color: context.appPrimaryLight),
      title: Text(
        title,
        style: TextStyle(
          fontWeight: FontWeight.w600,
          fontSize: 14.5,
          color: context.appTextPrimary,
        ),
      ),
      subtitle: Text(
        subtitle,
        style: TextStyle(color: context.appTextSecondary, fontSize: 13),
      ),
      trailing: onTap == null
          ? null
          : Icon(Icons.copy, size: 18, color: context.appTextSecondary),
    );
  }
}

class _FaqTile extends StatelessWidget {
  const _FaqTile({required this.question, required this.answer});

  final String question;
  final String answer;

  @override
  Widget build(BuildContext context) {
    return Theme(
      data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
      child: ExpansionTile(
        tilePadding: const EdgeInsets.symmetric(horizontal: 16),
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 14),
        iconColor: context.appTextSecondary,
        collapsedIconColor: context.appTextSecondary,
        title: Text(
          question,
          style: TextStyle(
            fontWeight: FontWeight.w600,
            fontSize: 14.5,
            color: context.appTextPrimary,
          ),
        ),
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              answer,
              style: TextStyle(
                color: context.appTextSecondary,
                fontSize: 13.5,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
