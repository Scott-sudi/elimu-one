import 'package:equatable/equatable.dart';

/// Jetons JWT renvoyés par `/api/v1/auth/token/`.
class AuthTokens extends Equatable {
  const AuthTokens({
    required this.access,
    required this.refresh,
  });

  final String access;
  final String refresh;

  factory AuthTokens.fromJson(Map<String, dynamic> json) {
    return AuthTokens(
      access: json['access']?.toString() ?? '',
      refresh: json['refresh']?.toString() ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
        'access': access,
        'refresh': refresh,
      };

  @override
  List<Object?> get props => [access, refresh];
}
