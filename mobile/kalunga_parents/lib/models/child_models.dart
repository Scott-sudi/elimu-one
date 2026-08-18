import 'package:equatable/equatable.dart';

import '../config/api_config.dart';

/// Enfant lié au parent connecté (réponse `/parents/children/`).
class ChildSummary extends Equatable {
  const ChildSummary({
    required this.id,
    required this.displayName,
    required this.classLabel,
    required this.matricule,
    required this.isActive,
    this.photoUrl,
  });

  final String id;
  final String displayName;
  final String classLabel;
  final String matricule;
  final bool isActive;
  final String? photoUrl;

  /// Initiales pour avatar de secours (ex. « EM »).
  String get initials {
    final parts = displayName
        .trim()
        .split(RegExp(r'\s+'))
        .where((p) => p.isNotEmpty)
        .toList();
    if (parts.isEmpty) return '?';
    if (parts.length == 1) {
      final w = parts.first;
      return w.substring(0, w.length >= 2 ? 2 : 1).toUpperCase();
    }
    return ('${parts.first[0]}${parts[1][0]}').toUpperCase();
  }

  factory ChildSummary.fromJson(Map<String, dynamic> json) {
    return ChildSummary(
      id: json['id']?.toString() ?? '',
      displayName: json['nom']?.toString() ?? '',
      classLabel: json['classe']?.toString() ?? 'Classe non assignée',
      matricule: json['matricule']?.toString() ?? '',
      isActive: json['actif'] as bool? ?? false,
      photoUrl: ApiConfig.resolveMediaUrl(json['photo']?.toString()),
    );
  }

  @override
  List<Object?> get props => [id, displayName, classLabel, matricule, isActive];
}
