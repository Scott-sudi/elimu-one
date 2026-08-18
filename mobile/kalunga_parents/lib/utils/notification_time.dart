/// Affiche la date/heure selon l'horloge du téléphone.
String notificationTimeLabel(DateTime? occurred, [String fallback = '']) {
  if (occurred == null) return fallback;
  final local = occurred.toLocal();
  final now = DateTime.now();
  final today = DateTime(now.year, now.month, now.day);
  final day = DateTime(local.year, local.month, local.day);
  final clock =
      '${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
  final delta = today.difference(day).inDays;
  if (delta <= 0) return "Aujourd'hui, $clock";
  if (delta == 1) return 'Hier, $clock';
  final d = day.day.toString().padLeft(2, '0');
  final m = day.month.toString().padLeft(2, '0');
  return '$d/$m/${day.year} $clock';
}
