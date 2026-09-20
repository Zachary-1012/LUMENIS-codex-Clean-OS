import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/cth/cth02/cth02_repository.dart';
import 'package:lumenis_app/features/cth/cth02/cth02_screen.dart';

void main() {
  testWidgets('loading keeps the business list hidden until it is ready', (
    tester,
  ) async {
    final pending = Completer<Cth02Directory>();
    await tester.pumpWidget(_app(_FakeRepository(() => pending.future)));

    expect(find.text('经营主体与关联信息'), findsNothing);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is Semantics && widget.properties.label == '正在查看 CTH 经营主体名单',
      ),
      findsOneWidget,
    );
    expect(find.text('SUBJ-PRIVATE-01'), findsNothing);
    _expectNoInternalCopy(tester);

    pending.complete(_directory());
    await tester.pumpAndSettle();
    expect(find.text('SUBJ-PRIVATE-01'), findsOneWidget);
  });

  testWidgets(
    'sign-in failure hides the list and does not expose server details',
    (tester) async {
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

      expect(find.textContaining('请重新登录'), findsOneWidget);
      expect(find.text('SUBJ-PRIVATE-01'), findsNothing);
      expect(find.text('主体敏感名称'), findsNothing);
      expect(find.text('DANGER-KEYWORD'), findsNothing);
      _expectNoInternalCopy(tester);
    },
  );

  testWidgets('all failure states use business copy without internal details', (
    tester,
  ) async {
    final failures = <Object>[
      const LumenisCoreException('denied', statusCode: 403),
      const LumenisCoreException('authorization unavailable', statusCode: 503),
      const LumenisCoreException('Core unavailable'),
      const FormatException('Subject Registry contract invalid'),
      StateError('raw internal server response'),
    ];

    for (final failure in failures) {
      await tester.pumpWidget(
        _app(_FakeRepository(() => Future.error(failure))),
      );
      await tester.pumpAndSettle();

      _expectNoInternalCopy(tester);
      _expectRestrictedValuesHidden(tester);
    }
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
      expect(find.textContaining('名单可见不代表可以查看名单内任一主体的经营数据'), findsOneWidget);
      expect(find.text('经营主体 → 业务单元'), findsOneWidget);
      expect(find.text('业务单元 → 品牌 / 业态'), findsOneWidget);
      expect(find.text('资料暂缺'), findsNWidgets(2));
      expect(find.text('NOT_COLLECTED'), findsNothing);
      _expectNoInternalCopy(tester);
      _expectRestrictedValuesHidden(tester);
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
    expect(find.text('经营主体 → 业务单元'), findsOneWidget);
    expect(find.text('业务单元 → 品牌 / 业态'), findsOneWidget);
    _expectNoInternalCopy(tester);
    expect(tester.takeException(), isNull);
  });

  testWidgets('empty list explains that no business subjects are listed', (
    tester,
  ) async {
    final emptyDirectory = Cth02Directory.fromResponse(
      _response(subjects: const []),
    );
    await tester.pumpWidget(_app(_FakeRepository(() async => emptyDirectory)));
    await tester.pumpAndSettle();

    expect(find.text('当前 CTH 经营主体名单中暂无主体。'), findsOneWidget);
    expect(find.text('资料暂缺'), findsNWidgets(2));
    _expectNoInternalCopy(tester);
    _expectRestrictedValuesHidden(tester);
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

void _expectNoInternalCopy(WidgetTester tester) {
  final renderedText = tester
      .widgetList<Text>(find.byType(Text))
      .map((widget) => widget.data ?? widget.textSpan?.toPlainText() ?? '')
      .join(' ');
  final semanticLabels = tester
      .widgetList<Semantics>(find.byType(Semantics))
      .map((widget) => widget.properties.label ?? '')
      .join(' ');
  final copy = '$renderedText $semanticLabels'.toLowerCase();

  for (final term in const [
    'subject',
    'core',
    'api',
    'contract',
    'evidence',
    'ownership',
    'not_collected',
    'permission',
    'unknown',
    'backend-gap',
    'source',
    'owner',
    'registry',
    'selection_only',
    'lumenis_subject_registry',
    '/api/',
    'http 401',
  ]) {
    expect(copy, isNot(contains(term)), reason: 'Visible copy leaked "$term".');
  }
}

void _expectRestrictedValuesHidden(WidgetTester tester) {
  final renderedText = tester
      .widgetList<Text>(find.byType(Text))
      .map((widget) => widget.data ?? widget.textSpan?.toPlainText() ?? '')
      .join(' ');
  final semanticLabels = tester
      .widgetList<Semantics>(find.byType(Semantics))
      .map((widget) => widget.properties.label ?? '')
      .join(' ');
  final copy = '$renderedText $semanticLabels'.toLowerCase();

  for (final value in const [
    'Sensitive Subject Name',
    'DANGER-KEYWORD',
    '2026-09-01T00:00:00Z',
    'raw internal server response',
  ]) {
    expect(find.textContaining(value), findsNothing);
    expect(copy, isNot(contains(value.toLowerCase())));
  }
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
