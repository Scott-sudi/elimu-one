import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_theme_colors.dart';
import '../../models/child_models.dart';
import '../../models/child_module_models.dart';
import '../../providers/child_modules_providers.dart';

/// Dossier disciplinaire — même structure que le dossier web ERP.
class ChildDisciplineScreen extends ConsumerWidget {
  const ChildDisciplineScreen({super.key, required this.child});

  final ChildSummary child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncData = ref.watch(childDisciplineProvider(child.id));

    return Scaffold(
      backgroundColor: context.appBackground,
      appBar: AppBar(
        backgroundColor: context.appPrimary,
        foregroundColor: Colors.white,
        title: const Text('Discipline'),
      ),
      body: asyncData.when(
        loading: () => Center(
          child: CircularProgressIndicator(color: context.appPrimary),
        ),
        error: (e, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(e.toString(), textAlign: TextAlign.center),
                const SizedBox(height: 12),
                ElevatedButton(
                  onPressed: () =>
                      ref.invalidate(childDisciplineProvider(child.id)),
                  child: const Text('Réessayer'),
                ),
              ],
            ),
          ),
        ),
        data: (dossier) => RefreshIndicator(
          color: context.appPrimary,
          onRefresh: () async {
            ref.invalidate(childDisciplineProvider(child.id));
            await ref.read(childDisciplineProvider(child.id).future);
          },
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
            children: [
              _HeaderCard(dossier: dossier, child: child),
              const SizedBox(height: 12),
              _IdentityCard(dossier: dossier),
              const SizedBox(height: 12),
              _StatsGrid(stats: dossier.stats),
              if (dossier.recentAttendance.isNotEmpty) ...[
                const SizedBox(height: 12),
                _SectionTitle('Derniers pointages'),
                ...dossier.recentAttendance.map(
                  (row) => _SimpleTile(
                    title: row.dateLabel,
                    subtitle: [
                      row.statusLabel,
                      if (row.note.isNotEmpty) row.note,
                    ].where((e) => e.isNotEmpty).join(' · '),
                  ),
                ),
              ],
              const SizedBox(height: 12),
              _SectionTitle(
                'Incidents disciplinaires'
                '${dossier.stats.totalIncidents > 0 ? ' (${dossier.stats.totalIncidents})' : ''}',
              ),
              if (dossier.incidents.isEmpty)
                const _EmptyLine('Aucun incident disciplinaire enregistré.')
              else
                ...dossier.incidents.map(
                  (item) => _IncidentTile(item: item),
                ),
              const SizedBox(height: 12),
              _SectionTitle('Mesures disciplinaires'),
              if (dossier.measures.isEmpty)
                const _EmptyLine('Aucune mesure disciplinaire appliquée.')
              else
                ...dossier.measures.map(
                  (item) => _SimpleTile(
                    title: item.title,
                    subtitle: [
                      if (item.reason.isNotEmpty) item.reason,
                      if (item.dateLabel.isNotEmpty) item.dateLabel,
                      item.statusLabel,
                    ].where((e) => e.isNotEmpty).join(' · '),
                  ),
                ),
              const SizedBox(height: 12),
              _SectionTitle(
                'Convocations'
                '${dossier.stats.totalSummons > 0 ? ' (${dossier.stats.totalSummons})' : ''}',
              ),
              if (dossier.summonses.isEmpty)
                const _EmptyLine('Aucune convocation enregistrée.')
              else
                ...dossier.summonses.map(
                  (item) => _SimpleTile(
                    title: item.title,
                    subtitle: [
                      if (item.dateLabel.isNotEmpty) item.dateLabel,
                      if (item.reason.isNotEmpty) item.reason,
                      item.statusLabel,
                    ].where((e) => e.isNotEmpty).join(' · '),
                  ),
                ),
              if (dossier.followupStatusLabel.isNotEmpty) ...[
                const SizedBox(height: 16),
                _SectionTitle('Suivi'),
                _SimpleTile(
                  title: 'État actuel',
                  subtitle: dossier.followupStatusLabel,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _HeaderCard extends StatelessWidget {
  const _HeaderCard({required this.dossier, required this.child});

  final DisciplineDossier dossier;
  final ChildSummary child;

  @override
  Widget build(BuildContext context) {
    final photoUrl = (dossier.photoUrl != null && dossier.photoUrl!.isNotEmpty)
        ? dossier.photoUrl
        : child.photoUrl;

    return Material(
      color: context.appCard,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'DOSSIER DISCIPLINAIRE',
                    style: TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 15,
                      letterSpacing: 0.4,
                      color: context.appPrimary,
                    ),
                  ),
                  if (dossier.reference.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      'Réf. ${dossier.reference}',
                      style: TextStyle(
                        color: context.appTextSecondary,
                        fontSize: 13,
                      ),
                    ),
                  ],
                  if (dossier.schoolYearLabel.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      'Année scolaire ${dossier.schoolYearLabel}',
                      style: TextStyle(color: context.appTextSecondary),
                    ),
                  ],
                  if (dossier.followupStatusLabel.isNotEmpty) ...[
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.lightGreen,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        dossier.followupStatusLabel,
                        style: TextStyle(
                          color: context.appPrimary,
                          fontWeight: FontWeight.w600,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(width: 12),
            _DossierPhoto(photoUrl: photoUrl, initials: child.initials),
          ],
        ),
      ),
    );
  }
}

class _DossierPhoto extends StatelessWidget {
  const _DossierPhoto({required this.photoUrl, required this.initials});

