import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/features/shared/sh02/sh02_snapshot.dart';

const scope = Sh02Scope(
  mode: Sh02ScopeMode.globalAll,
  domain: null,
  focusId: null,
  displayName: 'All',
);

Map<String, dynamic> row() => {
  'id': 'canonical:source-1',
  'kind': 'COLLECTED_SOURCE',
  'summary': 'Research on public APIs',
  'source': 'public_http',
  'lineage': ['SOURCE', 'EVIDENCE'],
  'projection': {
    'contract': 'lumenis.shared.experience-row-projection',
    'version': 3,
    'purpose': 'SOURCE_INSPECTION',
    'read_allowed': true,
    'scope': {'mode': 'GLOBAL_ALL', 'global_all_granted': true},
    'canonical_reference': 'canonical:source-1',
    'stored_scope': {
      'product_id': 'CTH',
      'domain_id': 'cth',
      'scope_status': 'UNASSIGNED',
      'global': true,
      'subject_id': null,
      'brand_focus_id': null,
    },
    'evidence': {
      'source_id': 'source-1',
      'evidence_id': '18',
      'canonical_reference': 'evidence:collector:18',
    },
    'integrity': {
      'verified': true,
      'lineage_verified': true,
      'assurance': 'writer-authenticated',
    },
  },
  'inspection': {
    'contract': 'lumenis.collected-source-inspection/v1',
    'source_id': 'source-1',
    'evidence_ref': 'app_evidence_records:18',
    'scope_status': 'UNASSIGNED',
    'source_use': {
      'state': 'CHECK_SOURCE_USE_PER_ACTION',
      'grants_source_use': false,
    },
    'original': {
      'endpoint': '/api/experience/cth/platform-collection/results',
      'query': {
        'evidence_ref': 'app_evidence_records:18',
        'source_id': 'source-1',
      },
      'scope': {'mode': 'GLOBAL_ALL', 'domain_id': 'CTH'},
    },
    'collection_task': {
      'task_id': 5,
      'endpoint': '/api/experience/cth/platform-collection/tasks/5',
      'scope': {'mode': 'GLOBAL_ALL', 'domain_id': 'CTH'},
    },
  },
};

void main() {
  test(
    'collected source keeps inspection identity without claiming a focused fact',
    () {
      final item = Sh02Evidence.tryParse(row(), scope: scope)!;
      expect(item.summary, 'Research on public APIs');
      expect(item.kind, Sh02EvidenceKind.source);
      expect(item.lineage, ['来源', '资料依据']);
      expect(item.inspection!.taskId, 5);
      expect(item.inspection!.evidenceRef, 'app_evidence_records:18');
      expect(
        Sh02Evidence.tryParse(
          row(),
          scope: const Sh02Scope(
            mode: Sh02ScopeMode.focus,
            domain: 'CTH',
            focusId: 'different',
            displayName: 'Other',
          ),
        ),
        isNull,
      );
    },
  );

  test(
    'inspection rejects mismatched source, grants, task or unverified custody',
    () {
      for (final mutate in <void Function(Map<String, dynamic>)>[
        (r) => r['projection']['integrity']['assurance'] =
            'content-integrity-only',
        (r) => r['projection']['stored_scope']['subject_id'] = 'unrelated',
        (r) => r['inspection']['original']['query']['source_id'] = 'different',
        (r) => r['inspection']['source_use']['grants_source_use'] = true,
        (r) => r['inspection']['collection_task']['scope']['domain_id'] = 'BMP',
        (r) => r['projection']['evidence']['evidence_id'] = '19',
        (r) => r['projection']['read_allowed'] = false,
      ]) {
        final value = jsonDecode(jsonEncode(row())) as Map<String, dynamic>;
        mutate(value);
        expect(Sh02Evidence.tryParse(value, scope: scope), isNull);
      }
    },
  );
}
