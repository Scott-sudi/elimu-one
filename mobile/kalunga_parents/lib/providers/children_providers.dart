import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/errors/api_exception.dart';
import '../models/child_models.dart';
import '../utils/friendly_error.dart';
import 'dependency_providers.dart';

/// Liste des enfants du parent connecté.
final childrenListProvider = FutureProvider.autoDispose<List<ChildSummary>>((
  ref,
) async {
  try {
    return await ref.watch(childrenRepositoryProvider).loadChildren();
  } on ApiException catch (e) {
    throw ChildrenLoadException(friendlyErrorMessage(e));
  } catch (e) {
    throw ChildrenLoadException(friendlyErrorMessage(e));
  }
});

class ChildrenLoadException implements Exception {
  const ChildrenLoadException(this.message);

  final String message;

  @override
  String toString() => message;
}
