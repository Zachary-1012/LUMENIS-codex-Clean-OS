import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/features/ai01/ai01_intent.dart';

void main() {
  test('completed execution is the only success', () {
    final result = Ai01IntentResult.fromResponse({
      'ok': true,
      'permission_status': 'granted',
      'status': 'completed',
      'execution_id': 'exec-1',
      'evidence_recorded': true,
      'audit_id': 'aud-1',
      'ai_is_derivative': true,
      'note': 'AI 输出保持派生结果。',
    });

    expect(result.kind, Ai01IntentKind.completed);
    expect(result.permissionStatus, 'granted');
    expect(result.executionId, 'exec-1');
    expect(result.evidenceRecorded, isTrue);
    expect(result.auditId, 'aud-1');
    expect(result.aiIsDerivative, isTrue);
    expect(result.note, 'AI 输出保持派生结果。');
  });

  test('2xx with a failed execution (owned AI not bound) is not success', () {
    // Real Core response while the owned AI runtime is NOT_BOUND.
    final result = Ai01IntentResult.fromResponse({
      'ok': true,
      'permission_status': 'granted',
      'status': 'failed',
      'execution_id': '2c37c431869e4129',
      'evidence_recorded': false,
      'ai_is_derivative': true,
      'note': '当前执行未完成。',
    });

    expect(result.kind, Ai01IntentKind.notCompleted);
    expect(result.status, 'failed');
    expect(result.evidenceRecorded, isFalse);
    expect(result.permissionStatus, 'granted');
    expect(result.aiIsDerivative, isTrue);
    expect(result.note, '当前执行未完成。');
  });

  test('pending approval is parsed as not executed', () {
    final result = Ai01IntentResult.fromResponse({
      'ok': false,
      'status': 'pending_approval',
      'requires_approval': true,
      'audit_id': 'aud-2',
      'permission_required': 'CONFIG_MODIFY',
      'risk_level': 'high',
      'reason': '需要人工审批。',
    });

    expect(result.kind, Ai01IntentKind.pendingApproval);
    expect(result.executionId, isNull);
    expect(result.evidenceRecorded, isNull);
    expect(result.auditId, 'aud-2');
    expect(result.requiresApproval, isTrue);
    expect(result.permissionRequired, 'CONFIG_MODIFY');
    expect(result.riskLevel, 'high');
    expect(result.reason, '需要人工审批。');
  });

  for (final invalid in <Map<String, dynamic>>[
    {'ok': false, 'status': 'denied'},
    {'ok': true, 'status': 'completed'},
    {
      'ok': true,
      'permission_status': 'denied',
      'status': 'completed',
      'execution_id': 'exec-1',
      'evidence_recorded': true,
    },
    {
      'ok': true,
      'permission_status': 'granted',
      'status': 'completed',
      'execution_id': '',
      'evidence_recorded': true,
    },
    {
      'ok': true,
      'permission_status': 'granted',
      'status': 'completed',
      'execution_id': 'exec-1',
      'evidence_recorded': 'yes',
    },
    {'ok': false, 'status': 'pending_approval', 'requires_approval': false},
  ]) {
    test('rejects an invalid response shape: $invalid', () {
      expect(
        () => Ai01IntentResult.fromResponse(invalid),
        throwsFormatException,
      );
    });
  }
}
