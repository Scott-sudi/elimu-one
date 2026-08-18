import 'package:flutter/material.dart';

/// Langues supportées dans l’app parents.
enum AppLanguage {
  fr(code: 'fr', label: 'Français', locale: Locale('fr')),
  en(code: 'en', label: 'English', locale: Locale('en')),
  sw(code: 'sw', label: 'Kiswahili', locale: Locale('sw'));

  const AppLanguage({
    required this.code,
    required this.label,
    required this.locale,
  });

  final String code;
  final String label;
  final Locale locale;

  /// Locale Material (sw n'a pas encore de bundle Material complet).
  Locale get materialLocale => switch (this) {
        AppLanguage.sw => const Locale('en'),
        _ => locale,
      };

  static AppLanguage fromCode(String? raw) {
    return AppLanguage.values.firstWhere(
      (e) => e.code == raw,
      orElse: () => AppLanguage.fr,
    );
  }
}
