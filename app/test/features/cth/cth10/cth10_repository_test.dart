import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/cth/cth10/cth10_repository.dart';

void main() {
  test(
    'source brief keeps the exact validated report and Evidence snapshot',
    () async {
      final result = await CoreCth10Repository(
        client: _ContractClient(screenResponse: _sourceBriefResponse()),
      ).load();
      final brief = result.reports.single.sourceBrief!;
      expect(brief.records.single['title'], '实际交付稿');
      expect(brief.sample['returned_verified_count'], 1);
      expect(brief.coverage, 'UNKNOWN');
      expect(result.reports.single.blocks.single.body, _briefBody);
    },
  );

  for (final mutation in <String, void Function(Map<String, dynamic>)>{
    'hash': (brief) => brief['content_hash'] = List.filled(64, 'b').join(),
    'body': (brief) => brief['markdown'] = '# Different body',
    'scope': (brief) => (brief['scope'] as Map)['subject_id'] = 'FOREIGN',
    'Evidence': (brief) =>
        ((brief['records'] as List).single as Map)['evidence_id'] = '2',
    'count': (brief) => (brief['sample'] as Map)['returned_verified_count'] = 2,
  }.entries) {
    test(
      'source brief with mismatched ${mutation.key} never falls back to diagnostic text',
      () async {
        final response = _sourceBriefResponse();
        mutation.value(response['source_brief'] as Map<String, dynamic>);
        final result = await CoreCth10Repository(
          client: _ContractClient(screenResponse: response),
        ).load();
        expect(result.state, Cth10ContentState.partial);
        expect(result.reports, isEmpty);
      },
    );
  }

  test(
    'verified report paragraphs and quotations retain their full text',
    () async {
      final body = List.filled(40, '运营记录需要连同变化原因与后续安排一起阅读。').join('\n');
      final quote = List.filled(30, '现场记录中的完整原文，保留限定条件。').join('\n');
      final repository = CoreCth10Repository(
        client: _ContractClient(
          screenResponse: _response(
            'CTH-10',
            sections: [
              {
                'type': 'reports',
                'items': [
                  {
                    'id': 'REPORT-LONG',
                    'title': '完整运营记录',
                    'period': '近7天',
                    'state': 'confirmed',
                    'scope': 'GLOBAL / ALL',
                    'blocks': [
                      {'id': 'BLOCK-LONG', 'title': '运营记录', 'body': body},
                    ],
                    'evidence': [
                      {..._evidence('EV-LONG'), 'quote': quote},
                    ],
                  },
                ],
              },
            ],
          ),
        ),
      );

      final result = await repository.load();
      expect(result.state, Cth10ContentState.ready);
      expect(result.reports.single.blocks.single.body, body);
      expect(result.reports.single.evidence.single.quote, quote);
    },
  );

  test(
    'withheld malformed or sensitive blocks make the report partial',
    () async {
      final repository = CoreCth10Repository(
        client: _ContractClient(
          screenResponse: _response(
            'CTH-10',
            sections: [
              {
                'type': 'reports',
                'items': [
                  {
                    'id': 'REPORT-PARTIAL',
                    'title': '部分运营记录',
                    'period': '近7天',
                    'scope': 'GLOBAL / ALL',
                    'blocks': [
                      {'id': 'VISIBLE', 'title': '可读部分', 'body': '已核验内容'},
                      'invalid block',
                      {
                        'id': 'WITHHELD',
                        'title': '内部记录',
                        'body': 'api_key=private',
                      },
                    ],
                    'evidence': [_evidence('EV-PARTIAL')],
                  },
                ],
              },
            ],
          ),
        ),
      );

      final result = await repository.load();
      expect(result.state, Cth10ContentState.partial);
      expect(result.reports.single.blocks.single.id, 'VISIBLE');
    },
  );

  test(
    'current report response is blocked without applied scope binding',
    () async {
      final repository = CoreCth10Repository(
        client: _ContractClient(
          screenResponse: const {
            'ok': true,
            'screen': 'CTH-10',
            'binding': {
              'screen': 'CTH-10',
              'bound': true,
              'actor_scope': 'verified',
              'domain': 'CTH',
              'context_mode': 'GLOBAL_ALL',
              'evidence_lineage': 'verified',
            },
            'sections': [
              {
                'type': 'reports',
                'items': [
                  {'id': 'REPORT-1', 'title': 'Must stay hidden'},
                ],
              },
            ],
          },
        ),
      );

      await expectLater(
        repository.load(),
        throwsA(isA<Cth10BlockedException>()),
      );
    },
  );

  test(
    'accepts only canonical report sources and marks the page partial',
    () async {
      final repository = CoreCth10Repository(
        client: _ContractClient(
          screenResponse: _response(
            'CTH-10',
            sections: [
              {
                'type': 'reports',
                'items': [
                  {
                    'id': 'REPORT-1',
                    'title': '安全报告',
                    'period': '近7天',
                    'state': 'confirmed',
                    'scope': 'GLOBAL / ALL',
                    'blocks': [
                      {
                        'id': 'BLOCK-1',
                        'title': '结论',
                        'kind': 'conclusion',
                        'body': '可见摘要',
                        'status': 'confirmed',
                      },
                    ],
                    'evidence': [
                      _evidence('EV-SERVER-1'),
                      {'id': 'EV-FABRICATED', 'quote': 'not canonical'},
                      'EV-RAW-STRING',
                      _evidence('EV-CROSS-SCOPE', subjectId: 'SUBJECT-OTHER'),
                    ],
                  },
                ],
              },
            ],
          ),
        ),
      );

      final result = await repository.load();
      expect(result.state, Cth10ContentState.partial);
      expect(result.reports.single.title, '安全报告');
      expect(result.reports.single.evidence.single.id, 'EV-SERVER-1');
      expect(result.reports.single.evidence.single.integrityStatus, 'verified');
      expect(result.reports.single.evidence.single.scopeMode, 'GLOBAL_ALL');
    },
  );

  for (final policy in ['local-workspace-read-v1', 'actor-exact-scope-v1']) {
    for (final mode in ['FOCUS', 'GLOBAL_ALL']) {
      test(
        'canonical $policy read preserves exact $mode report and Evidence',
        () async {
          final subject = mode == 'FOCUS' ? 'SUBJECT-42' : null;
          final response = _response(
            'CTH-10',
            mode: mode,
            subjectId: subject,
            policy: policy,
            actorScope: policy == 'local-workspace-read-v1'
                ? 'anonymous_read'
                : 'authenticated',
            sections: [_readableReport(mode: mode, subjectId: subject)],
          );
          final repository = CoreCth10Repository(
            client: _ContractClient(
              contextResponse: subject == null
                  ? _globalContext
                  : _focusContext(subject),
              screenResponse: response,
            ),
          );
          final result = await repository.load();
          expect(result.state, Cth10ContentState.ready);
          expect(result.reports.single.blocks.single.body, '保留当前来源正文。');
          expect(result.reports.single.evidence.single.quote, '已核验');
          expect(result.reports.single.evidence.single.subjectId, subject);
          final binding = response['binding'] as Map;
          expect(
            binding['actor_scope'],
            policy == 'local-workspace-read-v1'
                ? 'anonymous_read'
                : 'authenticated',
          );
          expect(
            binding['global_all_granted'],
            mode == 'GLOBAL_ALL' && policy == 'actor-exact-scope-v1',
          );
        },
      );
    }
  }

  for (final (name, delta) in <(String, Map<String, Object?>)>[
    ('unknown policy', {'policy': 'unknown-read'}),
    ('missing policy', {'policy': null}),
    ('unknown actor state', {'actor_scope': 'verified'}),
    ('missing actor state', {'actor_scope': null}),
    ('local policy with account actor', {'actor_scope': 'authenticated'}),
    ('account policy with anonymous actor', {'policy': 'actor-exact-scope-v1'}),
    ('wrong contract', {'contract': 'lumenis.context.v1'}),
    ('missing contract', {'contract': null}),
    ('wrong module', {'module': 'reports'}),
    ('missing module', {'module': null}),
    ('denied read', {'read_allowed': false}),
    ('unverified scope', {'scope_verified': false}),
    ('unverified Evidence', {'evidence_lineage': 'unverified'}),
    ('wrong subject', {'subject_id': 'SUBJECT-OTHER'}),
    ('wrong domain', {'domain_id': 'BMP'}),
    ('wrong product', {'product_id': 'ZBMP'}),
    ('wrong context mode', {'context_mode': 'GLOBAL_ALL'}),
    ('wrong canonical scope', {'canonical_scope': 'GLOBAL_ALL'}),
    ('unapplied binding', {'applied': false}),
    ('focus claiming a global grant', {'global_all_granted': true}),
  ]) {
    test('$name cannot expose the focused report', () async {
      final response = _response(
        'CTH-10',
        mode: 'FOCUS',
        subjectId: 'SUBJECT-42',
        sections: [_readableReport(mode: 'FOCUS', subjectId: 'SUBJECT-42')],
      );
      (response['binding'] as Map<String, dynamic>).addAll(delta);
      final repository = CoreCth10Repository(
        client: _ContractClient(
          contextResponse: _focusContext('SUBJECT-42'),
          screenResponse: response,
        ),
      );
      await expectLater(
        repository.load(),
        throwsA(isA<Cth10BlockedException>()),
      );
    });
  }

  for (final (name, policy, actor, delta)
      in <(String, String, String, Map<String, Object?>)>[
        (
          'local read cannot claim an account global grant',
          'local-workspace-read-v1',
          'anonymous_read',
          {'global_all_granted': true},
        ),
        (
          'account global read needs its grant',
          'actor-exact-scope-v1',
          'authenticated',
          {'global_all_granted': false},
        ),
        (
          'global read cannot carry a subject',
          'local-workspace-read-v1',
          'anonymous_read',
          {'subject_id': 'SUBJECT-42'},
        ),
      ]) {
    test(name, () async {
      final response = _response(
        'CTH-10',
        policy: policy,
        actorScope: actor,
        sections: [_readableReport()],
      );
      (response['binding'] as Map<String, dynamic>).addAll(delta);
      final repository = CoreCth10Repository(
        client: _ContractClient(screenResponse: response),
      );
      await expectLater(
        repository.load(),
        throwsA(isA<Cth10BlockedException>()),
      );
    });
  }

  test('focus report source must match the selected subject exactly', () async {
    final repository = CoreCth10Repository(
      client: _ContractClient(
        contextResponse: _focusContext('SUBJECT-42'),
        screenResponse: _response(
          'CTH-10',
          mode: 'FOCUS',
          subjectId: 'SUBJECT-42',
          sections: [
            {
              'type': 'reports',
              'items': [
                {
                  'id': 'REPORT-FOCUS',
                  'title': '聚焦报告',
                  'period': '近7天',
                  'state': 'draft',
                  'scope': 'FOCUS',
                  'blocks': [
                    {
                      'id': 'BLOCK-FOCUS',
                      'title': '结论',
                      'kind': 'conclusion',
                      'body': '聚焦摘要',
                      'status': 'draft',
                    },
                  ],
                  'evidence': [
                    _evidence(
                      'EV-FOCUS-1',
                      mode: 'FOCUS',
                      subjectId: 'SUBJECT-42',
                    ),
                    _evidence(
                      'EV-OTHER-1',
                      mode: 'FOCUS',
                      subjectId: 'SUBJECT-OTHER',
                    ),
                  ],
                },
              ],
            },
          ],
        ),
      ),
    );

    final result = await repository.load();
    expect(result.state, Cth10ContentState.partial);
    expect(result.reports.single.evidence.single.id, 'EV-FOCUS-1');
    expect(result.reports.single.evidence.single.subjectId, 'SUBJECT-42');
  });
}

