import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh01/manuscript_controller.dart';

Map<String, dynamic> response(String name) =>
    (jsonDecode(File('test/fixtures/creation/$name.json').readAsStringSync())
            as Map<String, dynamic>)['result']
        as Map<String, dynamic>;

void main() {
  for (final name in ['external-source', 'private-source']) {
    test(
      '$name: backend contract generates and independently reopens',
      () async {
        final client = _CreationClient(response(name));
        final controller = ManuscriptController(
          client: client,
          scope: const SharedWorkspaceScope(),
          draft: _draft,
        );
        addTearDown(controller.dispose);
        await controller.generate({
          'brief': {
            'title': 'A careful proposal',
            'question': 'Write a proposal',
            'language': 'en',
          },
        });
        expect(controller.errorCode, isNull);
        expect(controller.hasUnresolvedSave, isFalse);
        expect(client.runCalls, 1);
        final saved = controller.savedWork!;
        expect(saved.manuscript.authorship, 'assisted');
        expect(saved.revisionSections, hasLength(2));
        expect(saved.creationEvidence?['evidence_id'], isA<int>());
        expect(
          saved.citations,
          name == 'private-source' ? isEmpty : hasLength(1),
        );
        await controller.reopen(saved.artifactId);
        expect(controller.errorCode, isNull);
        expect(controller.savedWork?.artifactId, saved.artifactId);
        expect(controller.savedWork?.creationEvidence, saved.creationEvidence);
        expect(client.runCalls, 1);
      },
    );
  }

  for (final mutation in [
    'missing-evidence',
    'wrong-owner',
    'wrong-section',
    'unsupported-claim',
  ]) {
    test(
      'generated writing rejects $mutation without replacing draft',
      () async {
        final data = response('external-source');
        final work = data['work'] as Map<String, dynamic>;
        final payload = work['document']['payload'] as Map<String, dynamic>;
        switch (mutation) {
          case 'missing-evidence':
            data.remove('creation_evidence');
            work.remove('creation_evidence');
          case 'wrong-owner':
            payload['creation']['execution_evidence']['asset_id'] =
                'another-task';
          case 'wrong-section':
            data['revision_sections'][0]['body'] = 'Not this saved version';
          case 'unsupported-claim':
            payload['creation']['provenance']['product_acceptance'] = true;
        }
        final client = _CreationClient(data);
        final controller = ManuscriptController(
          client: client,
          scope: const SharedWorkspaceScope(),
          draft: _draft,
        );
        addTearDown(controller.dispose);
        await controller.generate({
          'brief': {
            'title': 'A careful proposal',
            'question': 'Write',
            'language': 'en',
          },
        });
        expect(controller.savedWork, isNull);
        expect(controller.errorCode, isNotNull);
        expect(controller.draft.toJson(), _draft.toJson());
        expect(controller.hasUnresolvedSave, isTrue);
      },
    );
  }
}

final _draft = InternalPitchManuscript(
  title: 'My existing writing',
  summary: 'My working notes',
  sections: [InternalPitchSection(heading: 'Notes', body: 'Keep this text.')],
  language: 'en',
  authorship: 'user_supplied',
);

class _CreationClient extends LumenisCoreClient {
  _CreationClient(this.data) : super(baseUrl: 'http://127.0.0.1:1');
  final Map<String, dynamic> data;
  int runCalls = 0;
  @override
  Future<Map<String, dynamic>> prepareGeneratedPitch({
    required LumenisWorkspaceScope scope,
    required Map<String, dynamic> generation,
    required String requestId,
    InternalPitchRevision? revision,
  }) async {
    data['work']['document']['request_id'] = requestId;
    return {
      'task_id': data['task_id'],
      'state': 'pending',
      'error': null,
      'scope': scope.toJson(),
    };
  }

  @override
  Future<Map<String, dynamic>> runInternalPitch({
    required String taskId,
    required LumenisWorkspaceScope scope,
  }) async {
    runCalls++;
    return data;
  }

  @override
  Future<Map<String, dynamic>> readInternalPitch({
    required String taskId,
    required LumenisWorkspaceScope scope,
  }) async => data;
  @override
  Future<Map<String, dynamic>> reopenSharedSavedManuscript({
    required SharedWorkspaceScope scope,
    required String artifactId,
  }) async => data['work'];
}
