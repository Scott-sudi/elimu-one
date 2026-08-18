import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import 'pdf_frame_stub.dart'
    if (dart.library.html) 'pdf_frame_web.dart' as pdf_frame;

/// Affiche un PDF : iframe sur web, sinon ouverture externe.
class PdfPreviewPane extends StatelessWidget {
  const PdfPreviewPane({super.key, required this.pdfUrl});

  final String pdfUrl;

  @override
  Widget build(BuildContext context) {
    if (pdfUrl.isEmpty) {
      return const Center(child: Text('PDF indisponible.'));
    }
    if (kIsWeb) {
      return pdf_frame.buildPdfFrame(pdfUrl);
    }
    return Center(
      child: ElevatedButton.icon(
        onPressed: () async {
          final uri = Uri.tryParse(pdfUrl);
          if (uri != null) {
            await launchUrl(uri, mode: LaunchMode.externalApplication);
          }
        },
        icon: const Icon(Icons.picture_as_pdf_outlined),
        label: const Text('Ouvrir le reçu PDF'),
      ),
    );
  }
}