const _briefBody = '# 来源简报\n- 覆盖：UNKNOWN\n- 范围：全部获准主体';

Map<String, dynamic> _sourceBriefResponse() {
  final hash = List.filled(64, 'a').join();
  return {
    ..._response(
      'CTH-10',
      sections: [
        {
          'type': 'reports',
          'items': [
            {
              'id': 'source-brief:$hash',
              'title': '资料来源简报',
              'period': '当前已收录资料',
              'scope': '全部获准主体',
              'state': 'derived_preview_not_saved',
              'blocks': [
                {
                  'id': 'source-summary',
                  'title': '来源与覆盖',
                  'kind': 'source_brief',
                  'body': _briefBody,
                  'status': 'AVAILABLE',
                },
              ],
              'evidence': [_evidence('evidence:canonical:1')],
            },
          ],
        },
      ],
    ),
    'source_brief': {
      'content_hash': hash,
      'markdown': _briefBody,
      'status': 'AVAILABLE',
      'coverage': 'UNKNOWN',
      'freshness': 'UNKNOWN',
      'collection_state': 'UNKNOWN',
      'scope': {
        'product_id': 'CTH',
        'domain_id': 'cth',
        'global': true,
        'subject_id': null,
        'brand_focus_id': null,
        'entity_label': '全部获准主体',
      },
      'sample': {
        'returned_verified_count': 1,
        'candidate_count': 1,
        'scanned_count': 1,
        'rejected_count': 0,
        'withheld_count': 0,
        'truncated': false,
        'withheld': false,
        'source_type_counts_sample': {'document': 1},
        'platform_counts_sample': {'UNKNOWN': 1},
      },
      'records': [
        {
          'source_id': 'document:original',
          'title': '实际交付稿',
          'evidence_id': '1',
          'scope_evidence_ref': '1',
          'subject_id': 'SUBJECT-1',
          'source_type': 'document',
          'source_platform': 'UNKNOWN',
          'publish_datetime': null,
          'captured_at': '2026-10-25',
          'source_url': null,
          'source_link_status': 'UNKNOWN',
        },
      ],
    },
  };
}

