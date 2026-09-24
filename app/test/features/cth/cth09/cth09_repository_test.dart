import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/cth/cth09/cth09_repository.dart';

void main() {
  test('current risk response is blocked before rows are exposed', () async {
    final repository = CoreCth09Repository(
      client: _ContractClient(
        screenResponse: const {
          'ok': true,
          'screen': 'CTH-09',
          'binding': {'screen': 'CTH-09', 'bound': true},
          'sections': [
            {
              'type': 'risks',
              'items': [
                {'id': 'RISK-1', 'title': 'Must stay hidden'},
              ],
            },
          ],
        },
      ),
    );

    await expectLater(repository.load(), throwsA(isA<Cth09BlockedException>()));
  });

  test(
    'accepts canonical evidence and drops fabricated or cross-scope rows',
    () async {
      final repository = CoreCth09Repository(
        client: _ContractClient(
          screenResponse: _response(
            'CTH-09',
            sections: [
              {
                'type': 'risks',
                'items': [
                  {
                    'id': 'RISK-1',
                    'title': '安全风险',
                    'level': 'high',
                    'score': 68,
                    'summary': '可见摘要',
                    'evidence': [
                      _evidence('EV-SERVER-1'),
                      {'id': 'EV-FABRICATED'},
                      'EV-RAW-STRING',
                      _evidence('EV-CROSS-SCOPE', subjectId: 'SUBJECT-OTHER'),
                      {..._evidence('EV-MISSING-READ'), 'read_allowed': false},
                    ],
                  },
                ],
              },
              {
                'type': 'decisions',
                'items': [
                  {
                    'id': 'DEC-1',
                    'title': '增派引导',
                    'owner': '运营',
                    'status': 'pending',
                    'action_label': '准备排班方案',
                    'action_contract': {
                      'permission': 'verified',
                      'effect_fence': 'armed',
                      'result_contract': 'bound',
                      'callable': true,
                      'approval': 'required',
                    },
                    'evidence': [_evidence('EV-DECISION-1')],
                  },
                ],
              },
            ],
          ),
        ),
      );

      final result = await repository.load();
      expect(result.state, Cth09ContentState.partial);
      expect(result.risks.single.evidence.single.id, 'EV-SERVER-1');
      expect(result.risks.single.evidence.single.integrityStatus, 'verified');
      expect(
        result.risks.single.evidence.single.integrityVersion,
        'evidence-v1',
      );
      expect(result.decisions.single.evidence.single.id, 'EV-DECISION-1');
      expect(result.decisions.single.gate.exactContractBound, isFalse);
    },
  );

  test('focus evidence cannot cross the selected subject', () async {
    final repository = CoreCth09Repository(
      client: _ContractClient(
        contextResponse: _focusContext('SUBJECT-42'),
        screenResponse: _response(
          'CTH-09',
          mode: 'FOCUS',
          subjectId: 'SUBJECT-42',
          sections: [
            {
              'type': 'risks',
              'items': [
                {
                  'id': 'RISK-FOCUS',
                  'title': '聚焦风险',
                  'level': 'medium',
                  'score': 42,
                  'summary': '聚焦范围',
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
    expect(result.state, Cth09ContentState.partial);
    expect(result.risks.single.evidence.single.id, 'EV-FOCUS-1');
    expect(result.risks.single.evidence.single.subjectId, 'SUBJECT-42');
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
    expect(screenId, 'CTH-09');
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
