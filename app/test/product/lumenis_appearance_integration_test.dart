import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/ai01/ai01_screen.dart';
import 'package:lumenis_app/features/system/sys05/sys05_appearance_controller.dart';
import 'package:lumenis_app/navigation/lumenis_workspace_routes.dart';
import 'package:lumenis_app/product/lumenis_app.dart';
import 'package:shared_preferences_platform_interface/in_memory_shared_preferences_async.dart';
import 'package:shared_preferences_platform_interface/shared_preferences_async_platform_interface.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferencesAsyncPlatform.instance =
        InMemorySharedPreferencesAsync.empty();
  });

  testWidgets('AI-01 draft survives opening and dismissing appearance', (
    tester,
  ) async {
    await _openAi01(tester);
    const draft = 'Compare the latest campaign results against the brief.';
    final draftField = _draftField();
    await tester.tap(draftField);
    await tester.enterText(draftField, draft);
    await tester.pump();

    final client = _lastClient!;
    final ai01State = tester.state(find.byType(Ai01Screen));
    final controller = tester.widget<TextField>(draftField).controller!;
    expect(controller.text, draft);
    final disableAnimationsBefore = _disableAnimations(tester);

    await _openAppearance(tester);
    expect(find.byKey(const ValueKey('appearance/black')), findsOneWidget);
    expect(controller.text, draft);

    await tester.sendKeyEvent(LogicalKeyboardKey.escape);
    await tester.pumpAndSettle();

    _expectDraftAndScreenUnchanged(
      tester,
      client,
      ai01State,
      controller,
      draft,
      disableAnimationsBefore,
    );
  });

  testWidgets('AI-01 draft survives black appearance change and Escape', (
    tester,
  ) async {
    await _openAi01(tester);
    const draft = 'Review the evidence before preparing the next decision.';
    final draftField = _draftField();
    await tester.tap(draftField);
    await tester.enterText(draftField, draft);
    await tester.pump();

    final client = _lastClient!;
    final ai01State = tester.state(find.byType(Ai01Screen));
    final controller = tester.widget<TextField>(draftField).controller!;
    expect(controller.text, draft);
    final disableAnimationsBefore = _disableAnimations(tester);

    await _openAppearance(tester);
    await tester.tap(find.byKey(const ValueKey('appearance/black')));
    await tester.pumpAndSettle();

    final blackChip = tester.widget<ChoiceChip>(
      find.byKey(const ValueKey('appearance/black')),
    );
    expect(blackChip.selected, isTrue);
    final sheetContext = tester.element(find.byType(BottomSheet));
    final sheetColor = Theme.of(
      sheetContext,
    ).bottomSheetTheme.modalBackgroundColor!;
    expect(sheetColor.a, greaterThanOrEqualTo(.98));
    expect(sheetColor.computeLuminance(), lessThan(.1));
    expect(controller.text, draft);
    expect(tester.state(find.byType(Ai01Screen)), same(ai01State));
    expect(_disableAnimations(tester), disableAnimationsBefore);

    await tester.sendKeyEvent(LogicalKeyboardKey.escape);
    await tester.pumpAndSettle();

    _expectDraftAndScreenUnchanged(
      tester,
      client,
      ai01State,
      controller,
      draft,
      disableAnimationsBefore,
    );
  });

  testWidgets('large local typography fits a phone and preserves its draft', (
    tester,
  ) async {
    await _openAi01(tester);
    await tester.binding.setSurfaceSize(const Size(390, 844));
    await tester.pumpAndSettle();
    const draft = 'Keep this working draft while changing text size.';
    await tester.enterText(_draftField(), draft);
    final appearance = Sys05AppearanceScope.maybeOf(
      tester.element(find.byType(Ai01Screen)),
    )!;
    await appearance.update(uiFontSize: 18, reducedMotion: true);
    await tester.pumpAndSettle();
    expect(tester.widget<TextField>(_draftField()).controller!.text, draft);
    expect(
      MediaQuery.textScalerOf(
        tester.element(find.byType(Ai01Screen)),
      ).scale(14),
      18,
    );
    await _openAppearance(tester);
    expect(tester.takeException(), isNull);
    await tester.tap(find.byKey(const ValueKey('appearance/close')));
    await tester.pumpAndSettle();
    expect(tester.widget<TextField>(_draftField()).controller!.text, draft);
    expect(tester.takeException(), isNull);
  });
}

_AppearanceClient? _lastClient;

Future<void> _openAi01(WidgetTester tester) async {
  await tester.binding.setSurfaceSize(const Size(1440, 1000));
  addTearDown(() => tester.binding.setSurfaceSize(null));
  final client = _AppearanceClient();
  _lastClient = client;
  await tester.pumpWidget(
    LumenisApp(client: client, initialLocation: LumenisWorkspaceRoutes.ai01),
  );
  await tester.pumpAndSettle();

  expect(find.byType(Ai01Screen), findsOneWidget);
  expect(client.screenReads, ['AI-01']);
}

Future<void> _openAppearance(WidgetTester tester) async {
  await tester.tap(find.byKey(const ValueKey('appearance/open')));
  await tester.pumpAndSettle();
}

Finder _draftField() => find.byWidgetPredicate(
  (widget) => widget is TextField && widget.maxLength == 4000,
  description: 'AI-01 4000-character task draft field',
);

bool _disableAnimations(WidgetTester tester) =>
    MediaQuery.of(tester.element(find.byType(Ai01Screen))).disableAnimations;

void _expectDraftAndScreenUnchanged(
  WidgetTester tester,
  _AppearanceClient client,
  Object ai01State,
  TextEditingController controller,
  String draft,
  bool disableAnimationsBefore,
) {
  expect(find.byType(Ai01Screen), findsOneWidget);
  expect(tester.state(find.byType(Ai01Screen)), same(ai01State));
  expect(tester.widget<TextField>(_draftField()).controller, same(controller));
  expect(controller.text, draft);
  expect(_disableAnimations(tester), disableAnimationsBefore);
  expect(client.screenReads, [
    'AI-01',
  ], reason: 'Closing appearance must not refetch AI-01.');
  expect(tester.takeException(), isNull);
}

class _AppearanceClient extends LumenisCoreClient {
  final screenReads = <String>[];

  @override
  Future<Map<String, dynamic>> runtimeIdentity() async => {
    'ok': true,
    'domain': 'workspace',
  };

  @override
  Future<Map<String, dynamic>> settingsContext() async => _globalContext;

  @override
  Future<Map<String, dynamic>> screen(String screenId) async {
    screenReads.add(screenId);
    return {
      'ok': true,
      'screen': screenId,
      'source': 'runtime',
      'bound': false,
      'generated_at': '2026-09-24T00:00:00',
      'binding': {'unavailable': []},
      'sections': [
        {'type': 'cards', 'items': const []},
        {
          'type': 'split',
          'main': const [],
          'side': [
            {'type': 'runtime', 'items': const []},
          ],
        },
      ],
      'truth': const {},
    };
  }
}

const _globalContext = {
  'ok': true,
  'contract': 'lumenis.context.v1',
  'context': {
    'mode': 'GLOBAL_ALL',
    'mode_label_key': 'context.mode.global_all',
    'domain_id': null,
    'product_id': null,
    'subject_id': null,
    'subject_type': null,
    'display_name': null,
    'display_state': 'not_applicable',
  },
  'authorized_domains': [
    {'id': 'CTH', 'name': 'Business', 'product': 'CTH'},
    {'id': 'BMP', 'name': 'Brand', 'product': 'ZBMP'},
  ],
  'selection_only': true,
};
