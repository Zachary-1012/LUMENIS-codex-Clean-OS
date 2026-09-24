import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/ai04/ai04_repository.dart';
import 'package:lumenis_app/features/ai04/ai04_screen.dart';
import 'package:lumenis_app/features/ai04/ai04_snapshot.dart';
import 'package:lumenis_app/features/ai04/ai04_view_model.dart';

import '../shared/shared_test_support.dart';

void main() {
  test('AI-04 shows only versioned, bound and non-deprecated skills', () {
    final snapshot = Ai04Snapshot.fromResponse({
      'ok': true,
      'skills': [
        _skill(),
        {..._skill(), 'implementation_state': 'UNBOUND'},
        {..._skill(), 'version': 'latest'},
        {..._skill(), 'description': 'provider=secret /private/path'},
      ],
    });

    expect(snapshot.state, Ai04CatalogState.ready);
    expect(snapshot.skills, hasLength(1));
    expect(snapshot.skills.single.owner, 'Shared Capability');
    expect(snapshot.rejectedCount, 3);
  });

  test(
    'AI-04 filter is read-only catalog state, not an install action',
    () async {
      final viewModel = Ai04ViewModel(repository: _FakeAi04Repository());
      addTearDown(viewModel.dispose);

      await viewModel.refresh();
      viewModel.updateFilter('research');

      expect(viewModel.filteredSkills, hasLength(1));
      expect(viewModel.filteredSkills.single.skillId, 'skill.research');
    },
  );

  testWidgets('AI-04 mobile catalog keeps the list viewport bounded', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      sharedTestApp(
        Ai04Screen(
          client: LumenisCoreClient(),
          repository: _FakeAi04Repository(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(TextField), findsOneWidget);
    expect(find.text('Research skill'), findsWidgets);
    expect(tester.takeException(), isNull);
  });
}

Map<String, dynamic> _skill({String id = 'skill.research'}) => {
  'skill_id': id,
  'name': 'Research skill',
  'description': 'Read-only research capability',
  'version': '1.2.0',
  'owner': 'Shared Capability',
  'category': 'research',
  'permission_level': 'READ',
  'risk_level': 'LOW',
  'execution_policy': 'READ_ONLY',
  'evaluation_status': 'EVALUATED',
  'input_hint': 'A verified Subject',
  'output_hint': 'A cited summary',
  'consumers': ['CTH', 'BMP'],
  'implementation_state': 'BOUND_RUNTIME',
  'binding': {'available': true},
};

class _FakeAi04Repository implements Ai04Repository {
  @override
  Future<Ai04Snapshot> load() async => Ai04Snapshot.fromResponse({
    'ok': true,
    'skills': [_skill()],
  });
}
