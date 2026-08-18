import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../constants/app_constants.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_theme_colors.dart';
import '../../models/child_models.dart';
import '../../models/student_id_card.dart';
import '../../providers/child_modules_providers.dart';

/// Affiche la carte d'élève (PNG secrétariat identique au web).
class StudentIdCardScreen extends ConsumerWidget {
  const StudentIdCardScreen({super.key, required this.child});

  final ChildSummary child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncCard = ref.watch(childIdCardProvider(child.id));

    return Scaffold(
      backgroundColor: context.appBackground,
      appBar: AppBar(
        backgroundColor: context.appPrimary,
        foregroundColor: Colors.white,
        title: const Text(
          'Carte d’élève',
          style: TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      body: asyncCard.when(
        loading: () => Center(
          child: CircularProgressIndicator(color: context.appPrimary),
        ),
        error: (e, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  e.toString().replaceFirst('Exception: ', ''),
                  textAlign: TextAlign.center,
                  style: TextStyle(color: context.appTextSecondary),
                ),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () =>
                      ref.invalidate(childIdCardProvider(child.id)),
                  child: const Text('Réessayer'),
                ),
              ],
            ),
          ),
        ),
        data: (card) => _CardBody(card: card),
      ),
    );
  }
}

class _CardBody extends StatelessWidget {
  const _CardBody({required this.card});

  final StudentIdCard card;

  @override
  Widget build(BuildContext context) {
    final preview = card.previewUrl;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 32),
      children: [
        if (preview != null && preview.isNotEmpty)
          AspectRatio(
            aspectRatio: 105 / 66,
            child: Material(
              elevation: 3,
              shadowColor: Colors.black38,
              borderRadius: BorderRadius.circular(10),
              clipBehavior: Clip.antiAlias,
              child: Image.network(
                preview,
                fit: BoxFit.contain,
                width: double.infinity,
                errorBuilder: (_, __, ___) => _FlutterIdCard(card: card),
                loadingBuilder: (context, child, progress) {
                  if (progress == null) return child;
                  return ColoredBox(
                    color: Colors.white,
                    child: Center(
                      child: CircularProgressIndicator(
                        color: context.appPrimary,
                      ),
                    ),
                  );
                },
              ),
            ),
          )
        else
          AspectRatio(
            aspectRatio: 105 / 66,
            child: _FlutterIdCard(card: card),
          ),
        const SizedBox(height: 16),
        Text(
          'Carte N° ${card.cardNumber}',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontWeight: FontWeight.w700,
            color: context.appTextPrimary,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          'Identique à la carte enregistrée au secrétariat.',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 12.5,
            color: context.appTextSecondary.withOpacity(0.9),
          ),
        ),
      ],
    );
  }
}

/// Fallback Flutter si le PNG web n'est pas joignable (même structure).
class _FlutterIdCard extends StatelessWidget {
  const _FlutterIdCard({required this.card});

  final StudentIdCard card;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF121212), width: 1.2),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          Container(
            height: 52,
            color: const Color(0xFF121212),
            padding: const EdgeInsets.symmetric(horizontal: 10),
            child: Row(
              children: [
                ClipOval(
                  child: Image.asset(
                    AppConstants.logoAsset,
                    width: 36,
                    height: 36,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => Container(
                      width: 36,
                      height: 36,
                      color: AppColors.lightGreen,
                      alignment: Alignment.center,
                      child: Text(
                        'IK',
                        style: TextStyle(
                          color: context.appPrimary,
                          fontWeight: FontWeight.w800,
                          fontSize: 11,
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        card.schoolName.toUpperCase(),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w800,
                          fontSize: 12,
                        ),
                      ),
                      Text(
                        card.schoolSlogan,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 9.5,
                        ),
                      ),
                    ],
                  ),
                ),
                Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      'Code ${card.schoolCode}',
                      style: const TextStyle(color: Colors.white, fontSize: 9.5),
                    ),
                    Text(
                      card.schoolCity,
                      style: const TextStyle(color: Colors.white, fontSize: 9.5),
                    ),
                  ],
                ),
              ],
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(8, 8, 8, 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 64,
                    height: 80,
                    decoration: BoxDecoration(
                      border: Border.all(color: Colors.black87),
                      borderRadius: BorderRadius.circular(4),
                      color: const Color(0xFFF3F6F4),
                    ),
                    clipBehavior: Clip.antiAlias,
                    child: card.photoUrl != null && card.photoUrl!.isNotEmpty
                        ? Image.network(card.photoUrl!, fit: BoxFit.cover)
                        : const Center(
                            child: Icon(Icons.person, color: Colors.grey),
                          ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    flex: 3,
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              _Field(label: 'NOM', value: card.nom),
                              _Field(label: 'POSTNOM', value: card.postnom),
                              _Field(label: 'PRÉNOM', value: card.prenom),
                              _Field(label: 'MATRICULE', value: card.matricule),
                            ],
                          ),
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              _Field(label: 'CLASSE', value: card.classe),
                              _Field(label: 'SECTION', value: card.section),
                              _Field(label: 'OPTION', value: card.option),
                              _Field(label: 'ANNÉE', value: card.annee),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 6),
                  Column(
                    children: [
                      SizedBox(
                        width: 58,
                        height: 58,
                        child: card.qrImageUrl != null &&
                                card.qrImageUrl!.isNotEmpty
                            ? Image.network(card.qrImageUrl!, fit: BoxFit.contain)
                            : const ColoredBox(
                                color: Color(0xFFEEEEEE),
                                child: Icon(Icons.qr_code, size: 40),
                              ),
                      ),
                      const SizedBox(height: 2),
                      const Text(
                        'Scanner',
                        style: TextStyle(
                          fontSize: 8,
                          color: Color(0xFF757575),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          Container(
            width: double.infinity,
            color: const Color(0xFFF3F6F4),
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Text(
              'Carte N° ${card.cardNumber}',
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 11,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Field extends StatelessWidget {
  const _Field({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontSize: 7.5,
              color: Color(0xFF757575),
              fontWeight: FontWeight.w600,
              letterSpacing: 0.3,
            ),
          ),
          Text(
            value.isEmpty ? '—' : value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontSize: 10.5,
              fontWeight: FontWeight.w700,
              color: Color(0xFF1A1A1A),
            ),
          ),
        ],
      ),
    );
  }
}
