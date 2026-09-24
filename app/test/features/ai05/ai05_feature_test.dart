import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/features/ai05/ai05_snapshot.dart';

void main() {
  test('AI-05 normalizes provider identity and preserves returned state', () {
    final snapshot = Ai05Snapshot.fromResponse({
      'ok': true,
      'screen': 'AI-05',
      'source': 'runtime',
      'bound': true,
      'providers': [
        {'name': 'ollama-private-prod', 'state': 'ready', 'latency_ms': 42},
        {'name': 'zhipu-internal', 'state': 'offline', 'latency_ms': -1},
      ],
      'call_series': [10, -1, 25, 100000001],
    });

    expect(snapshot.isBound, isTrue);
    expect(snapshot.providers, hasLength(2));
    expect(snapshot.providers.first.kind, Ai05ProviderKind.local);
    expect(snapshot.providers.last.kind, Ai05ProviderKind.optional);
    expect(snapshot.providers.first.latencyMs, 42);
    expect(snapshot.providers.last.latencyMs, isNull);
    expect(snapshot.callSeries, [10, 25]);
  });

  test(
    'AI-05 fallback stays explicitly diagnostic and does not expose raw names',
    () {
      final snapshot = Ai05Snapshot.fromAi01Diagnostic({
        'ok': true,
        'screen': 'AI-01',
        'sections': [
          {
            'type': 'runtime',
            'items': [
              {'name': 'provider-secret', 'state': 'ok'},
              {'name': 'local', 'state': 'idle'},
            ],
          },
        ],
      });

      expect(snapshot.bindingState, Ai05BindingState.fallbackDiagnostic);
      expect(snapshot.providers, hasLength(2));
      expect(snapshot.providers.first.kind, Ai05ProviderKind.generic);
      expect(snapshot.providers.last.kind, Ai05ProviderKind.local);
    },
  );
}
