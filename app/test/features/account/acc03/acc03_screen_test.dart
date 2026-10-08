import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/account/acc03/acc03_repository.dart';
import 'package:lumenis_app/features/account/acc03/acc03_screen.dart';
import 'package:lumenis_app/features/account/acc03/acc03_snapshot.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

void main() {
  testWidgets(
    'Home opens the editable task draft and four business destinations',
    (tester) async {
      final client = _Client();
      final repository = _UnusedRepository();
      final opened = <Acc03Destination>[];
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        _app(
          key: const ValueKey('home'),
          client: client,
          repository: repository,
          onOpen: opened.add,
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('ai01-embedded-content')),
        findsOneWidget,
      );
      final draftFinder = find.byKey(const ValueKey('ai01-task-input'));
      expect(draftFinder, findsOneWidget);
      await tester.enterText(draftFinder, 'Review global market signals');
      expect(
        tester.widget<TextField>(draftFinder).controller!.text,
        'Review global market signals',
      );
      expect(client.requestedScreens, ['AI-01']);
      expect(repository.calls, 0);
      expect(find.text('从一处，看见全局。'), findsNothing);
      expect(find.text('从一处，看见全局'), findsNothing);
      expect(find.text('工作入口'), findsNothing);
      expect(find.text('入口检查'), findsNothing);
      expect(find.text('查看入口状态'), findsNothing);

      final submit = find.widgetWithText(FilledButton, '开始分析');
      expect(submit, findsOneWidget);
      expect(tester.widget<FilledButton>(submit).onPressed, isNull);
      final submitTooltip = find.ancestor(
        of: submit,
        matching: find.byType(Tooltip),
      );
      expect(
        tester.widget<Tooltip>(submitTooltip.first).message,
        contains('AI 任务提交能力尚未接入'),
      );

      const destinations = <(String, Acc03Destination)>[
        ('CTH-01', Acc03Destination.commerce),
        ('BMP-01', Acc03Destination.brand),
        ('SH-02', Acc03Destination.research),
        ('SH-01', Acc03Destination.creation),
      ];
      for (final (screenId, _) in destinations) {
        final button = find.byKey(ValueKey('acc03-destination-$screenId'));
        expect(button, findsOneWidget);
        final rect = tester.getRect(button);
        expect(rect.height, greaterThanOrEqualTo(48));
        expect(rect.top, greaterThanOrEqualTo(0));
        expect(rect.bottom, lessThanOrEqualTo(844));
      }
      for (final (screenId, _) in destinations) {
        await tester.tap(find.byKey(ValueKey('acc03-destination-$screenId')));
        await tester.pump();
      }

      expect(
        opened,
        destinations.map((entry) => entry.$2).toList(growable: false),
      );
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'default global focus copy stays accurate in three locales at large text',
    (tester) async {
      final clients = <_Client>[];
      final repository = _UnusedRepository();
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      const locales = <Locale>[Locale('zh', 'CN'), Locale('en'), Locale('ko')];
      const oldSubjectBlockers = <String>[
        '尚未确认可用的经营对象',
        'No usable business subject or brand is confirmed',
        '사용할 사업 주체 또는 브랜드가 확인되지 않았습니다',
      ];
      const oldSubmitBlockers = <String>[
        '当前尚未确认可处理的经营主体或品牌，暂不能开始分析。',
        'A usable business subject or brand is not confirmed, so analysis cannot start.',
        '사용할 사업 주체 또는 브랜드가 확인되지 않아 분석을 시작할 수 없습니다.',
      ];
      const globalFocusCopy = <String>['范围可选', 'Optional focus', '범위 선택 가능'];
      const expectedFirstDestination = <String>['商业运营', 'Commerce', '커머스 운영'];
      const marketingTitles = <String>[
        '今天，想完成什么？',
        'What would you like to work on?',
        '오늘 어떤 일을 해볼까요?',
      ];

      for (var index = 0; index < locales.length; index++) {
        final client = _Client();
        clients.add(client);
        await tester.pumpWidget(
          _app(
            key: ValueKey('locale-$index'),
            client: client,
            repository: repository,
            locale: locales[index],
            textScaler: TextScaler.linear(2),
          ),
        );
        await tester.pumpAndSettle();

        expect(find.byKey(const ValueKey('ai01-task-input')), findsOneWidget);
        expect(find.text(globalFocusCopy[index]), findsOneWidget);
        expect(find.text(oldSubjectBlockers[index]), findsNothing);
        expect(find.text(oldSubmitBlockers[index]), findsNothing);
        expect(find.text(marketingTitles[index]), findsNothing);
        expect(find.text(expectedFirstDestination[index]), findsOneWidget);
        for (final screenId in const ['CTH-01', 'BMP-01', 'SH-02', 'SH-01']) {
          final button = find.byKey(ValueKey('acc03-destination-$screenId'));
          expect(button, findsOneWidget);
          expect(tester.getSize(button).height, greaterThanOrEqualTo(48));
        }
        expect(tester.takeException(), isNull);
      }
      for (final client in clients) {
        expect(client.requestedScreens, ['AI-01']);
      }
      expect(repository.calls, 0);
    },
  );

  testWidgets('desktop keeps the task editor within the approved width', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        key: const ValueKey('desktop'),
        client: _Client(),
        repository: _UnusedRepository(),
      ),
    );
    await tester.pumpAndSettle();

    final editor = tester.getRect(
      find.byKey(const ValueKey('ai01-composer-surface')),
    );
    expect(editor.width, lessThanOrEqualTo(820));
    expect((editor.center.dx - 640).abs(), lessThanOrEqualTo(1));
    expect(tester.takeException(), isNull);
  });

  testWidgets('continue last page appears only for a safe ID and callback', (
    tester,
  ) async {
    final client = _Client();
    final resumed = <String>[];
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        key: const ValueKey('valid-last-page'),
        client: client,
        repository: _UnusedRepository(),
        lastOpenedScreenId: 'CTH-03',
        onOpenScreenId: resumed.add,
      ),
    );
    await tester.pumpAndSettle();
    final lastPage = find.byKey(const ValueKey('acc03-last-opened'));
    expect(lastPage, findsOneWidget);
    await tester.ensureVisible(lastPage);
    await tester.tap(lastPage);
    await tester.pump();
    expect(resumed, ['CTH-03']);

    for (final screenId in const ['ACC-03', 'SYS-06', 'not-a-screen']) {
      await tester.pumpWidget(
        _app(
          key: ValueKey('invalid-$screenId'),
          client: _Client(),
          repository: _UnusedRepository(),
          lastOpenedScreenId: screenId,
          onOpenScreenId: resumed.add,
        ),
      );
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('acc03-last-opened')), findsNothing);
    }

    await tester.pumpWidget(
      _app(
        key: const ValueKey('no-callback'),
        client: _Client(),
        repository: _UnusedRepository(),
        lastOpenedScreenId: 'CTH-03',
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('acc03-last-opened')), findsNothing);
    expect(client.requestedScreens, ['AI-01']);
    expect(tester.takeException(), isNull);
  });
}