  final String? photoUrl;
  final String initials;

  @override
  Widget build(BuildContext context) {
    final fallback = Text(
      initials,
      style: TextStyle(
        color: context.appPrimary,
        fontWeight: FontWeight.w700,
        fontSize: 20,
      ),
    );

    return ClipRRect(
      borderRadius: BorderRadius.circular(10),
      child: Container(
        width: 88,
        height: 110,
        color: AppColors.lightGreen,
        alignment: Alignment.center,
        child: (photoUrl == null || photoUrl!.isEmpty)
            ? fallback
            : Image.network(
                photoUrl!,
                key: ValueKey(photoUrl),
                fit: BoxFit.cover,
                width: 88,
                height: 110,
                webHtmlElementStrategy: kIsWeb
                    ? WebHtmlElementStrategy.prefer
                    : WebHtmlElementStrategy.never,
                filterQuality: FilterQuality.medium,
                errorBuilder: (_, __, ___) => fallback,
                loadingBuilder: (context, childWidget, progress) {
                  if (progress == null) return childWidget;
                  return SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: context.appPrimary,
                    ),
                  );
                },
              ),
      ),
    );
  }
}

class _IdentityCard extends StatelessWidget {
  const _IdentityCard({required this.dossier});

  final DisciplineDossier dossier;

  @override
  Widget build(BuildContext context) {
    final id = dossier.identity;
    final rows = <MapEntry<String, String>>[
      if (id.matricule.isNotEmpty) MapEntry('Matricule', id.matricule),
      if (id.className.isNotEmpty) MapEntry('Classe', id.className),
      if (id.levelLabel.isNotEmpty) MapEntry('Niveau', id.levelLabel),
      if (id.sectionLabel.isNotEmpty) MapEntry('Section', id.sectionLabel),
      if (id.optionLabel.isNotEmpty) MapEntry('Option', id.optionLabel),
    ];
    if (rows.isEmpty) return const SizedBox.shrink();

    return Material(
      color: context.appCard,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Identité de l’élève',
              style: TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 15,
                color: context.appTextPrimary,
              ),
            ),
            const SizedBox(height: 10),
            ...rows.map(
              (e) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  children: [
                    SizedBox(
                      width: 88,
                      child: Text(
                        e.key,
                        style: TextStyle(
                          color: context.appTextSecondary,
                          fontSize: 13,
                        ),
                      ),
                    ),
                    Expanded(
                      child: Text(
                        e.value,
                        style: const TextStyle(
                          fontWeight: FontWeight.w600,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatsGrid extends StatelessWidget {
  const _StatsGrid({required this.stats});

  final DisciplineStats stats;

  @override
  Widget build(BuildContext context) {
    final items = <(String, int)>[
      ('Présences', stats.present),
      ('Retards', stats.late),
      ('Absences', stats.absent),
      ('Injustifiées', stats.unjustified),
      ('Obs. +', stats.positiveObservations),
      ('Obs. −', stats.negativeObservations),
      ('Inc. ouverts', stats.openIncidents),
      ('Inc. clôturés', stats.closedIncidents),
      ('Convocations', stats.totalSummons),
      ('Mesures', stats.activeMeasures),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _SectionTitle('Résumé disciplinaire'),
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 8,
          crossAxisSpacing: 8,
          childAspectRatio: 2.4,
          children: items
              .map(
                (e) => Material(
                  color: context.appCard,
                  borderRadius: BorderRadius.circular(10),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 10,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          e.$1,
                          style: TextStyle(
                            fontSize: 12,
                            color: context.appTextSecondary,
                          ),
                        ),
                        Text(
                          '${e.$2}',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                            color: context.appTextPrimary,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              )
              .toList(),
        ),
      ],
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.title);

  final String title;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8, top: 4),
      child: Text(
        title,
        style: TextStyle(
          fontWeight: FontWeight.w700,
          fontSize: 16,
          color: context.appTextPrimary,
        ),
      ),
    );
  }
}

class _EmptyLine extends StatelessWidget {
  const _EmptyLine(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        text,
        style: TextStyle(color: context.appTextSecondary, fontSize: 13),
      ),
    );
  }
}

class _SimpleTile extends StatelessWidget {
  const _SimpleTile({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: context.appCard,
        borderRadius: BorderRadius.circular(12),
        child: ListTile(
          title: Text(
            title,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          subtitle: subtitle.isEmpty
              ? null
              : Text(
                  subtitle,
                  style: TextStyle(color: context.appTextSecondary),
                ),
        ),
      ),
    );
  }
}

class _IncidentTile extends StatelessWidget {
  const _IncidentTile({required this.item});

  final DisciplineItem item;

  @override
  Widget build(BuildContext context) {
    final meta = [
      if (item.dateLabel.isNotEmpty) item.dateLabel,
      if (item.category.isNotEmpty) item.category,
      if (item.severityLabel.isNotEmpty) item.severityLabel,
      item.statusLabel,
    ].where((e) => e.isNotEmpty).join(' · ');

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: context.appCard,
        borderRadius: BorderRadius.circular(12),
        child: ListTile(
          title: Text(
            item.title,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          subtitle: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (meta.isNotEmpty)
                Text(
                  meta,
                  style: TextStyle(color: context.appTextSecondary),
                ),
              if (item.description.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  item.description,
                  style: TextStyle(
                    color: context.appTextSecondary,
                    fontSize: 13,
                  ),
                ),
              ],
            ],
          ),
          isThreeLine: item.description.isNotEmpty,
        ),
      ),
    );
  }
}
