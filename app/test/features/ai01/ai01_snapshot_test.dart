import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/features/ai01/ai01_snapshot.dart';

void main() {
  test('keeps safe provider and suggestion metadata from AI-01', () {
    final snapshot = Ai01Snapshot.fromResponse(_response());

    expect(snapshot.isBound, isTrue);
    expect(snapshot.generatedAt, '2026-09-20T10:30:00');
    expect(snapshot.providers, hasLength(1));
    expect(snapshot.providers.single.name, '本地 Ollama');
    expect(snapshot.providers.single.state, 'idle');
    expect(snapshot.suggestions.single.intent, '检查本周风险变化');
  });

  test('discards whole-store statistics and unscoped execution history', () {
    final snapshot = Ai01Snapshot.fromResponse(_response());

    expect(
      snapshot.providers.map((provider) => provider.name),
      isNot(contains('规则引擎')),
    );
    expect(
      snapshot.providers.map((provider) => provider.name),
      isNot(contains('备用通道')),
    );
    expect(snapshot.suggestions.single.title, '风险变化');
  });

  test('rejects a response for a different screen', () {
    expect(
      () => Ai01Snapshot.fromResponse({'ok': true, 'screen': 'AI-02'}),
      throwsFormatException,
    );
  });
}

Map<String, dynamic> _response() {
  return {
    'ok': true,
    'screen': 'AI-01',
    'source': 'runtime',
    'bound': true,
    'generated_at': '2026-09-20T10:30:00',
    'truth': {
      'evidence_stats': {
        'total': 120,
        'by_result': {'confirmed': 90, 'pending': 30},
        'by_level': {'L1': 120},
      },
    },
    'binding': {'unavailable': []},
    'sections': [
      {
        'type': 'cards',
        'items': [
          {
            'title': '风险变化',
            'desc': '查看趋势与来源',
            'action': {'intent': '检查本周风险变化'},
          },
        ],
      },
      {
        'type': 'split',
        'main': [
          {
            'type': 'timeline',
            'items': [
              {
                'time': '10:20',
                'title': '全局私有任务',
                'desc': 'completed · execution-12',
                'done': true,
              },
            ],
          },
        ],
        'side': [
          {
            'type': 'runtime',
            'items': [
              {
                'kind': 'system',
                'name': '规则引擎',
                'state': 'ok',
                'detail': 'deterministic',
              },
              {
                'kind': 'system',
                'name': '备用通道',
                'state': 'idle',
                'detail': 'standby',
              },
              {
                'kind': 'provider',
                'name': '本地 Ollama',
                'state': 'idle',
                'detail': 'daemon/model not ready',
              },
            ],
          },
        ],
      },
    ],
  };
}
