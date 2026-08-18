import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme_colors.dart';
import '../../models/notification_detail_models.dart';
import '../../providers/dependency_providers.dart';
import '../../providers/home_providers.dart';
import '../../providers/notifications_providers.dart';

/// Détail d'un message secrétariat.
class CommunicationDetailScreen extends ConsumerStatefulWidget {
  const CommunicationDetailScreen({super.key, required this.publicId});

  final String publicId;

  @override
  ConsumerState<CommunicationDetailScreen> createState() =>
      _CommunicationDetailScreenState();
}

class _CommunicationDetailScreenState
    extends ConsumerState<CommunicationDetailScreen> {
  late final Future<CommunicationDetail> _future;
  var _refreshed = false;

  @override
  void initState() {
    super.initState();
    _future = ref
        .read(notificationDetailServiceProvider)
        .fetchCommunication(widget.publicId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: context.appBackground,
      appBar: AppBar(
        title: const Text('Message'),
        backgroundColor: context.appCard,
        foregroundColor: context.appTextPrimary,
        elevation: 0,
      ),
      body: FutureBuilder<CommunicationDetail>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return Center(
              child: CircularProgressIndicator(color: context.appPrimary),
            );
          }
          if (snapshot.hasError || snapshot.data == null) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  snapshot.error?.toString() ?? 'Impossible de charger le message.',
                  textAlign: TextAlign.center,
                ),
              ),
            );
          }
          final d = snapshot.data!;
          if (!_refreshed) {
            _refreshed = true;
            WidgetsBinding.instance.addPostFrameCallback((_) {
              ref.invalidate(parentNotificationsProvider);
              ref.invalidate(homeDashboardProvider);
            });
          }

          final meta = [
            if (d.categoryLabel.isNotEmpty) d.categoryLabel,
            if (d.priorityLabel.isNotEmpty) d.priorityLabel,
            if (d.studentName.isNotEmpty) d.studentName,
            if (d.publishedLabel.isNotEmpty) d.publishedLabel,
          ].join(' · ');

          return ListView(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
            children: [
              Text(
                d.title,
                style: TextStyle(
                  color: context.appTextPrimary,
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  height: 1.25,
                ),
              ),
              if (meta.isNotEmpty) ...[
                const SizedBox(height: 10),
                Text(
                  meta,
                  style: TextStyle(
                    color: context.appTextSecondary,
                    fontSize: 13,
                  ),
                ),
              ],
              const SizedBox(height: 18),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: context.appCard,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: context.appDivider),
                ),
                child: Text(
                  d.content.isEmpty ? 'Aucun contenu.' : d.content,
                  style: TextStyle(
                    color: context.appTextPrimary,
                    fontSize: 15.5,
                    height: 1.5,
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
