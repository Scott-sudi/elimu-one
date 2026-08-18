/// Chemins relatifs à [ApiConfig.baseUrl] (sans slash initial obligatoire).
///
/// Exemple : `auth/token/` → `POST {baseUrl}/auth/token/`
abstract final class ApiEndpoints {
  // Santé
  static const String health = 'health/';

  // Authentification JWT (Django SimpleJWT + enveloppe Kalunga)
  static const String token = 'auth/token/';
  static const String tokenRefresh = 'auth/token/refresh/';
  static const String logout = 'auth/logout/';
  static const String me = 'auth/me/';
  static const String changePassword = 'auth/change-password/';

  // Authentification parents (mobile)
  static const String parentVerifyPhone = 'parents/auth/verify-phone/';

  // Réservés parents (à brancher progressivement)
  static const String parentHomeOverview = 'parents/home/overview/';
  static const String parentRecentActivities = 'parents/home/activities/';
  static const String parentNotifications = 'parents/notifications/';
  static const String notifications = 'parents/notifications/';
  static const String parentNotificationsMarkRead = 'parents/notifications/';
  static const String parentDeviceRegister = 'parents/devices/register/';

  static String parentCommunicationDetail(String id) =>
      'parents/communications/$id/';

  static String parentPaymentReceipt(String id) => 'parents/payments/$id/';

  static String parentPaymentReceiptPdf(String id) =>
      'parents/payments/$id/receipt.pdf';

  static String parentDisciplineDetail(String kind, String id) =>
      'parents/discipline/$kind/$id/';
  static const String parentProfile = 'parents/profile/';
  static const String children = 'parents/children/';

  static String childAttendance(String studentId) =>
      'parents/children/$studentId/attendance/';

  static String childDiscipline(String studentId) =>
      'parents/children/$studentId/discipline/';

  static String childFinance(String studentId) =>
      'parents/children/$studentId/finance/';

  static String childCard(String studentId) =>
      'parents/children/$studentId/card/';
}
