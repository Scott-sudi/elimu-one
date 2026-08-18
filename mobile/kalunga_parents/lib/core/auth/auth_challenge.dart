/// Contrat pour les défis d'authentification futurs.
///
/// Aujourd'hui : seul [PhoneAuthChallenge] est utilisé.
/// Demain : Password / Pin / Otp / Biometric sans changer AuthRepository.
library;

import 'auth_step.dart';

sealed class AuthChallenge {
  AuthMethod get method;
  AuthStep get completesStep;
}

class PhoneAuthChallenge extends AuthChallenge {
  PhoneAuthChallenge({
    required this.telephone,
    required this.numeroIdentification,
  });

  final String telephone;
  final String numeroIdentification;

  @override
  AuthMethod get method => AuthMethod.phone;

  @override
  AuthStep get completesStep => AuthStep.phone;
}

/// Stubs documentaires — non utilisés tant que l'étape n'est pas développée.
class PasswordAuthChallenge extends AuthChallenge {
  PasswordAuthChallenge(this.password);

  final String password;

  @override
  AuthMethod get method => AuthMethod.password;

  @override
  AuthStep get completesStep => AuthStep.password;
}

class PinAuthChallenge extends AuthChallenge {
  PinAuthChallenge(this.pin);

  final String pin;

  @override
  AuthMethod get method => AuthMethod.pin;

  @override
  AuthStep get completesStep => AuthStep.pin;
}

class OtpAuthChallenge extends AuthChallenge {
  OtpAuthChallenge(this.code);

  final String code;

  @override
  AuthMethod get method => AuthMethod.otp;

  @override
  AuthStep get completesStep => AuthStep.otp;
}

class BiometricAuthChallenge extends AuthChallenge {
  @override
  AuthMethod get method => AuthMethod.biometric;

  @override
  AuthStep get completesStep => AuthStep.biometric;
}
