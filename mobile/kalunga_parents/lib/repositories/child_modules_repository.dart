import '../models/child_module_models.dart';
import '../models/student_id_card.dart';
import '../services/auth_service.dart';
import '../services/child_modules_service.dart';

class ChildModulesRepository {
  ChildModulesRepository({
    required ChildModulesService modulesService,
    required AuthService authService,
  })  : _modules = modulesService,
        _auth = authService;

  final ChildModulesService _modules;
  final AuthService _auth;

  Future<String> _guardianId() async {
    final session = await _auth.readParentSession();
    return session?.guardianPublicId ?? '';
  }

  Future<AttendanceListResult> loadAttendance({
    required String studentId,
    required String kind,
  }) async {
    return _modules.fetchAttendance(
      guardianPublicId: await _guardianId(),
      studentId: studentId,
      kind: kind,
    );
  }

  Future<DisciplineDossier> loadDiscipline({required String studentId}) async {
    return _modules.fetchDiscipline(
      guardianPublicId: await _guardianId(),
      studentId: studentId,
    );
  }

  Future<ChildFinanceSituation> loadFinance({required String studentId}) async {
    return _modules.fetchFinance(
      guardianPublicId: await _guardianId(),
      studentId: studentId,
    );
  }

  Future<StudentIdCard> loadCard({required String studentId}) async {
    return _modules.fetchCard(
      guardianPublicId: await _guardianId(),
      studentId: studentId,
    );
  }
}
