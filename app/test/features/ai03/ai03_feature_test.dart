import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/features/ai03/ai03_snapshot.dart';

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
}

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
