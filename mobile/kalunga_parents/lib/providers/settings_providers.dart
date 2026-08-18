import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/l10n/app_language.dart';
import '../core/l10n/app_strings.dart';
import '../models/parent_profile.dart';
import '../repositories/profile_repository.dart';
import '../services/profile_service.dart';
import 'auth_providers.dart';
import 'dependency_providers.dart';

export '../core/l10n/app_language.dart';

abstract final class SettingsKeys {
  static const language = 'kalunga_app_language';
  static const themeMode = 'kalunga_app_theme_mode';
}

class AppLanguageNotifier extends StateNotifier<AppLanguage> {
  AppLanguageNotifier() : super(AppLanguage.fr) {
    _restore();
  }

  Future<void> _restore() async {
    final prefs = await SharedPreferences.getInstance();
    state = AppLanguage.fromCode(prefs.getString(SettingsKeys.language));
  }

  Future<void> setLanguage(AppLanguage language) async {
    state = language;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(SettingsKeys.language, language.code);
  }
}

final appLanguageProvider =
    StateNotifierProvider<AppLanguageNotifier, AppLanguage>((ref) {
  return AppLanguageNotifier();
});

final appStringsProvider = Provider<AppStrings>((ref) {
  return AppStrings.of(ref.watch(appLanguageProvider));
});

class ThemeModeNotifier extends StateNotifier<ThemeMode> {
  ThemeModeNotifier() : super(ThemeMode.light) {
    _restore();
  }

  Future<void> _restore() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(SettingsKeys.themeMode);
    state = switch (raw) {
      'dark' => ThemeMode.dark,
      'system' => ThemeMode.system,
      _ => ThemeMode.light,
    };
  }

  Future<void> setThemeMode(ThemeMode mode) async {
    state = mode;
    final prefs = await SharedPreferences.getInstance();
    final value = switch (mode) {
      ThemeMode.dark => 'dark',
      ThemeMode.system => 'system',
      ThemeMode.light => 'light',
    };
    await prefs.setString(SettingsKeys.themeMode, value);
  }
}

final themeModeProvider =
    StateNotifierProvider<ThemeModeNotifier, ThemeMode>((ref) {
  return ThemeModeNotifier();
});

final profileRepositoryProvider = Provider<ProfileRepository>((ref) {
  return ProfileRepository(
    profileService: ProfileService(api: ref.watch(apiServiceProvider)),
    authService: ref.watch(authServiceProvider),
  );
});

final parentProfileProvider = FutureProvider<ParentProfile>((ref) async {
  ref.watch(authSessionProvider);
  return ref.watch(profileRepositoryProvider).loadProfile();
});