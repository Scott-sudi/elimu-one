import '../core/auth/auth_challenge.dart';
import '../core/auth/auth_step.dart';
import '../models/auth_tokens.dart';
import '../models/parent_identity.dart';
import '../models/user_model.dart';
import '../services/auth_service.dart';
import '../services/login_service.dart';
import '../services/phone_auth_service.dart';
import '../services/user_service.dart';

/// Orchestration auth parents — extensible sans casser l'UI.
///
/// Aujourd'hui : [PhoneAuthChallenge] uniquement.
/// Demain : brancher password / PIN / OTP / biométrie via [submitChallenge].
class AuthRepository {
  AuthRepository({
    required PhoneAuthService phoneAuthService,
    required LoginService loginService,
    required AuthService authService,
    required UserService userService,
  })  : _phoneAuth = phoneAuthService,
        _login = loginService,
        _auth = authService,
        _users = userService;

  final PhoneAuthService _phoneAuth;
  final LoginService _login;
  final AuthService _auth;
  final UserService _users;

  Future<bool> hasSession() => _auth.hasSession();

  Future<bool> hasJwtSession() => _auth.hasJwtSession();

  Future<ParentIdentity?> currentParentSession() =>
      _auth.readParentSession();

  /// Point d'entrée unique pour les défis d'auth (stratégie par type).
  Future<AuthChallengeOutcome> submitChallenge(AuthChallenge challenge) async {
    switch (challenge) {
      case PhoneAuthChallenge(
          :final telephone,
          :final numeroIdentification,
        ):
        return _handlePhone(
          telephone: telephone,
          numeroIdentification: numeroIdentification,
        );
      case PasswordAuthChallenge():
      case PinAuthChallenge():
      case OtpAuthChallenge():
      case BiometricAuthChallenge():
        return const AuthChallengeOutcome.notImplemented();
    }
  }

  Future<AuthChallengeOutcome> _handlePhone({
    required String telephone,
    required String numeroIdentification,
  }) async {
    final result = await _phoneAuth.verifyCredentials(
      telephone: telephone,
      numeroIdentification: numeroIdentification,
    );
    if (!result.recognized || result.identity == null) {
      return AuthChallengeOutcome.rejected(
        message: result.message,
        step: AuthStep.phone,
      );
    }

    await _auth.persistPhoneVerifiedSession(result.identity!);

    return AuthChallengeOutcome.completed(identity: result.identity!);
  }

  Future<AuthTokens> loginWithPassword({
    required String username,
    required String password,
  }) {
    return _login.login(username: username, password: password);
  }

  Future<UserModel> currentUser() => _users.fetchCurrentUser();

  Future<void> persistParentIdentity(ParentIdentity identity) =>
      _auth.persistPhoneVerifiedSession(identity);

  Future<void> logout() => _auth.logout();
}

/// Résultat d'un défi d'authentification (pour l'UI).
sealed class AuthChallengeOutcome {
  const AuthChallengeOutcome();

  const factory AuthChallengeOutcome.completed({
    required ParentIdentity identity,
  }) = AuthChallengeCompleted;

  const factory AuthChallengeOutcome.nextStep({
    required ParentIdentity identity,
    required AuthStep nextStep,
  }) = AuthChallengeNextStep;

  const factory AuthChallengeOutcome.rejected({
    required String message,
    required AuthStep step,
  }) = AuthChallengeRejected;

  const factory AuthChallengeOutcome.notImplemented() =
      AuthChallengeNotImplemented;
}

class AuthChallengeCompleted extends AuthChallengeOutcome {
  const AuthChallengeCompleted({required this.identity});

  final ParentIdentity identity;
}

class AuthChallengeNextStep extends AuthChallengeOutcome {
  const AuthChallengeNextStep({
    required this.identity,
    required this.nextStep,
  });

  final ParentIdentity identity;
  final AuthStep nextStep;
}

class AuthChallengeRejected extends AuthChallengeOutcome {
  const AuthChallengeRejected({
    required this.message,
    required this.step,
  });

  final String message;
  final AuthStep step;
}

class AuthChallengeNotImplemented extends AuthChallengeOutcome {
  const AuthChallengeNotImplemented();
}
