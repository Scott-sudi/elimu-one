import 'package:equatable/equatable.dart';

import '../config/api_config.dart';

/// Jour de présence / absence.
class AttendanceDay extends Equatable {
  const AttendanceDay({
    required this.id,
    required this.dateLabel,
    required this.statusLabel,
    this.note = '',
  });

  final String id;
  final String dateLabel;
  final String statusLabel;
  final String note;

  factory AttendanceDay.fromJson(Map<String, dynamic> json) {
    return AttendanceDay(
      id: json['id']?.toString() ?? '',
      dateLabel: json['date_label']?.toString() ?? '',
      statusLabel: json['status_label']?.toString() ?? '',
      note: json['note']?.toString() ?? '',
    );
  }

  @override
  List<Object?> get props => [id, dateLabel, statusLabel];
}

class AttendanceListResult extends Equatable {
  const AttendanceListResult({
    required this.studentName,
    required this.kind,
    required this.days,
    this.schoolYearLabel = '',
  });

  final String studentName;
  final String kind;
  final String schoolYearLabel;
  final List<AttendanceDay> days;

  factory AttendanceListResult.fromJson(Map<String, dynamic> json) {
    final raw = json['jours'] as List<dynamic>? ?? const [];
    return AttendanceListResult(
      studentName: json['student_name']?.toString() ?? '',
      kind: json['kind']?.toString() ?? 'present',
      schoolYearLabel: json['school_year_label']?.toString() ?? '',
      days: raw
          .map((e) => AttendanceDay.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList(),
    );
  }

  @override
  List<Object?> get props => [studentName, kind, days];
}

class DisciplineItem extends Equatable {
  const DisciplineItem({
    required this.id,
    required this.title,
    required this.statusLabel,
    this.dateLabel = '',
    this.description = '',
    this.category = '',
    this.severityLabel = '',
    this.reason = '',
  });

  final String id;
  final String title;
  final String statusLabel;
  final String dateLabel;
  final String description;
  final String category;
  final String severityLabel;
  final String reason;

  factory DisciplineItem.fromJson(Map<String, dynamic> json) {
    return DisciplineItem(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ??
          json['label']?.toString() ??
          '',
      statusLabel: json['status_label']?.toString() ?? '',
      dateLabel: json['date_label']?.toString() ?? '',
      description: json['description']?.toString() ?? '',
      category: json['category']?.toString() ?? '',
      severityLabel: json['severity_label']?.toString() ?? '',
      reason: json['reason']?.toString() ?? '',
    );
  }

  @override
  List<Object?> get props => [id, title, statusLabel];
}

class DisciplineIdentity extends Equatable {
  const DisciplineIdentity({
    this.matricule = '',
    this.nom = '',
    this.postnom = '',
    this.prenom = '',
    this.className = '',
    this.levelLabel = '',
    this.sectionLabel = '',
    this.optionLabel = '',
  });

  final String matricule;
  final String nom;
  final String postnom;
  final String prenom;
  final String className;
  final String levelLabel;
  final String sectionLabel;
  final String optionLabel;

  factory DisciplineIdentity.fromJson(Map<String, dynamic> json) {
    return DisciplineIdentity(
      matricule: json['matricule']?.toString() ?? '',
      nom: json['nom']?.toString() ?? '',
      postnom: json['postnom']?.toString() ?? '',
      prenom: json['prenom']?.toString() ?? '',
      className: json['class_name']?.toString() ?? '',
      levelLabel: json['level_label']?.toString() ?? '',
      sectionLabel: json['section_label']?.toString() ?? '',
      optionLabel: json['option_label']?.toString() ?? '',
    );
  }

  @override
  List<Object?> get props => [matricule, className];
}

class DisciplineStats extends Equatable {
  const DisciplineStats({
    this.present = 0,
    this.late = 0,
    this.absent = 0,
    this.unjustified = 0,
    this.positiveObservations = 0,
    this.negativeObservations = 0,
    this.openIncidents = 0,
    this.closedIncidents = 0,
    this.totalSummons = 0,
    this.activeMeasures = 0,
    this.totalIncidents = 0,
    this.pendingSummons = 0,
    this.lateMinutes = 0,
  });

  final int present;
  final int late;
  final int absent;
  final int unjustified;
  final int positiveObservations;
  final int negativeObservations;
  final int openIncidents;
  final int closedIncidents;
  final int totalSummons;
  final int activeMeasures;
  final int totalIncidents;
  final int pendingSummons;
  final int lateMinutes;

  factory DisciplineStats.fromJson(Map<String, dynamic> json) {
    int n(String key) => int.tryParse(json[key]?.toString() ?? '') ?? 0;
    return DisciplineStats(
      present: n('present'),
      late: n('late'),
      absent: n('absent'),
      unjustified: n('unjustified'),
      positiveObservations: n('positive_observations'),
      negativeObservations: n('negative_observations'),
      openIncidents: n('open_incidents'),
      closedIncidents: n('closed_incidents'),
      totalSummons: n('total_summons'),
      activeMeasures: n('active_measures'),
      totalIncidents: n('total_incidents'),
      pendingSummons: n('pending_summons'),
      lateMinutes: n('late_minutes'),
    );
  }

  @override
  List<Object?> get props => [openIncidents, totalSummons, activeMeasures];
}

class DisciplineDossier extends Equatable {
  const DisciplineDossier({
    required this.studentName,
    required this.incidents,
    required this.measures,
    required this.summonses,
    this.schoolYearLabel = '',
    this.reference = '',
    this.followupStatusLabel = '',
    this.photoUrl,
    this.identity = const DisciplineIdentity(),
    this.stats = const DisciplineStats(),
    this.recentAttendance = const [],
  });

