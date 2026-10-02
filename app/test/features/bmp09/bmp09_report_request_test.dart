import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/bmp09/bmp09_repository.dart';
import 'package:lumenis_app/features/bmp09/bmp09_screen.dart';
import 'package:lumenis_app/features/bmp09/bmp09_snapshot.dart';
import 'package:lumenis_app/features/bmp09/bmp09_view_model.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

void main() {
  for (final copy in _reportRequestCopies) {
    testWidgets(
      'BMP-09 describes temporary request preparation in ${copy.locale.languageCode}',
      (tester) async {
        final repository = _FakeBmp09Repository(_snapshot());
        await tester.pumpWidget(
          _app(
            Bmp09Screen(
              client: LumenisCoreClient(),
              repository: repository,
            ),
            locale: copy.locale,
          ),
        );
        await tester.pumpAndSettle();

        expect(find.text(copy.button), findsOneWidget);
        expect(find.text(copy.guard), findsOneWidget);
        await tester.ensureVisible(find.text(copy.button));
        await tester.tap(find.text(copy.button));
        await tester.pump();

        expect(find.text(copy.prepared), findsOneWidget);
        expect(repository.loadCount, 1);
      },
    );
  }

  testWidgets('BMP-09 keeps the request blocked without report:write', (
    tester,
  ) async {
    final repository = _FakeBmp09Repository(
      _snapshot(grantedPermissions: const {}),
    );
    await tester.pumpWidget(
      _app(
        Bmp09Screen(client: LumenisCoreClient(), repository: repository),
      ),
    );
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text(_reportRequestCopies.first.button));
    await tester.tap(find.text(_reportRequestCopies.first.button));
    await tester.pump();

    expect(find.text(_reportRequestCopies.first.blocked), findsOneWidget);
    expect(find.text(_reportRequestCopies.first.prepared), findsNothing);
    expect(repository.loadCount, 1);
  });

  testWidgets(
    'BMP-09 keeps the request blocked when scope evidence is unapproved',
    (tester) async {
      final repository = _FakeBmp09Repository(
        _snapshot(scopeApproved: false),
      );
      await tester.pumpWidget(
        _app(
          Bmp09Screen(client: LumenisCoreClient(), repository: repository),
        ),
      );
      await tester.pumpAndSettle();

      await tester.ensureVisible(find.text(_reportRequestCopies.first.button));
      await tester.tap(find.text(_reportRequestCopies.first.button));
      await tester.pump();

      expect(find.text(_reportRequestCopies.first.blocked), findsOneWidget);
      expect(find.text(_reportRequestCopies.first.prepared), findsNothing);
      expect(repository.loadCount, 1);
    },
  );

  test('refresh clears the in-memory report request state', () async {
    final repository = _FakeBmp09Repository(_snapshot());
    final viewModel = Bmp09ViewModel(repository: repository);
    addTearDown(viewModel.dispose);

    await viewModel.refresh();
    viewModel.stageReportRequest();

    expect(viewModel.actionState, Bmp09ActionState.staged);
    expect(repository.loadCount, 1);

    await viewModel.refresh();

    expect(viewModel.actionState, Bmp09ActionState.idle);
    expect(repository.loadCount, 2);
  });
}

Widget _app(Widget child, {Locale locale = const Locale('zh', 'CN')}) {
  return MaterialApp(
    theme: LumenisTheme.dark,
    locale: locale,
    supportedLocales: LumenisLocalizations.supportedLocales,
    localizationsDelegates: const [
      LumenisLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    home: Scaffold(body: child),
  );
}

Bmp09Snapshot _snapshot({
  bool scopeApproved = true,
  Set<String> grantedPermissions = const {'report:write'},
}) => Bmp09Snapshot(
  contractBound: true,
  dataState: 'READY',
  scope: const Bmp09Scope(
    mode: 'FOCUS',
    brandId: 'brand-a',
    displayNames: {
      'zh-CN': '示例品牌',
      'en': 'Example Brand',
      'ko': '예시 브랜드',
    },
  ),
  scopeApproved: scopeApproved,
  dimensions: const [],
  reports: const [],
  grantedPermissions: grantedPermissions,
);

class _FakeBmp09Repository implements Bmp09Repository {
  _FakeBmp09Repository(this.snapshot);

  final Bmp09Snapshot snapshot;
  int loadCount = 0;

  @override
  Future<Bmp09Snapshot> load() async {
    loadCount += 1;
    return snapshot;
  }
}

class _ReportRequestCopy {
  const _ReportRequestCopy({
    required this.locale,
    required this.button,
    required this.prepared,
    required this.blocked,
    required this.guard,
  });

  final Locale locale;
  final String button;
  final String prepared;
  final String blocked;
  final String guard;
}

const _reportRequestCopies = <_ReportRequestCopy>[
  _ReportRequestCopy(
    locale: Locale('zh', 'CN'),
    button: '准备评估报告请求',
    prepared:
        '评估报告请求仅在当前页面暂时准备；刷新或离开后会清除，尚未生成或写入任何报告。',
    blocked: '当前范围还不能准备评估报告请求；请先确认品牌范围与报告授权。',
    guard:
        '此操作只在当前页面暂时准备请求状态；刷新或离开页面后会清除，不会保存草稿，也不会生成或写入报告。',
  ),
  _ReportRequestCopy(
    locale: Locale('en'),
    button: 'Prepare report request',
    prepared:
        'Report request prepared temporarily on this page. Refreshing or leaving clears it; no report was generated or written.',
    blocked:
        'A report request cannot be prepared for the current brand scope or authorization state.',
    guard:
        'This only prepares a temporary request state on this page. Refreshing or leaving clears it; no draft is saved and no report is generated or written.',
  ),
  _ReportRequestCopy(
    locale: Locale('ko'),
    button: '평가 보고서 요청 준비',
    prepared:
        '평가 보고서 요청을 현재 페이지에 임시로 준비했습니다. 새로고침하거나 페이지를 나가면 지워지며 보고서를 생성하거나 기록하지 않았습니다.',
    blocked: '현재 브랜드 범위 또는 권한 상태에서는 평가 보고서 요청을 준비할 수 없습니다.',
    guard:
        '이 작업은 현재 페이지에 요청 상태를 임시로 준비할 뿐입니다. 새로고침하거나 페이지를 나가면 지워지고, 초안 저장이나 보고서 생성·기록은 이루어지지 않습니다.',
  ),
];
