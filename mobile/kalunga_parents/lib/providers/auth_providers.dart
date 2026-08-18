import 'package:equatable/equatable.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/auth/auth_challenge.dart';
import '../models/parent_identity.dart';
import '../repositories/auth_repository.dart';
import '../services/phone_auth_service.dart';
import 'dependency_providers.dart';

/// État d'authentification de l'application.
sealed class AuthSessionState extends Equatable {
  const AuthSessionState();

  @override
  List<Object?> get props => [];
}

class AuthSessionUnknown extends AuthSessionState {
  const AuthSessionUnknown();
}

class AuthSessionLoading extends AuthSessionState {
  const AuthSessionLoading();
}

class AuthSessionUnauthenticated extends AuthSessionState {
  const AuthSessionUnauthenticated();
}

class AuthSessionAuthenticated extends AuthSessionState {
  const AuthSessionAuthenticated(this.identity);

  final ParentIdentity identity;

  @override
  List<Object?> get props => [identity];
}

class AuthSessionNotifier extends StateNotifier<AuthSessionState> {
  AuthSessionNotifier(this._repository) : super(const AuthSessionUnknown()) {
    restore();
  }

  final AuthRepository _repository;

  Future<void> restore() async {
    state = const AuthSessionLoading();
    try {
      final identity = await _repository
          .currentParentSession()
          .timeout(const Duration(seconds: 3));
      if (identity != null) {
        state = AuthSessionAuthenticated(identity);
        return;
      }
      final hasJwt = await _repository
          .hasJwtSession()
          .timeout(const Duration(seconds: 2));
      if (hasJwt) {
        state = const AuthSessionAuthenticated(
          ParentIdentity(
            guardianPublicId: '',
            displayName: '',
            phone: '',
          ),
        );
        return;
      }
      state = const AuthSessionUnauthenticated();
    } catch (_) {
      // Timeout / erreur stockage → écran de connexion (jamais bloquer).
      state = const AuthSessionUnauthenticated();
    }
  }

  /// Vérifie téléphone + n° d'identification puis ouvre la session si OK.
  ///
  /// Retourne un message d'échec utilisateur, ou `null` en cas de succès.
  Future<String?> continueWithCredentials({
    required String telephone,
    required String numeroIdentification,
  }) async {
    try {
      final outcome = await _repository.submitChallenge(
        PhoneAuthChallenge(
          telephone: telephone,
          numeroIdentification: numeroIdentification,
        ),
      );

      switch (outcome) {
        case AuthChallengeCompleted(:final identity):
          state = AuthSessionAuthenticated(identity);
          return null;
        case AuthChallengeNextStep(:final identity):
          state = AuthSessionAuthenticated(identity);
          return null;
        case AuthChallengeRejected(:final message):
          return message;
        case AuthChallengeNotImplemented():
          return 'Cette étape de connexion n’est pas encore disponible.';
      }
    } on PhoneValidationException catch (e) {
      return e.message;
    } on PhoneNetworkException catch (e) {
      return e.message;
    } catch (_) {
      return 'Impossible de vérifier vos identifiants. Réessayez plus tard.';
    }
  }

  Future<void> logout() async {
    await _repository.logout();
    state = const AuthSessionUnauthenticated();
  }

  /// Met à jour le nom affiché (ex. après refresh Accueil depuis Django).
  Future<void> syncDisplayName(String displayName) async {
    final trimmed = displayName.trim();
    if (trimmed.isEmpty) return;
    final current = state;
    if (current is! AuthSessionAuthenticated) return;
    if (current.identity.displayName == trimmed) return;
    final updated = current.identity.copyWith(displayName: trimmed);
    await _repository.persistParentIdentity(updated);
    state = AuthSessionAuthenticated(updated);
  }
}

final authSessionProvider =
    StateNotifierProvider<AuthSessionNotifier, AuthSessionState>((ref) {
  return AuthSessionNotifier(ref.watch(authRepositoryProvider));
});
