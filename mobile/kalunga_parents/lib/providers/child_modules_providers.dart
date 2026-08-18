import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/child_module_models.dart';
import '../models/student_id_card.dart';
import 'dependency_providers.dart';

final childAttendanceProvider = FutureProvider.autoDispose
    .family<AttendanceListResult, ({String studentId, String kind})>((
  ref,
  args,
) async {
  return ref.watch(childModulesRepositoryProvider).loadAttendance(
        studentId: args.studentId,
        kind: args.kind,
      );
});

final childDisciplineProvider =
    FutureProvider.autoDispose.family<DisciplineDossier, String>((
  ref,
  studentId,
) async {
  return ref
      .watch(childModulesRepositoryProvider)
      .loadDiscipline(studentId: studentId);
});

final childFinanceProvider =
    FutureProvider.autoDispose.family<ChildFinanceSituation, String>((
  ref,
  studentId,
) async {
  return ref
      .watch(childModulesRepositoryProvider)
      .loadFinance(studentId: studentId);
});

final childIdCardProvider =
    FutureProvider.autoDispose.family<StudentIdCard, String>((
  ref,
  studentId,
) async {
  return ref.watch(childModulesRepositoryProvider).loadCard(studentId: studentId);
});
