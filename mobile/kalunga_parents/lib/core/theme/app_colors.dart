import 'package:flutter/material.dart';

/// Palette fidèle au logo ELIMU (marine + vert).
abstract final class AppColors {
  static const Color primary = Color(0xFF002858);
  static const Color primaryLight = Color(0xFF1058A0);
  static const Color accent = Color(0xFF40A040);

  /// Aligné sur le web (`--color-primary: #002858`).
  static const Color brandWeb = Color(0xFF002858);

  static const Color background = Color(0xFFF5F7FA);
  static const Color card = Color(0xFFFFFFFF);
  static const Color surface = Color(0xFFFFFFFF);

  static const Color textPrimary = Color(0xFF12151C);
  static const Color textSecondary = Color(0xFF5C6573);
  static const Color textOnPrimary = Color(0xFFFFFFFF);

  static const Color divider = Color(0xFFE8EBF0);
  static const Color badge = Color(0xFF002858);

  static const Color activityBulletin = Color(0xFF2D7A2D);
  static const Color activityMeeting = Color(0xFFE65100);
  static const Color activityFees = Color(0xFF1058A0);

  static const Color lightGreen = Color(0xFFE8EEF6);
  static const Color inactiveBadge = Color(0xFF9E9E9E);
  static const Color inactiveBadgeBg = Color(0xFFEEEEEE);

  static const Color actionPresenceBg = Color(0xFFE8F5E9);
  static const Color actionAbsenceBg = Color(0xFFFFF3E0);
  static const Color actionDisciplineBg = Color(0xFFF3E5F5);
  static const Color actionPaymentBg = Color(0xFFE8EEF6);

  static const Color shadow = Color(0x1A000000);
}
