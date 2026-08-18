import 'package:equatable/equatable.dart';
import 'package:flutter/material.dart';

import '../core/theme/app_colors.dart';
import '../utils/notification_sort.dart';
import 'home_models.dart';

/// Élément de l'inbox Notifications (finance / secrétariat / discipline).
class ParentNotificationItem extends Equatable {
  const ParentNotificationItem({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.timestampLabel,
    required this.type,
    this.body = '',
    this.isRead = true,
    this.studentId = '',
    this.studentName = '',
    this.source = '',
    this.sourceId = '',
    this.occurredAt,
  });

  final String id;
  final String title;
  final String subtitle;
  final String timestampLabel;
  final ActivityType type;
  final String body;
  final bool isRead;
  final String studentId;
  final String studentName;
  final String source;
  final String sourceId;

  /// Instant réel pour tri (plus récent en haut).
  final DateTime? occurredAt;

  /// UUID métier extrait de `source_id` ou de `id` (`payment:uuid`).
  String get resolvedSourceId {
    if (sourceId.trim().isNotEmpty) return sourceId.trim();
    final parts = id.split(':');
    if (parts.length >= 2) return parts.sublist(1).join(':');
    return id;
  }

  /// Filtre maquette : toutes / generales / scolaires / financieres.
  String get filterBucket {
    switch (source) {
      case 'finance_payment':
        return 'financieres';
      case 'discipline_summons':
      case 'discipline_incident':
      case 'discipline_attendance':
      case 'discipline_measure':
      case 'discipline_exit':
      case 'discipline_justification':
        // Présence, convocations, incidents → onglet Scolaires.
        return 'scolaires';
      case 'secretariat_communication':
        return type == ActivityType.bulletin ? 'scolaires' : 'generales';
      default:
        if (source.startsWith('discipline_')) return 'scolaires';
        if (type == ActivityType.fees) return 'financieres';
        if (type == ActivityType.meeting || type == ActivityType.bulletin) {
          return 'scolaires';
        }
        return 'generales';
    }
  }

  Color get iconBackground {
    switch (type) {
      case ActivityType.bulletin:
        return AppColors.activityBulletin;
      case ActivityType.meeting:
        return AppColors.activityMeeting;
      case ActivityType.fees:
        return AppColors.activityFees;
      case ActivityType.info:
        if (source == 'discipline_attendance') {
          return const Color(0xFF2E7D32);
        }
        if (source == 'discipline_exit') {
          return const Color(0xFF1565C0);
        }
        if (source == 'discipline_justification') {
          return const Color(0xFF6A1B9A);
        }
        if (source == 'discipline_measure') {
          return const Color(0xFFEF6C00);
        }
        return source.startsWith('discipline')
            ? const Color(0xFFC62828)
            : AppColors.primaryLight;
    }
  }

  IconData get icon {
    switch (source) {
      case 'finance_payment':
        return Icons.check_circle_outline;
      case 'discipline_summons':
        return Icons.campaign_outlined;
      case 'discipline_incident':
        return Icons.warning_amber_rounded;
      case 'discipline_attendance':
        return Icons.how_to_reg_outlined;
      case 'discipline_measure':
        return Icons.gavel_outlined;
      case 'discipline_exit':
        return Icons.exit_to_app_outlined;
      case 'discipline_justification':
        return Icons.fact_check_outlined;
      case 'secretariat_communication':
        return type == ActivityType.bulletin
            ? Icons.description_outlined
            : Icons.info_outline;
      default:
        switch (type) {
          case ActivityType.bulletin:
            return Icons.description_outlined;
          case ActivityType.meeting:
            return Icons.campaign_outlined;
          case ActivityType.fees:
            return Icons.check_circle_outline;
          case ActivityType.info:
            return Icons.info_outline;
        }
    }
  }

  RecentActivity get asActivity => RecentActivity(
        id: id,
        title: title,
        subtitle: subtitle,
        timestampLabel: timestampLabel,
        type: type,
        body: body,
        source: source,
        sourceId: sourceId,
        occurredAt: occurredAt,
      );

  /// Depuis une activité Accueil (même source que l’inbox Notifications).
  factory ParentNotificationItem.fromRecentActivity(RecentActivity activity) {
    return ParentNotificationItem(
      id: activity.id,
      title: activity.title,
      subtitle: activity.subtitle,
      timestampLabel: activity.timestampLabel,
      type: activity.type,
      body: activity.body.isNotEmpty ? activity.body : activity.subtitle,
      source: activity.source,
      sourceId: activity.sourceId,
      occurredAt: activity.occurredAt,
    );
  }

  factory ParentNotificationItem.fromJson(Map<String, dynamic> json) {
    DateTime? occurred;
    final rawOccurred = json['occurred_at']?.toString();
    if (rawOccurred != null && rawOccurred.isNotEmpty) {
      occurred = DateTime.tryParse(rawOccurred)?.toLocal();
    }
    return ParentNotificationItem(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      subtitle: json['subtitle']?.toString() ?? '',
      timestampLabel: json['timestamp_label']?.toString() ?? '',
      type: RecentActivity.fromJson({
        'id': json['id'],
        'title': json['title'],
        'subtitle': json['subtitle'],
        'timestamp_label': json['timestamp_label'],
        'type': json['type'],
      }).type,
      body: json['body']?.toString() ?? '',
      isRead: json['is_read'] as bool? ?? true,
      studentId: json['student_id']?.toString() ?? '',
      studentName: json['student_name']?.toString() ?? '',
      source: json['source']?.toString() ?? '',
      sourceId: json['source_id']?.toString() ?? '',
      occurredAt: occurred,
    );
  }

  @override
  List<Object?> get props => [id, title, isRead, type, sourceId, occurredAt];
}

class ParentNotificationsResult extends Equatable {
  const ParentNotificationsResult({
    required this.items,
    this.unreadCount = 0,
    this.totalCount = 0,
  });

  final List<ParentNotificationItem> items;
  final int unreadCount;
  final int totalCount;

  factory ParentNotificationsResult.fromJson(Map<String, dynamic> json) {
    final raw = json['items'] as List<dynamic>? ?? const [];
    final items = raw
        .map(
          (e) => ParentNotificationItem.fromJson(
            Map<String, dynamic>.from(e as Map),
          ),
        )
        .toList();
    // Filet de sécurité : plus récent en haut (jamais par titre).
    sortParentNotificationsNewestFirst(items);
    return ParentNotificationsResult(
      unreadCount: int.tryParse(json['unread_count']?.toString() ?? '') ?? 0,
      totalCount: int.tryParse(json['total_count']?.toString() ?? '') ?? 0,
      items: items,
    );
  }

  @override
  List<Object?> get props => [items, unreadCount, totalCount];
}
