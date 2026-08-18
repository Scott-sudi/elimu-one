import 'package:flutter/material.dart';

import 'app_colors.dart';

/// Couleurs UI qui suivent le thème clair / sombre actif.
extension AppThemeColors on BuildContext {
  bool get isDarkTheme => Theme.of(this).brightness == Brightness.dark;

  Color get appBackground =>
      isDarkTheme ? const Color(0xFF121412) : AppColors.background;

  Color get appCard =>
      isDarkTheme ? const Color(0xFF1C211D) : AppColors.card;

  Color get appTextPrimary =>
      isDarkTheme ? const Color(0xFFF1F3F1) : AppColors.textPrimary;

  Color get appTextSecondary =>
      isDarkTheme ? const Color(0xFFA7B0A9) : AppColors.textSecondary;

  Color get appDivider =>
      isDarkTheme ? const Color(0xFF2C332E) : AppColors.divider;

  Color get appPrimary =>
      isDarkTheme ? AppColors.accent : AppColors.primary;

  Color get appPrimaryLight =>
      isDarkTheme ? AppColors.accent : AppColors.primaryLight;

  Color get appAvatarBg =>
      isDarkTheme ? const Color(0xFF243028) : AppColors.lightGreen;
}
