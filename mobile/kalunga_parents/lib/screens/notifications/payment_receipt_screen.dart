import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme_colors.dart';
import '../../models/notification_detail_models.dart';
import '../../providers/dependency_providers.dart';
import '../../widgets/pdf_preview_pane.dart';

/// Reçu de paiement — aperçu PDF identique au web.
class PaymentReceiptScreen extends ConsumerStatefulWidget {
  const PaymentReceiptScreen({super.key, required this.publicId});

  final String publicId;

  @override
  ConsumerState<PaymentReceiptScreen> createState() =>
      _PaymentReceiptScreenState();
}

class _PaymentReceiptScreenState extends ConsumerState<PaymentReceiptScreen> {
  late final Future<PaymentReceiptDetail> _future;

  @override
  void initState() {
    super.initState();
    _future = ref
        .read(notificationDetailServiceProvider)
        .fetchPaymentReceipt(widget.publicId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: context.appBackground,
      appBar: AppBar(
        title: const Text('Reçu de paiement'),
        backgroundColor: context.appCard,
        foregroundColor: context.appTextPrimary,
        elevation: 0,
      ),
      body: FutureBuilder<PaymentReceiptDetail>(
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
                  snapshot.error?.toString() ?? 'Impossible de charger le reçu.',
                  textAlign: TextAlign.center,
                ),
              ),
            );
          }
          final r = snapshot.data!;
          return Column(
            children: [
              Material(
                color: context.appCard,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        r.receiptNumber.isEmpty ? 'Reçu' : r.receiptNumber,
                        style: TextStyle(
                          color: context.appTextPrimary,
                          fontWeight: FontWeight.w800,
                          fontSize: 17,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        [
                          if (r.studentName.isNotEmpty) r.studentName,
                          if (r.paymentDateLabel.isNotEmpty) r.paymentDateLabel,
                          if (r.amountLabel.isNotEmpty) r.amountLabel,
                        ].join(' · '),
                        style: TextStyle(
                          color: context.appTextSecondary,
                          fontSize: 13,
                        ),
                      ),
                      if (r.purpose.isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Text(
                          r.purpose,
                          style: TextStyle(
                            color: context.appTextSecondary,
                            fontSize: 12.5,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              Divider(height: 1, color: context.appDivider),
              Expanded(
                child: ColoredBox(
                  color: const Color(0xFFE8E8E8),
                  child: PdfPreviewPane(pdfUrl: r.pdfUrl),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
