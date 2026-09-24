import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/ai02/ai02_repository.dart';
import 'package:lumenis_app/features/ai02/ai02_screen.dart';
import 'package:lumenis_app/features/ai02/ai02_snapshot.dart';
import 'package:lumenis_app/features/ai02/ai02_view_model.dart';

import '../shared/shared_test_support.dart';

void main() {
  test(
    'AI-02 refuses VERIFIED_AVAILABLE without the governed execution proof',
    () {
      final snapshot = Ai02Snapshot.fromResponse({
        'ok': true,
        'screen': 'AI-02',
        'source': 'runtime',
        'bound': true,
        'sections': [
          {
            'type': 'stages',
            'items': [
              {'id': 'collect', 'label': '读取资料', 'state': 'completed'},
              {
                'id': 'bad',
                'label': 'provider=secret /private/path',
                'state': 'running',
              },
            ],
          },
        ],
        'evidence_refs': ['EV-100', '/private/evidence', 'CASE-12'],
        'actions': [
          {'id': 'fake', 'capability_status': 'AVAILABLE'},
          {'id': 'start', 'capability_status': 'VERIFIED_AVAILABLE'},
        ],
      });

      expect(snapshot.isBound, isTrue);
      expect(snapshot.steps, hasLength(1));
      expect(snapshot.evidenceRefs, ['EV-100', 'CASE-12']);
      expect(snapshot.hasExecutableRoute, isFalse);
      expect(snapshot.executionProof.actorBound, isFalse);
      expect(snapshot.executionProof.callableContract, isFalse);
    },
  );

  test(
    'AI-02 accepts a server-backed exact-scope permissioned execution proof',
    () {
      final snapshot = Ai02Snapshot.fromResponse(_permissionedResponse());

      expect(snapshot.hasExecutableRoute, isTrue);
      expect(snapshot.executionProof.ready, isTrue);
      expect(snapshot.executionProof.exactScope, isTrue);
      expect(snapshot.executionProof.readAllowed, isTrue);
      expect(snapshot.executionProof.executeAllowed, isTrue);
    },
  );

  test('AI-02 accepts GLOBAL_ALL only without a Subject identifier', () {
    final response = _permissionedResponse();
    response['scope'] = {
      'mode': 'GLOBAL_ALL',
      'domain_id': 'CTH',
      'authorized': true,
    };

    final snapshot = Ai02Snapshot.fromResponse(response);

    expect(snapshot.hasExecutableRoute, isTrue);
    expect(snapshot.executionProof.scopeMode, Ai02ScopeMode.globalAll);
    expect(snapshot.executionProof.scopeSubjectId, isNull);
  });

  test('AI-02 rejects GLOBAL_ALL carrying a focus Subject identifier', () {
    final response = _permissionedResponse();
    response['scope'] = {
      'mode': 'GLOBAL_ALL',
      'domain_id': 'CTH',
      'subject_id': 'subject-1',
      'authorized': true,
    };

    final snapshot = Ai02Snapshot.fromResponse(response);

    expect(snapshot.hasExecutableRoute, isFalse);
    expect(snapshot.executionProof.exactScope, isFalse);
  });

  test(
    'AI-02 view model keeps draft local and blocks unbound execution',
    () async {
      final viewModel = Ai02ViewModel(repository: _FakeAi02Repository());
      addTearDown(viewModel.dispose);

      await viewModel.refresh();
      viewModel.updateDraft('检查已返回的资料');

      expect(viewModel.draft, '检查已返回的资料');
      expect(viewModel.canStart, isFalse);
      expect(viewModel.blockedReason, contains('尚未绑定'));
    },
  );

  testWidgets('AI-02 enables start only when a real host action is connected', (
    tester,
  ) async {
    var started = false;
    await tester.pumpWidget(
      sharedTestApp(
        Ai02Screen(
          client: LumenisCoreClient(),
          repository: _FakeAi02Repository(
            snapshot: Ai02Snapshot.fromResponse(_permissionedResponse()),
          ),
          onStart: () => started = true,
        ),
      ),
    );
    await tester.pumpAndSettle();

    final button = tester.widget<FilledButton>(find.byType(FilledButton));
    expect(button.onPressed, isNotNull);
    await tester.tap(find.text('开始任务'));
    expect(started, isTrue);
  });

  testWidgets('AI-02 stays disabled when the host action is not connected', (
    tester,
  ) async {
    await tester.pumpWidget(
      sharedTestApp(
        Ai02Screen(
          client: LumenisCoreClient(),
          repository: _FakeAi02Repository(
            snapshot: Ai02Snapshot.fromResponse(_permissionedResponse()),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final button = tester.widget<FilledButton>(find.byType(FilledButton));
    expect(button.onPressed, isNull);
    expect(visibleSharedCopy(tester), contains('宿主尚未连接实际动作'));
  });
}

class _FakeAi02Repository implements Ai02Repository {
  _FakeAi02Repository({this._snapshot});

  final Ai02Snapshot? _snapshot;

  @override
  Future<Ai02Snapshot> load() async =>
      _snapshot ??
      const Ai02Snapshot(
        bindingState: Ai02BindingState.unavailable,
        steps: [],
        evidenceRefs: [],
        executionProof: Ai02ExecutionProof.unverified(),
        unavailableFields: ['task_steps'],
      );
}

Map<String, dynamic> _permissionedResponse() => {
  'ok': true,
  'screen': 'AI-02',
  'source': 'runtime',
  'bound': true,
  'actor': {'id': 'actor-1', 'bound': true, 'source': 'server'},
  'scope': {
    'mode': 'FOCUS',
    'domain_id': 'CTH',
    'subject_id': 'subject-1',
    'authorized': true,
  },
  'permission': {'read': true, 'execute': true, 'decision': 'ALLOW'},
  'evidence': {'lineage_verified': true, 'integrity_verified': true},
  'sections': [
    {
      'type': 'stages',
      'items': [
        {'id': 'collect', 'label': '读取资料', 'state': 'completed'},
      ],
    },
  ],
  'evidence_refs': ['EV-100'],
  'actions': [
    {
      'id': 'ai02.start',
      'capability_status': 'VERIFIED_AVAILABLE',
      'callable': {
        'available': true,
        'method': 'POST',
        'route': '/api/experience/ai/intent',
        'request_fields': ['task'],
        'response_fields': ['execution_id', 'status'],
      },
    },
  ],
};
