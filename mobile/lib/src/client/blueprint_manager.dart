import '../repositories/local_blueprint_repository.dart';

class BlueprintManager {
  BlueprintManager({LocalBlueprintRepository? repository})
    : _repository = repository ?? LocalBlueprintRepository();

  final LocalBlueprintRepository _repository;

  Future<void> submitBlueprint(String blueprintId, String submittedBy) =>
      _repository.submit(blueprintId, actor: submittedBy);

  Future<void> approveBlueprint(
    String blueprintId,
    String approvedBy, {
    String? resolutionNote,
  }) => _repository.approve(
    blueprintId,
    actor: approvedBy,
    resolutionNote: resolutionNote,
  );

  Future<void> returnToDraft(
    String blueprintId,
    String reviewer,
    String note,
  ) => _repository.returnToDraft(blueprintId, actor: reviewer, note: note);
}
