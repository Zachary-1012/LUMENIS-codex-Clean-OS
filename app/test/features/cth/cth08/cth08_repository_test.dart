import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/cth/cth08/cth08_repository.dart';

void main() {
  test(
    'current runtime envelope is blocked without applied scope and lineage binding',
    () async {
      final repository = CoreCth08Repository(
        client: _ContractClient(
          screenResponse: const {
            'ok': true,
            'screen': 'CTH-08',
            'binding': {'screen': 'CTH-08', 'bound': true},
            'sections': [
              {
                'type': 'cases',
                'items': [
                  {'id': 'CASE-221', 'title': 'Must stay hidden'},
                ],
              },
            ],
          },
        ),
      );

      await expectLater(
        repository.load(),
        throwsA(isA<Cth08BlockedException>()),
      );
    },
  );

  test(
    'accepts canonical server evidence and marks hostile rows partial',
    () async {
      final repository = CoreCth08Repository(
        client: _ContractClient(
          screenResponse: _response(
            'CTH-08',
            sections: {
              'type': 'cases',
              'items': [
                {
                  'id': 'CASE-1',
                  'title': '安全案例',
                  'summary': '可见摘要',
                  'state': 'open',
                  'risk': 'high',
                  'timeline': [
                    {'label': '观察', 'state': 'current', 'detail': '现场记录'},
                  ],
                  'evidence': [
                    _evidence('EV-SERVER-1'),
                    {'id': 'EV-FABRICATED', 'quote': 'not canonical'},
                    'EV-RAW-STRING',
                    _evidence('EV-CROSS-SCOPE', subjectId: 'SUBJECT-OTHER'),
                    {
                      ..._evidence('EV-BAD-INTEGRITY'),
                      'integrity': {
                        'status': 'tampered',
                        'version': 'evidence-v1',
                      },
                    },
                  ],
                },
              ],
            },
          ),
        ),
      );

      final result = await repository.load();
      expect(result.state, Cth08ContentState.partial);
      expect(result.cases, hasLength(1));
      expect(result.cases.single.evidence.map((item) => item.id), [
        'EV-SERVER-1',
      ]);
      expect(result.cases.single.evidence.single.integrityStatus, 'verified');
      expect(
        result.cases.single.evidence.single.integrityVersion,
        'evidence-v1',
      );
      expect(result.cases.single.evidence.single.scopeMode, 'GLOBAL_ALL');
      expect(result.cases.single.evidence.single.subjectId, isNull);
    },
  );

  test('focus binding and evidence require the exact subject scope', () async {
    final repository = CoreCth08Repository(
      client: _ContractClient(
        contextResponse: _focusContext('SUBJECT-42'),
        screenResponse: _response(
          'CTH-08',
          mode: 'FOCUS',
          subjectId: 'SUBJECT-42',
          sections: {
            'type': 'cases',
            'items': [
              {
                'id': 'CASE-FOCUS',
                'title': '聚焦案例',
                'summary': '聚焦范围',
                'state': 'open',
                'risk': 'medium',
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
        ),
      ),
    );

    final result = await repository.load();
    expect(result.state, Cth08ContentState.partial);
    expect(result.cases.single.evidence.single.id, 'EV-FOCUS-1');
    expect(result.cases.single.evidence.single.subjectId, 'SUBJECT-42');
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
    expect(screenId, 'CTH-08');
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
  required Map<String, dynamic> sections,
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
  'sections': [sections],
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
  'captured_at': '10:22',
  'integrity': {'status': 'verified', 'version': 'evidence-v1'},
  'scope': {
    'mode': mode,
    'domain_id': 'CTH',
    'product_id': 'CTH',
    'subject_id': subjectId,
    'scope_verified': true,
  },
};
