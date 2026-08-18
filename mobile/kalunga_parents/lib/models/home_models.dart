import 'package:equatable/equatable.dart';
import 'package:flutter/material.dart';

/// Résumé « Vue d'ensemble » de la page Accueil.
class HomeOverview extends Equatable {
  const HomeOverview({
    required this.schoolYearLabel,
    required this.childrenCount,
    required this.notificationsCount,
    required this.unpaidBalanceLabel,
    this.paidBalanceLabel = 'Aucun',
    this.generalAveragePercent,
    this.unreadNotificationsBadge = 0,
  });

  final String schoolYearLabel;
  final int childrenCount;
  final int notificationsCount;
  /// Conservé pour compat ; l’UI affiche désormais [paidBalanceLabel].
  final int? generalAveragePercent;
  final String paidBalanceLabel;
  final String unpaidBalanceLabel;
  final int unreadNotificationsBadge;

  factory HomeOverview.fromJson(Map<String, dynamic> json) {
    final averageRaw = json['general_average_percent'];
    int? average;
    if (averageRaw is num) {
      average = averageRaw.round();
    }
    return HomeOverview(
      schoolYearLabel: json['school_year_label']?.toString() ?? '',
      childrenCount: json['children_count'] as int? ?? 0,
      notificationsCount: json['notifications_count'] as int? ?? 0,
      generalAveragePercent: average,
      paidBalanceLabel: json['paid_balance_label']?.toString() ?? 'Aucun',
      unpaidBalanceLabel: json['unpaid_balance_label']?.toString() ?? 'Aucun',
      unreadNotificationsBadge: json['unread_notifications_badge'] as int? ?? 0,
    );
  }

  @override
  List<Object?> get props => [
        schoolYearLabel,
        childrenCount,
        notificationsCount,
        generalAveragePercent,
        paidBalanceLabel,
        unpaidBalanceLabel,
        unreadNotificationsBadge,
      ];
}

/// Type d'activité récente (détermine couleur / icône).
enum ActivityType { bulletin, meeting, fees, info }

/// Élément de la liste « Activités récentes ».
class RecentActivity extends Equatable {
  const RecentActivity({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.timestampLabel,
    required this.type,
    this.body = '',
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
  final String source;
  final String sourceId;
  final DateTime? occurredAt;

  IconData get icon {
    switch (type) {
      case ActivityType.bulletin:
        return Icons.assignment_outlined;
      case ActivityType.meeting:
        return Icons.calendar_today_outlined;
      case ActivityType.fees:
        return Icons.info_outline;
      case ActivityType.info:
        return Icons.notifications_none_outlined;
    }
  }

  factory RecentActivity.fromJson(Map<String, dynamic> json) {
    DateTime? occurred;
    final rawOccurred = json['occurred_at']?.toString();
    if (rawOccurred != null && rawOccurred.isNotEmpty) {
      occurred = DateTime.tryParse(rawOccurred)?.toLocal();
    }
    return RecentActivity(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      subtitle: json['subtitle']?.toString() ?? '',
      timestampLabel: json['timestamp_label']?.toString() ?? '',
      type: _parseType(json['type']?.toString()),
      body: json['body']?.toString() ?? '',
      source: json['source']?.toString() ?? '',
      sourceId: json['source_id']?.toString() ?? '',
      occurredAt: occurred,
    );
  }

  static ActivityType _parseType(String? raw) {
    switch (raw) {
      case 'bulletin':
        return ActivityType.bulletin;
      case 'meeting':
        return ActivityType.meeting;
      case 'fees':
        return ActivityType.fees;
      default:
        return ActivityType.info;
    }
  }

  @override
  List<Object?> get props => [
        id,
        title,
        subtitle,
        timestampLabel,
        type,
        body,
        source,
        sourceId,
        occurredAt,
      ];
}

/// Agrégat Accueil (parent connecté + vue d'ensemble + activités).
class HomeDashboard extends Equatable {
  const HomeDashboard({
    required this.parentDisplayName,
    required this.overview,
    required this.activities,
  });

  final String parentDisplayName;
  final HomeOverview overview;
  final List<RecentActivity> activities;

  @override
  List<Object?> get props => [parentDisplayName, overview, activities];
}
