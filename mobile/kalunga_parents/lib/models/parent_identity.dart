import 'package:equatable/equatable.dart';

import '../core/auth/auth_step.dart';

/// Identité parent reconnue après vérification téléphone (Guardian Django).
class ParentIdentity extends Equatable {
  const ParentIdentity({
    required this.guardianPublicId,
    required this.displayName,
    required this.phone,
    this.email = '',
    this.nextAuthStep = AuthStep.password,
    this.availableMethods = const [
      AuthMethod.password,
      AuthMethod.pin,
      AuthMethod.otp,
      AuthMethod.biometric,
    ],
  });

  final String guardianPublicId;
  final String displayName;
  final String phone;
  final String email;
  final AuthStep nextAuthStep;
  final List<AuthMethod> availableMethods;

  factory ParentIdentity.fromVerifyJson(
    Map<String, dynamic> json, {
    required String phone,
  }) {
    final methodsRaw = json['available_auth_methods'];
    final methods = <AuthMethod>[];
    if (methodsRaw is List) {
      for (final item in methodsRaw) {
        switch (item.toString()) {
          case 'password':
            methods.add(AuthMethod.password);
          case 'pin':
            methods.add(AuthMethod.pin);
          case 'otp':
            methods.add(AuthMethod.otp);
          case 'biometric':
            methods.add(AuthMethod.biometric);
        }
      }
    }

    return ParentIdentity(
      guardianPublicId: json['guardian_public_id']?.toString() ?? '',
      displayName: json['display_name']?.toString() ?? '',
      phone: phone,
      email: json['email']?.toString() ?? '',
      nextAuthStep: AuthStepX.fromApi(json['next_auth_step']?.toString()),
      availableMethods: methods.isEmpty
          ? const [
              AuthMethod.password,
              AuthMethod.pin,
              AuthMethod.otp,
              AuthMethod.biometric,
            ]
          : methods,
    );
  }

  Map<String, String> toStorageMap() => {
        'guardian_public_id': guardianPublicId,
        'display_name': displayName,
        'phone': phone,
        'email': email,
        'next_auth_step': nextAuthStep.apiValue,
      };

  factory ParentIdentity.fromStorageMap(Map<String, String> map) {
    return ParentIdentity(
      guardianPublicId: map['guardian_public_id'] ?? '',
      displayName: map['display_name'] ?? '',
      phone: map['phone'] ?? '',
      email: map['email'] ?? '',
      nextAuthStep: AuthStepX.fromApi(map['next_auth_step']),
    );
  }

  ParentIdentity copyWith({
    String? guardianPublicId,
    String? displayName,
    String? phone,
    String? email,
    AuthStep? nextAuthStep,
    List<AuthMethod>? availableMethods,
  }) {
    return ParentIdentity(
      guardianPublicId: guardianPublicId ?? this.guardianPublicId,
      displayName: displayName ?? this.displayName,
      phone: phone ?? this.phone,
      email: email ?? this.email,
      nextAuthStep: nextAuthStep ?? this.nextAuthStep,
      availableMethods: availableMethods ?? this.availableMethods,
    );
  }

  @override
  List<Object?> get props => [guardianPublicId, displayName, phone, email];
}

/// Résultat de la vérification téléphone (sans lever d'exception métier).
class PhoneVerificationResult extends Equatable {
  const PhoneVerificationResult._({
    required this.recognized,
    this.identity,
    this.message = '',
  });

  const PhoneVerificationResult.recognized(ParentIdentity identity)
      : this._(recognized: true, identity: identity);

  const PhoneVerificationResult.unknown({
    String message = "Ce numéro n'est associé à aucun compte parent.",
  }) : this._(recognized: false, message: message);

  final bool recognized;
  final ParentIdentity? identity;
  final String message;

  @override
  List<Object?> get props => [recognized, identity, message];
}
