import 'package:equatable/equatable.dart';

/// Fiche identité responsable (API parents/profile/).
class ParentProfile extends Equatable {
  const ParentProfile({
    required this.guardianPublicId,
    required this.displayName,
    this.prenom = '',
    this.nom = '',
    this.postnom = '',
    this.sexe = '',
    this.telephone = '',
    this.telephoneSecondaire = '',
    this.email = '',
    this.adresse = '',
    this.profession = '',
    this.numeroIdentification = '',
  });

  final String guardianPublicId;
  final String displayName;
  final String prenom;
  final String nom;
  final String postnom;
  final String sexe;
  final String telephone;
  final String telephoneSecondaire;
  final String email;
  final String adresse;
  final String profession;
  final String numeroIdentification;

  factory ParentProfile.fromJson(Map<String, dynamic> json) {
    return ParentProfile(
      guardianPublicId: json['guardian_public_id']?.toString() ?? '',
      displayName: json['display_name']?.toString() ?? '',
      prenom: json['prenom']?.toString() ?? '',
      nom: json['nom']?.toString() ?? '',
      postnom: json['postnom']?.toString() ?? '',
      sexe: json['sexe']?.toString() ?? '',
      telephone: json['telephone']?.toString() ?? '',
      telephoneSecondaire: json['telephone_secondaire']?.toString() ?? '',
      email: json['email']?.toString() ?? '',
      adresse: json['adresse']?.toString() ?? '',
      profession: json['profession']?.toString() ?? '',
      numeroIdentification: json['numero_identification']?.toString() ?? '',
    );
  }

  factory ParentProfile.fromSession({
    required String guardianPublicId,
    required String displayName,
    required String phone,
    required String email,
  }) {
    return ParentProfile(
      guardianPublicId: guardianPublicId,
      displayName: displayName,
      telephone: phone,
      email: email,
    );
  }

  @override
  List<Object?> get props => [guardianPublicId, displayName, telephone, email];
}
