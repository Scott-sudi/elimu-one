import 'package:equatable/equatable.dart';

/// Profil utilisateur aligné sur [UserSerializer] Django.
class UserModel extends Equatable {
  const UserModel({
    required this.publicId,
    required this.username,
    this.email,
    this.nom,
    this.postnom,
    this.prenom,
    this.fullName,
    this.sexe,
    this.telephone,
    this.roleCode,
    this.roleName,
    this.isActive = true,
    this.mustChangePassword = false,
  });

  final String publicId;
  final String username;
  final String? email;
  final String? nom;
  final String? postnom;
  final String? prenom;
  final String? fullName;
  final String? sexe;
  final String? telephone;
  final String? roleCode;
  final String? roleName;
  final bool isActive;
  final bool mustChangePassword;

  /// Nom affiché dans l'AppBar (ex. « Jean KABASELE »).
  String get displayName {
    if (fullName != null && fullName!.trim().isNotEmpty) {
      return fullName!.trim();
    }
    final parts = <String>[
      if (prenom != null && prenom!.isNotEmpty) prenom!,
      if (nom != null && nom!.isNotEmpty) nom!.toUpperCase(),
    ];
    if (parts.isNotEmpty) return parts.join(' ');
    return username;
  }

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      publicId: json['public_id']?.toString() ?? '',
      username: json['username']?.toString() ?? '',
      email: json['email']?.toString(),
      nom: json['nom']?.toString(),
      postnom: json['postnom']?.toString(),
      prenom: json['prenom']?.toString(),
      fullName: json['full_name']?.toString(),
      sexe: json['sexe']?.toString(),
      telephone: json['telephone']?.toString(),
      roleCode: json['role_code']?.toString(),
      roleName: json['role_name']?.toString(),
      isActive: json['is_active'] as bool? ?? true,
      mustChangePassword: json['must_change_password'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
        'public_id': publicId,
        'username': username,
        'email': email,
        'nom': nom,
        'postnom': postnom,
        'prenom': prenom,
        'full_name': fullName,
        'sexe': sexe,
        'telephone': telephone,
        'role_code': roleCode,
        'role_name': roleName,
        'is_active': isActive,
        'must_change_password': mustChangePassword,
      };

  @override
  List<Object?> get props => [publicId, username, fullName, roleCode];
}
