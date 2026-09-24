import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/features/account/acc03/acc03_snapshot.dart';

void main() {
  test(
    'ACC-03 builds distinct workspace destinations from safe context data',
    () {
      final snapshot = Acc03Snapshot.fromResponses(
        identity: {
          'ok': true,
          'runtime_guardian': {'overall': 'healthy'},
        },
        context: {
          'ok': true,
          'contract': 'lumenis.context.v1',
          'selection_only': true,
          'context': {
            'mode': 'GLOBAL_ALL',
            'display_name': {'zh': '全局查看'},
          },
        },
      );

      expect(snapshot.runtimeState, Acc03RuntimeState.connected);
      expect(snapshot.contextState, Acc03RuntimeState.connected);
      expect(snapshot.launchCards.map((card) => card.domain), [
        'CTH',
        'BMP',
        'AI',
      ]);
    },
  );

  test('ACC-03 does not surface path or secret-like context labels', () {
    final snapshot = Acc03Snapshot.fromResponses(
      identity: {
        'ok': true,
        'runtime_guardian': {'overall': 'healthy'},
      },
      context: {
        'ok': true,
        'contract': 'lumenis.context.v1',
        'selection_only': true,
        'context': {
          'mode': 'FOCUS',
          'display_name': {'zh': 'provider=internal /private/path'},
        },
      },
    );

    expect(snapshot.currentView, isNull);
  });

  test(
    'ACC-03 preserves unknown when runtime or context evidence is missing',
    () {
      final snapshot = Acc03Snapshot.fromResponses(identity: {'ok': true});

      expect(snapshot.runtimeState, Acc03RuntimeState.unknown);
      expect(snapshot.startupChecks.first.state, Acc03RuntimeState.unknown);
      expect(snapshot.contextState, Acc03RuntimeState.unknown);
    },
  );

  test('ACC-03 does not treat an invalid context envelope as connected', () {
    final snapshot = Acc03Snapshot.fromResponses(
      identity: {
        'ok': true,
        'runtime_guardian': {'overall': 'healthy'},
      },
      context: {
        'context': {
          'mode': 'FOCUS',
          'display_name': {'zh': '未确认范围'},
        },
      },
    );

    expect(snapshot.runtimeState, Acc03RuntimeState.connected);
    expect(snapshot.contextState, Acc03RuntimeState.unavailable);
    expect(snapshot.currentView, isNull);
  });
}
