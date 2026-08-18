import '../config/api_config.dart';
import '../constants/api_endpoints.dart';
import '../core/errors/api_exception.dart';
import '../core/network/api_service.dart';
import '../models/notification_detail_models.dart';
import 'auth_service.dart';

class NotificationDetailService {
  NotificationDetailService({
    required ApiService api,
    required AuthService auth,
  })  : _api = api,
        _auth = auth;

  final ApiService _api;
  final AuthService _auth;

  Future<String> _guardianId() async {
    final parent = await _auth.readParentSession();
    return parent?.guardianPublicId ?? '';
  }

  Future<CommunicationDetail> fetchCommunication(String publicId) async {
    try {
      final gid = await _guardianId();
      final response = await _api.get<CommunicationDetail>(
        ApiEndpoints.parentCommunicationDetail(publicId),
        queryParameters: {'guardian_public_id': gid},
        parser: (raw) => CommunicationDetail.fromJson(
          Map<String, dynamic>.from(raw as Map),
        ),
      );
      return response.data!;
    } on ApiException {
      rethrow;
    } catch (_) {
      throw const NetworkException();
    }
  }

  Future<PaymentReceiptDetail> fetchPaymentReceipt(String publicId) async {
    try {
      final gid = await _guardianId();
      final response = await _api.get<PaymentReceiptDetail>(
        ApiEndpoints.parentPaymentReceipt(publicId),
        queryParameters: {'guardian_public_id': gid},
        parser: (raw) => PaymentReceiptDetail.fromJson(
          Map<String, dynamic>.from(raw as Map),
        ),
      );
      final data = response.data!;
      // Garantit l'URL PDF via proxy web si besoin.
      if (data.pdfUrl.isEmpty) {
        final path = ApiEndpoints.parentPaymentReceiptPdf(publicId);
        final url = ApiConfig.resolveMediaUrl(
          '${ApiConfig.baseUrl}/$path?guardian_public_id=$gid&inline=1',
        );
        return PaymentReceiptDetail(
          id: data.id,
          receiptNumber: data.receiptNumber,
          studentName: data.studentName,
          amountLabel: data.amountLabel,
          pdfUrl: url ?? '',
          paymentDateLabel: data.paymentDateLabel,
          matricule: data.matricule,
          className: data.className,
          schoolYearLabel: data.schoolYearLabel,
          amountInWords: data.amountInWords,
          remainingLabel: data.remainingLabel,
          purpose: data.purpose,
          paymentMethodLabel: data.paymentMethodLabel,
          recordedBy: data.recordedBy,
        );
      }
      return data;
    } on ApiException {
      rethrow;
    } catch (_) {
      throw const NetworkException();
    }
  }

  Future<DisciplineDetail> fetchDiscipline({
    required String kind,
    required String publicId,
  }) async {
    try {
      final gid = await _guardianId();
      final response = await _api.get<DisciplineDetail>(
        ApiEndpoints.parentDisciplineDetail(kind, publicId),
        queryParameters: {'guardian_public_id': gid},
        parser: (raw) => DisciplineDetail.fromJson(
          Map<String, dynamic>.from(raw as Map),
        ),
      );
      return response.data!;
    } on ApiException {
      rethrow;
    } catch (_) {
      throw const NetworkException();
    }
  }
}