Widget _app({
  Key? key,
  required _Client client,
  required _UnusedRepository repository,
  Locale locale = const Locale('zh', 'CN'),
  ValueChanged<Acc03Destination>? onOpen,
  String? lastOpenedScreenId,
  ValueChanged<String>? onOpenScreenId,
  TextScaler? textScaler,
}) => MaterialApp(
  key: key,
  locale: locale,
  theme: LumenisTheme.dark,
  builder: textScaler == null
      ? null
      : (context, child) => MediaQuery(
          data: MediaQuery.of(context).copyWith(textScaler: textScaler),
          child: child!,
        ),
  supportedLocales: LumenisLocalizations.supportedLocales,
  localizationsDelegates: const [
    LumenisLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  home: Scaffold(
    body: Acc03Screen(
      client: client,
      repository: repository,
      onOpen: onOpen,
      lastOpenedScreenId: lastOpenedScreenId,
      onOpenScreenId: onOpenScreenId,
    ),
  ),
);

class _Client extends LumenisCoreClient {
  final requestedScreens = <String>[];

  @override
  Future<Map<String, dynamic>> screen(String screenId) async {
    requestedScreens.add(screenId);
    throw const LumenisCoreException('Core unavailable', statusCode: 503);
  }
}

class _UnusedRepository implements Acc03Repository {
  int calls = 0;

  @override
  Future<Acc03Snapshot> load() async {
    calls += 1;
    throw StateError('Home must not load ACC-03 runtime status.');
  }
}
