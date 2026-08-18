import '../models/child_models.dart';
import '../services/auth_service.dart';
import '../services/children_service.dart';

/// Repository Mes Enfants : session parent + API Django.
class ChildrenRepository {
  ChildrenRepository({
    required ChildrenService childrenService,
    required AuthService authService,
  })  : _children = childrenService,
        _auth = authService;

  final ChildrenService _children;
  final AuthService _auth;

  Future<List<ChildSummary>> loadChildren() async {
    final session = await _auth.readParentSession();
    final guardianId = session?.guardianPublicId ?? '';
    return _children.fetchChildren(guardianPublicId: guardianId);
  }
}