  final String studentName;
  final String schoolYearLabel;
  final String reference;
  final String followupStatusLabel;
  final String? photoUrl;
  final DisciplineIdentity identity;
  final DisciplineStats stats;
  final List<AttendanceDay> recentAttendance;
  final List<DisciplineItem> incidents;
  final List<DisciplineItem> measures;
  final List<DisciplineItem> summonses;

  factory DisciplineDossier.fromJson(Map<String, dynamic> json) {
    List<DisciplineItem> parse(String key) {
      final raw = json[key] as List<dynamic>? ?? const [];
      return raw
          .map(
            (e) => DisciplineItem.fromJson(Map<String, dynamic>.from(e as Map)),
          )
          .toList();
    }

    final attendanceRaw =
        json['recent_attendance'] as List<dynamic>? ?? const [];
    final identityMap =
        Map<String, dynamic>.from(json['identity'] as Map? ?? {});
    final photoRaw =
        json['photo']?.toString() ?? identityMap['photo']?.toString();

    return DisciplineDossier(
      studentName: json['student_name']?.toString() ?? '',
      schoolYearLabel: json['school_year_label']?.toString() ?? '',
      reference: json['reference']?.toString() ?? '',
      followupStatusLabel: json['followup_status_label']?.toString() ?? '',
      photoUrl: ApiConfig.resolveMediaUrl(photoRaw),
      identity: DisciplineIdentity.fromJson(identityMap),
      stats: DisciplineStats.fromJson(
        Map<String, dynamic>.from(json['stats'] as Map? ?? {}),
      ),
      recentAttendance: attendanceRaw
          .map((e) => AttendanceDay.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList(),
      incidents: parse('incidents'),
      measures: parse('measures'),
      summonses: parse('summonses'),
    );
  }

  @override
  List<Object?> get props =>
      [studentName, reference, incidents, measures, summonses];
}

class FinanceObligation extends Equatable {
  const FinanceObligation({
    required this.id,
    required this.label,
    required this.amountDueLabel,
    required this.amountPaidLabel,
    required this.amountRemainingLabel,
    required this.tone,
  });

  final String id;
  final String label;
  final String amountDueLabel;
  final String amountPaidLabel;
  final String amountRemainingLabel;
  final String tone;

  factory FinanceObligation.fromJson(Map<String, dynamic> json) {
    return FinanceObligation(
      id: json['id']?.toString() ?? '',
      label: json['label']?.toString() ?? '',
      amountDueLabel: json['amount_due_label']?.toString() ?? '',
      amountPaidLabel: json['amount_paid_label']?.toString() ?? '',
      amountRemainingLabel: json['amount_remaining_label']?.toString() ?? '',
      tone: json['tone']?.toString() ?? 'unpaid',
    );
  }

  @override
  List<Object?> get props => [id, label, tone];
}

class FinancePayment extends Equatable {
  const FinancePayment({
    required this.id,
    required this.receiptNumber,
    required this.dateLabel,
    required this.amountLabel,
    required this.statusLabel,
  });

  final String id;
  final String receiptNumber;
  final String dateLabel;
  final String amountLabel;
  final String statusLabel;

  factory FinancePayment.fromJson(Map<String, dynamic> json) {
    return FinancePayment(
      id: json['id']?.toString() ?? '',
      receiptNumber: json['receipt_number']?.toString() ?? '',
      dateLabel: json['date_label']?.toString() ?? '',
      amountLabel: json['amount_label']?.toString() ?? '',
      statusLabel: json['status_label']?.toString() ?? '',
    );
  }

  @override
  List<Object?> get props => [id, receiptNumber];
}

class ChildFinanceSituation extends Equatable {
  const ChildFinanceSituation({
    required this.studentName,
    required this.amountDueLabel,
    required this.amountPaidLabel,
    required this.amountRemainingLabel,
    required this.tone,
    required this.obligations,
    required this.payments,
    this.schoolYearLabel = '',
  });

  final String studentName;
  final String schoolYearLabel;
  final String amountDueLabel;
  final String amountPaidLabel;
  final String amountRemainingLabel;
  final String tone;
  final List<FinanceObligation> obligations;
  final List<FinancePayment> payments;

  factory ChildFinanceSituation.fromJson(Map<String, dynamic> json) {
    final totals = Map<String, dynamic>.from(json['totals'] as Map? ?? {});
    final obligationsRaw = json['obligations'] as List<dynamic>? ?? const [];
    final paymentsRaw = json['payments'] as List<dynamic>? ?? const [];
    return ChildFinanceSituation(
      studentName: json['student_name']?.toString() ?? '',
      schoolYearLabel: json['school_year_label']?.toString() ?? '',
      amountDueLabel: totals['amount_due_label']?.toString() ?? '0 CDF',
      amountPaidLabel: totals['amount_paid_label']?.toString() ?? '0 CDF',
      amountRemainingLabel:
          totals['amount_remaining_label']?.toString() ?? '0 CDF',
      tone: totals['tone']?.toString() ?? 'paid',
      obligations: obligationsRaw
          .map(
            (e) => FinanceObligation.fromJson(
              Map<String, dynamic>.from(e as Map),
            ),
          )
          .toList(),
      payments: paymentsRaw
          .map(
            (e) =>
                FinancePayment.fromJson(Map<String, dynamic>.from(e as Map)),
          )
          .toList(),
    );
  }

  @override
  List<Object?> get props => [studentName, tone, obligations, payments];
}
