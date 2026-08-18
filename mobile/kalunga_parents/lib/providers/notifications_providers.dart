import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/notification_models.dart';
import 'dependency_providers.dart';

final parentNotificationsProvider =
    FutureProvider.autoDispose<ParentNotificationsResult>((ref) async {
  return ref.watch(notificationsRepositoryProvider).load();
});
