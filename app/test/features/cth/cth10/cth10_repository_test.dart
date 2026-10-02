import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/cth/cth10/cth10_repository.dart';

void main() {
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
}) => {
  'ok': true,
  'screen': screen,
  'binding': {
    'screen': screen,
    'applied': true,
    'actor_scope': 'verified',
    'domain_id': 'CTH',
    'product_id': 'CTH',
    'context_mode': mode,
    'canonical_scope': mode,
    'scope_verified': true,
    'read_allowed': true,
    'global_all_granted': mode == 'GLOBAL_ALL',
    'subject_id': subjectId,
    'evidence_lineage': 'verified',
  },
  'sections': sections,
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
