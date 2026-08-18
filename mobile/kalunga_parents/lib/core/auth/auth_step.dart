/// Étapes du parcours d'authentification parents.
///
/// Seule [AuthStep.phone] est active aujourd'hui.
/// Les autres valeurs préparent password / PIN / OTP / biométrie
/// sans implémentation UI pour l'instant.
enum AuthStep {
  /// Vérification du numéro de téléphone (étape actuelle).
  phone,

  /// Mot de passe (à venir).
  password,

  /// Code PIN (à venir).
  pin,

  /// OTP SMS (à venir).
  otp,

  /// Empreinte / Face ID (à venir).
  biometric,

  /// Parcours terminé — accès à l'application.
  completed,
}

/// Méthodes d'authentification futures (contrat stable pour l'UI).
enum AuthMethod {
  phone,
  password,
  pin,
  otp,
  biometric,
}

extension AuthStepX on AuthStep {
  static AuthStep fromApi(String? raw) {
    switch (raw) {
      case 'password':
        return AuthStep.password;
      case 'pin':
        return AuthStep.pin;
      case 'otp':
        return AuthStep.otp;
      case 'biometric':
        return AuthStep.biometric;
      case 'completed':
        return AuthStep.completed;
      case 'phone':
      default:
        return AuthStep.phone;
    }
  }

  String get apiValue => name;
}
