import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/cth/cth02/cth02_repository.dart';
import 'package:lumenis_app/features/cth/cth02/cth02_screen.dart';

void main() {
  testWidgets(
    'loading reveals no Subject data before the scoped read returns',
    (tester) async {
      final pending = Completer<Cth02Directory>();
      await tester.pumpWidget(_app(_FakeRepository(() => pending.future)));

      expect(find.text('主体档案与归属关系'), findsNothing);
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.text('SUBJ-PRIVATE-01'), findsNothing);

      pending.complete(_directory());
      await tester.pumpAndSettle();
      expect(find.text('SUBJ-PRIVATE-01'), findsOneWidget);
    },
  );

  testWidgets('unauthenticated response hides all Subject metadata', (
    tester,
  ) async {
    await tester.pumpWidget(
      _app(
        _FakeRepository(
          () => Future.error(
            const LumenisCoreException(
              'GET /api/settings/subjects?domain_id=CTH failed with HTTP 401',
              statusCode: 401,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('需要有效账号身份'), findsOneWidget);
    expect(find.text('SUBJ-PRIVATE-01'), findsNothing);
    expect(find.text('主体敏感名称'), findsNothing);
    expect(find.text('DANGER-KEYWORD'), findsNothing);
  });

  testWidgets(
    'desktop shows only registry metadata and uncollected relations',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 1000));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(_app(_FakeRepository(() async => _directory())));
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('cth02/desktop-layout')),
        findsOneWidget,
      );
      expect(find.text('主体敏感名称'), findsOneWidget);
      expect(find.text('SUBJ-PRIVATE-01'), findsOneWidget);
      expect(find.text('商业主体'), findsOneWidget);
      expect(find.text('服装零售'), findsOneWidget);
      expect(find.text('Subject → 业务单元'), findsOneWidget);
      expect(find.text('业务单元 → 品牌 / 业态'), findsOneWidget);
      expect(find.text('NOT_COLLECTED'), findsNWidgets(2));
      expect(find.text('DANGER-KEYWORD'), findsNothing);
      expect(find.text('2026-09-01T00:00:00Z'), findsNothing);
      expect(find.text('当前 Subject'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('mobile stacks the directory before the relationship state', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_FakeRepository(() async => _directory())));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('cth02/mobile-layout')), findsOneWidget);
    expect(find.text('主体敏感名称'), findsOneWidget);
    expect(find.text('业务单元 → 品牌 / 业态'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  test('directory parser requires a CTH selection-only registry response', () {
    expect(
      () => Cth02Directory.fromResponse(_response(selectionOnly: false)),
      throwsFormatException,
    );
    expect(
      () => Cth02Directory.fromResponse(_response(subjectDomain: 'BMP')),
      throwsFormatException,
    );
  });

  test('an authenticated empty CTH registry remains an empty directory', () {
    final directory = Cth02Directory.fromResponse(
      _response(subjects: const []),
    );
    expect(directory.subjects, isEmpty);
  });
}

Widget _app(Cth02Repository repository) => MaterialApp(
  theme: LumenisTheme.dark,
  home: Scaffold(
    body: Cth02Screen(client: LumenisCoreClient(), repository: repository),
  ),
);

class _FakeRepository implements Cth02Repository {
  const _FakeRepository(this.load);

  final Future<Cth02Directory> Function() load;

  @override
  Future<Cth02Directory> loadDirectory() => load();
}

Cth02Directory _directory() => Cth02Directory.fromResponse(_response());

Map<String, dynamic> _response({
  bool selectionOnly = true,
  String subjectDomain = 'CTH',
  List<Map<String, dynamic>>? subjects,
}) => {
  'ok': true,
  'source': 'lumenis_subject_registry',
  'selection_only': selectionOnly,
  'domains': [
    {'id': 'CTH', 'name': '商业运营', 'product': 'CTH'},
  ],
  'subject_types': [
    {'id': 'company', 'name': '商业主体'},
  ],
  'subjects':
      subjects ??
      [
        {
          'subject_id': 'SUBJ-PRIVATE-01',
          'domain_id': subjectDomain,
          'subject_type': 'company',
          'subject_type_name': '商业主体',
          'name_zh': '主体敏感名称',
          'name_en': 'Sensitive Subject Name',
          'industry': '服装零售',
          'keywords': ['DANGER-KEYWORD'],
          'created_at': '2026-09-01T00:00:00Z',
        },
      ],
};