class _ContractClient extends LumenisCoreClient {
  _ContractClient({
    required this.screenResponse,
    this.contextResponse = _globalContext,
  });

  final Map<String, dynamic> screenResponse;
  final Map<String, dynamic> contextResponse;

  @override
  Future<Map<String, dynamic>> settingsContext() async => contextResponse;

  @override
  Future<Map<String, dynamic>> screen(String screenId) async {
    expect(screenId, 'CTH-10');
    return screenResponse;
  }
}

const _globalContext = <String, dynamic>{
  'ok': true,
  'contract': 'lumenis.context.v1',
  'selection_only': true,
  'context': {'mode': 'GLOBAL_ALL', 'domain_id': null, 'subject_id': null},
};

Map<String, dynamic> _focusContext(String subjectId) => {
  'ok': true,
  'contract': 'lumenis.context.v1',
  'selection_only': true,
  'context': {'mode': 'FOCUS', 'domain_id': 'CTH', 'subject_id': subjectId},
};

Map<String, dynamic> _response(
  String screen, {
  required List<Map<String, dynamic>> sections,
  String mode = 'GLOBAL_ALL',
  String? subjectId,
  String policy = 'local-workspace-read-v1',
  String actorScope = 'anonymous_read',
}) => {
  'ok': true,
  'screen': screen,
  'binding': {
    'screen': screen,
    'contract': 'lumenis.scope-read-binding.v1',
    'module': 'commercial_realtime_stream',
    'policy': policy,
    'applied': true,
    'actor_scope': actorScope,
    'domain_id': 'CTH',
    'product_id': 'CTH',
    'context_mode': mode,
    'canonical_scope': mode,
    'scope_verified': true,
    'read_allowed': true,
    'global_all_granted':
        mode == 'GLOBAL_ALL' && policy == 'actor-exact-scope-v1',
    'subject_id': subjectId,
    'evidence_lineage': 'verified',
  },
  'sections': sections,
};

Map<String, dynamic> _readableReport({
  String mode = 'GLOBAL_ALL',
  String? subjectId,
}) => {
  'type': 'reports',
  'items': [
    {
      'id': 'REPORT-CURRENT',
      'title': '当前运营记录',
      'period': '近7天',
      'scope': mode,
      'blocks': [
        {'id': 'CURRENT-BLOCK', 'title': '正文', 'body': '保留当前来源正文。'},
      ],
      'evidence': [_evidence('EV-CURRENT', mode: mode, subjectId: subjectId)],
    },
  ],
};

Map<String, dynamic> _evidence(
  String ref, {
  String mode = 'GLOBAL_ALL',
  String? subjectId,
}) => {
  'canonical_ref': ref,
  'canonical': true,
  'read_allowed': true,
  'quote': '已核验',
  'captured_at': '09:09',
  'integrity': {'status': 'verified', 'version': 'evidence-v1'},
  'scope': {
    'mode': mode,
    'domain_id': 'CTH',
    'product_id': 'CTH',
    'subject_id': subjectId,
    'scope_verified': true,
  },
};
