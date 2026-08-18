import 'package:flutter/material.dart';

import '../../models/notification_models.dart';
import 'communication_detail_screen.dart';
import 'discipline_detail_screen.dart';
import 'payment_receipt_screen.dart';

/// Ouvre l'écran de détail adapté à la source de la notification.
Future<void> openNotificationDetail(
  BuildContext context,
  ParentNotificationItem item,
) async {
  final id = item.resolvedSourceId;
  if (id.isEmpty) return;

  final Widget screen;
  switch (item.source) {
    case 'finance_payment':
      screen = PaymentReceiptScreen(publicId: id);
    case 'secretariat_communication':
      screen = CommunicationDetailScreen(publicId: id);
    case 'discipline_summons':
      screen = DisciplineDetailScreen(kind: 'summons', publicId: id);
    case 'discipline_incident':
      screen = DisciplineDetailScreen(kind: 'incident', publicId: id);
    case 'discipline_attendance':
      screen = DisciplineDetailScreen(kind: 'attendance', publicId: id);
    case 'discipline_measure':
      screen = DisciplineDetailScreen(kind: 'measure', publicId: id);
    case 'discipline_exit':
      screen = DisciplineDetailScreen(kind: 'exit', publicId: id);
    case 'discipline_justification':
      screen = DisciplineDetailScreen(kind: 'justification', publicId: id);
    default:
      // Repli : message générique avec le body déjà chargé.
      screen = _GenericNotificationDetailScreen(item: item);
  }

  await Navigator.of(context).push(
    MaterialPageRoute(builder: (_) => screen),
  );
}

class _GenericNotificationDetailScreen extends StatelessWidget {
  const _GenericNotificationDetailScreen({required this.item});

  final ParentNotificationItem item;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(item.title)),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            item.title,
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 8),
          if (item.subtitle.isNotEmpty) Text(item.subtitle),
          const SizedBox(height: 8),
          if (item.timestampLabel.isNotEmpty) Text(item.timestampLabel),
          const SizedBox(height: 16),
          Text(item.body.isEmpty ? 'Aucun détail supplémentaire.' : item.body),
        ],
      ),
    );
  }
}
