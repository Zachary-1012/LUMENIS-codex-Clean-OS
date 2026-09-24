import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/features/account/acc04/acc04_snapshot.dart';

void main() {
  test('ACC-04 keeps unbound guard state and safe recovery paths honest', () {
    final snapshot = Acc04Snapshot.fromResponse({
      'ok': true,
      'screen': 'ACC-04',
      'source': 'runtime',
      'bound': false,
      'guard': {
        'recovery_paths': [
          'retry',
          'switch_context',
          'request_access',
          'return',
        ],
        'reason': 'token=secret /private/path',
      },
    });

    expect(snapshot.guardState, Acc04GuardState.unavailable);
    expect(snapshot.productAccountDeferred, isTrue);
    expect(snapshot.recoveryPaths, contains(Acc04RecoveryPath.recheck));
    expect(snapshot.reason, isNull);
  });

  test('ACC-04 rejects a response for another screen', () {
    expect(
      () => Acc04Snapshot.fromResponse({'ok': true, 'screen': 'ACC-03'}),
      throwsFormatException,
    );
  });
}
