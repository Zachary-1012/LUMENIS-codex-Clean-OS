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
    this.permissionStatus,
    this.executionId,
    this.evidenceRecorded,
    this.auditId,
    this.requiresApproval,
    this.permissionRequired,
    this.riskLevel,
    this.reason,
    this.aiIsDerivative,
    this.note,
  });

  final Ai01IntentKind kind;

  /// Server-returned execution status (`completed`, `failed`, `blocked`,
  /// `rejected`, ...) or `pending_approval`.
  final String status;
  final String? permissionStatus;
  final String? executionId;

  /// `null` when the server did not report an execution (pending approval).
  final bool? evidenceRecorded;
  final String? auditId;

  /// Permission metadata returned by the existing intent route. These fields
  /// describe the server's decision; only [permissionStatus] == `granted`
  /// admits an execution response.
  final bool? requiresApproval;
  final String? permissionRequired;
  final String? riskLevel;
  final String? reason;

  /// Existing route metadata. The route does not return generated result text
  /// or a result version; [note] is only its explanatory note.
  final bool? aiIsDerivative;
  final String? note;

  factory Ai01IntentResult.fromResponse(Map<String, dynamic> response) {
    final status = response['status'];
    final auditId = response['audit_id'];
    if (response['ok'] == false &&
        status == 'pending_approval' &&
        response['requires_approval'] == true) {
      return Ai01IntentResult(
        kind: Ai01IntentKind.pendingApproval,
        status: 'pending_approval',
        requiresApproval: true,
        permissionRequired: _optionalString(response['permission_required']),
        riskLevel: _optionalString(response['risk_level']),
        reason: _optionalString(response['reason']),
        auditId: auditId is String && auditId.isNotEmpty ? auditId : null,
      );
    }

    final executionId = response['execution_id'];
    final evidenceRecorded = response['evidence_recorded'];
    final permissionStatus = response['permission_status'];
    if (response['ok'] != true ||
        permissionStatus != 'granted' ||
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
      permissionStatus: permissionStatus as String,
      executionId: executionId,
      evidenceRecorded: evidenceRecorded,
      auditId: auditId is String && auditId.isNotEmpty ? auditId : null,
      aiIsDerivative: response['ai_is_derivative'] is bool
          ? response['ai_is_derivative'] as bool
          : null,
      note: _optionalString(response['note']),
    );
  }

  static String? _optionalString(Object? value) =>
      value is String && value.isNotEmpty ? value : null;
}
