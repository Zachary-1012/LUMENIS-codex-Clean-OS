import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/features/ai03/ai03_repository.dart';
import 'package:lumenis_app/features/ai03/ai03_snapshot.dart';
import 'package:lumenis_app/features/ai03/ai03_view_model.dart';

void main() {
  test(
    'AI-03 accepts only typed canonical Evidence v2 in the exact context',
    () {
      final response = _baseResponse();
      response['thread'] = [
        {
          'role': 'assistant',
          'text': '结论需要回到来源核验。',
          'citations': [
            {
              'evidence': _evidenceV2(),
              'title': '公开资料',
              'passage': '返回的原文段落',
            },
            {'id': 'EV-101', 'title': 'legacy bare id'},
          ],
        },
      ];

      final snapshot = Ai03Snapshot.fromResponse(response);

      expect(snapshot.isBound, isTrue);
      expect(snapshot.hasEvidence, isTrue);
      expect(snapshot.thread.single.citations, hasLength(1));
      expect(snapshot.thread.single.citations.single.id, 'EV-100');
      expect(snapshot.thread.single.citations.single.title, '公开资料');
    },
  );

  test('AI-03 rejects legacy, fabricated, and missing-integrity citations', () {
    final response = _baseResponse();
    response['thread'] = [
      {
        'role': 'assistant',
        'text': '只保留可核验的来源。',
        'citations': [
          'EV-legacy-string',
          {'id': 'EV-fabricated'},
          {
            'evidence': {
              ..._evidenceV2(),
              'evidence_version': 1,
            },
          },
          {
            'evidence': {
              ..._evidenceV2(),
              'integrity': null,
            },
          },
        ],
      },
    ];

    final snapshot = Ai03Snapshot.fromResponse(response);

    expect(snapshot.hasEvidence, isFalse);
    expect(snapshot.thread.single.citations, isEmpty);
  });

  test('AI-03 rejects a typed Evidence v2 record from another Subject', () {
    final response = _baseResponse();
    response['thread'] = [
      {
        'role': 'assistant',
        'text': '跨主体来源不可见。',
        'citations': [
          {'evidence': _evidenceV2(subjectId: 'subject-other')},
        ],
      },
    ];

    final snapshot = Ai03Snapshot.fromResponse(response);

    expect(snapshot.thread.single.citations, isEmpty);
    expect(snapshot.hasEvidence, isFalse);
  });

  test('AI-03 retains an honest empty thread for an unbound screen', () {
    final snapshot = Ai03Snapshot.fromResponse({
      'ok': true,
      'screen': 'AI-03',
      'source': 'runtime',
      'bound': false,
      'binding': {
        'blocked': ['trace'],
      },
    });

    expect(snapshot.bindingState, Ai03BindingState.blocked);
    expect(snapshot.thread, isEmpty);
    expect(snapshot.hasEvidence, isFalse);
  });

  test('AI-03 ignores a delayed success after disposal', () async {
    final repository = _ControlledAi03Repository();
    final viewModel = Ai03ViewModel(repository: repository);
    final refresh = viewModel.refresh();

    expect(repository.pending, hasLength(1));
    viewModel.dispose();
    repository.pending.single.complete(_ai03Snapshot('过期结果'));

    await expectLater(refresh, completes);
    expect(viewModel.snapshot, isNull);
    expect(viewModel.phase, Ai03LoadPhase.loading);
  });

  test('AI-03 ignores a delayed failure after disposal', () async {
    final repository = _ControlledAi03Repository();
    final viewModel = Ai03ViewModel(repository: repository);
    final refresh = viewModel.refresh();

    expect(repository.pending, hasLength(1));
    viewModel.dispose();
    repository.pending.single.completeError(StateError('HTTP 403'));

    await expectLater(refresh, completes);
    expect(viewModel.failureKind, isNull);
    expect(viewModel.phase, Ai03LoadPhase.loading);
  });

  test('AI-03 keeps the latest overlapping refresh result', () async {
    final repository = _ControlledAi03Repository();
    final viewModel = Ai03ViewModel(repository: repository);
    final olderRefresh = viewModel.refresh();
    final latestRefresh = viewModel.refresh();

    expect(repository.pending, hasLength(2));
    repository.pending[1].complete(_ai03Snapshot('最新结果'));
    await latestRefresh;
    repository.pending[0].completeError(StateError('HTTP 403'));
    await olderRefresh;

    expect(viewModel.phase, Ai03LoadPhase.ready);
    expect(viewModel.failureKind, isNull);
    expect(viewModel.snapshot?.thread.single.text, '最新结果');
    viewModel.dispose();
  });

  test('AI-03 ignores citation selection after disposal', () async {
    final repository = _ControlledAi03Repository();
    final viewModel = Ai03ViewModel(repository: repository);
    final refresh = viewModel.refresh();

    repository.pending.single.complete(_ai03SnapshotWithCitation());
    await refresh;
    final citationId = viewModel.snapshot!.thread.single.citations.single.id;
    viewModel.dispose();

    expect(() => viewModel.selectCitation(citationId), returnsNormally);
    expect(viewModel.selectedCitationId, isNull);
  });
}

class _ControlledAi03Repository implements Ai03Repository {
  final List<Completer<Ai03Snapshot>> pending = [];

  @override
  Future<Ai03Snapshot> load() {
    final completer = Completer<Ai03Snapshot>();
    pending.add(completer);
    return completer.future;
  }
}

Ai03Snapshot _ai03Snapshot(String text) => Ai03Snapshot.fromResponse({
  ..._baseResponse(),
  'thread': [
    {'role': 'assistant', 'text': text, 'citations': []},
  ],
});

Ai03Snapshot _ai03SnapshotWithCitation() => Ai03Snapshot.fromResponse({
  ..._baseResponse(),
  'thread': [
    {
      'role': 'assistant',
      'text': '来源锚点可供检查。',
      'citations': [
        {'evidence': _evidenceV2(), 'title': '公开资料'},
      ],
    },
  ],
});

Map<String, dynamic> _baseResponse() => {
  'ok': true,
  'screen': 'AI-03',
  'source': 'runtime',
  'bound': true,
  'context': {
    'mode': 'FOCUS',
    'domain_id': 'CTH',
    'subject_id': 'subject-1',
  },
};

Map<String, dynamic> _evidenceV2({String subjectId = 'subject-1'}) => {
  'evidence_id': 'EV-100',
  'evidence_version': 2,
  'type': 'METRIC',
  'canonical': true,
  'scope_verified': true,
  'scope': {
    'mode': 'FOCUS',
    'domain_id': 'CTH',
    'subject_id': subjectId,
    'global': false,
  },
  'permission': {'read': true, 'decision': 'ALLOW'},
  'read_allowed': true,
  'lineage': ['Comment', 'Canonical', 'Metric'],
  'lineage_verified': true,
  'integrity': {
    'version': 2,
    'status': 'verified',
    'verified': true,
    'algorithm': 'sha256',
    'digest': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
  },
  'quote': '返回的原文段落',
};
