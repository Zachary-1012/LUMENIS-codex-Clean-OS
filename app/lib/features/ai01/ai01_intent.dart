/// Result of one AI-01 intent submission, parsed strictly from the real
/// `POST /api/experience/ai/intent` response.
///
/// A 2xx response is never treated as success by itself: the server returns
/// `ok:true` with a non-`completed` execution status (for example `failed`
/// while the owned AI runtime is not bound), and `ok:false` with
/// `pending_approval`. Only an execution whose returned status is `completed`
/// is reported as completed, and Evidence is only "recorded" when the server
/// says so.
enum Ai01IntentKind { completed, notCompleted, pendingApproval }

class Ai01IntentResult {
  const Ai01IntentResult({
    required this.kind,
    required this.status,
    this.executionId,
    this.evidenceRecorded,
    this.auditId,
  });

  final Ai01IntentKind kind;

  /// Server-returned execution status (`completed`, `failed`, `blocked`,
  /// `rejected`, ...) or `pending_approval`.
  final String status;
  final String? executionId;

  /// `null` when the server did not report an execution (pending approval).
  final bool? evidenceRecorded;
  final String? auditId;

  factory Ai01IntentResult.fromResponse(Map<String, dynamic> response) {
    final status = response['status'];
    final auditId = response['audit_id'];
    if (response['ok'] == false &&
        status == 'pending_approval' &&
        response['requires_approval'] == true) {
      return Ai01IntentResult(
        kind: Ai01IntentKind.pendingApproval,
        status: 'pending_approval',
        auditId: auditId is String && auditId.isNotEmpty ? auditId : null,
      );
    }

    final executionId = response['execution_id'];
    final evidenceRecorded = response['evidence_recorded'];
    if (response['ok'] != true ||
        response['permission_status'] != 'granted' ||
        status is! String ||
        status.isEmpty ||
        executionId is! String ||
        executionId.isEmpty ||
        evidenceRecorded is! bool) {
      throw const FormatException('AI-01 intent response is not valid.');
    }
    return Ai01IntentResult(
      kind: status == 'completed'
          ? Ai01IntentKind.completed
          : Ai01IntentKind.notCompleted,
      status: status,
      executionId: executionId,
      evidenceRecorded: evidenceRecorded,
      auditId: auditId is String && auditId.isNotEmpty ? auditId : null,
    );
  }
}
