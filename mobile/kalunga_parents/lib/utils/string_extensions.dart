/// Utilitaires UI / formatage (extensions futures).
library;

extension StringX on String {
  String get capitalizeFirst {
    if (isEmpty) return this;
    return '${this[0].toUpperCase()}${substring(1)}';
  }
}
