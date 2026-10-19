import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:lumenis_app/features/system/sys02/sys_system_foundation.dart';
import 'package:lumenis_app/features/system/sys05/sys05_appearance_controller.dart';

class _Store extends Fake implements SharedPreferencesAsync {
  final data = <String, String>{};
  bool fail = false;
  @override
  Future<String?> getString(String key) async => data[key];
  @override
  Future<void> setString(String key, String value) async {
    if (fail) throw StateError('test failure');
    data[key] = value;
  }
  @override
  Future<void> remove(String key) async { data.remove(key); }
}
Widget host(Sys05AppearanceController c, {bool reduced = false, bool loading = true}) =>
  MaterialApp(home: Sys05AppearanceScope(controller: c,
    child: MediaQuery(data: MediaQueryData(disableAnimations: reduced),
      child: Scaffold(body: loading
        ? const SysLoadingView(titleKey: 'sys.common.loading')
        : const Text('actual ready')))));
void main() {
  test('old preferences default simple; tone round trips and reset restores default', () async {
    final store = _Store();
    store.data[Sys05AppearanceController.preferenceKey] = jsonEncode({'version': 1});
    final c = Sys05AppearanceController(storage: store);
    await c.restore(); expect(c.waitingTone, WaitingTone.simple);
    await c.update(waitingTone: WaitingTone.playful);
    final restored = Sys05AppearanceController(storage: store);
    await restored.restore(); expect(restored.waitingTone, WaitingTone.playful);
    await restored.resetLocalAppearance(); expect(restored.waitingTone, WaitingTone.simple);
    c.dispose(); restored.dispose();
  });
  test('save failure is reported and does not forge persistent success', () async {
    final store = _Store()..fail = true;
    final c = Sys05AppearanceController(storage: store);
    await c.update(waitingTone: WaitingTone.off);
    expect(c.errorKey, 'appearance.saveFailed'); expect(store.data, isEmpty);
    c.dispose();
  });
  testWidgets('off hides extra copy, keeps real status; ready removes waiting immediately', (tester) async {
    final c = Sys05AppearanceController(storage: _Store());
    await c.update(waitingTone: WaitingTone.off);
    await tester.pumpWidget(host(c));
    expect(find.byKey(const ValueKey('sys/waiting-extra-text')), findsNothing);
    expect(find.byType(SysLoadingView), findsOneWidget);
    await tester.pumpWidget(host(c, loading: false));
    expect(find.byKey(const ValueKey('sys/waiting-paper')), findsNothing);
    expect(find.text('actual ready'), findsOneWidget);
    await tester.pumpWidget(const SizedBox()); c.dispose();
  });
  testWidgets('system reduction keeps feedback static and leaves no ticking frame', (tester) async {
    final c = Sys05AppearanceController(storage: _Store());
    await tester.pumpWidget(host(c, reduced: true));
    await tester.pump(); expect(tester.binding.hasScheduledFrame, isFalse);
    expect(find.byKey(const ValueKey('sys/waiting-paper')), findsOneWidget);
    await tester.pumpWidget(const SizedBox()); c.dispose();
  });
  testWidgets('user reduction takes effect while waiting; unmount disposes motion', (tester) async {
    final c = Sys05AppearanceController(storage: _Store());
    await tester.pumpWidget(host(c));
    await c.update(reducedMotion: true); await tester.pump(); await tester.pump();
    expect(tester.binding.hasScheduledFrame, isFalse);
    await tester.pumpWidget(const SizedBox());
    expect(tester.takeException(), isNull); c.dispose();
  });
  testWidgets('background pauses and foreground resumes existing waiting animation', (tester) async {
    final c = Sys05AppearanceController(storage: _Store());
    await tester.pumpWidget(host(c));
    await tester.pump(const Duration(milliseconds: 100));
    expect(tester.binding.hasScheduledFrame, isTrue);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    await tester.pump();
    expect(tester.binding.hasScheduledFrame, isFalse);
    expect(find.byType(SysLoadingView), findsOneWidget);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump(const Duration(milliseconds: 100));
    expect(tester.binding.hasScheduledFrame, isTrue);
    await tester.pumpWidget(const SizedBox());
    await tester.pump();
    expect(tester.binding.hasScheduledFrame, isFalse);
    expect(tester.takeException(), isNull);
    c.dispose();
  });
  testWidgets('hidden TickerMode pauses and visible mode resumes without changing state', (tester) async {
    final c = Sys05AppearanceController(storage: _Store());
    Widget scene(bool enabled) => MaterialApp(home: Sys05AppearanceScope(
      controller: c, child: Scaffold(body: TickerMode(enabled: enabled,
        child: const SysLoadingView(titleKey: 'sys.common.loading')))));
    await tester.pumpWidget(scene(true));
    await tester.pump(const Duration(milliseconds: 100));
    expect(tester.binding.hasScheduledFrame, isTrue);
    await tester.pumpWidget(scene(false));
    await tester.pump();
    expect(tester.binding.hasScheduledFrame, isFalse);
    expect(find.byType(SysLoadingView), findsOneWidget);
    await tester.pumpWidget(scene(true));
    await tester.pump(const Duration(milliseconds: 100));
    expect(tester.binding.hasScheduledFrame, isTrue);
    await tester.pumpWidget(const SizedBox());
    expect(tester.takeException(), isNull);
    c.dispose();
  });
  testWidgets('loading to actual failure branch removes decoration and extra copy', (tester) async {
    final c = Sys05AppearanceController(storage: _Store());
    await c.update(waitingTone: WaitingTone.playful);
    Widget scene(bool loading) => MaterialApp(home: Sys05AppearanceScope(
      controller: c, child: Scaffold(body: loading
        ? const SysLoadingView(titleKey: 'sys.common.loading')
        : SysFailureView(kind: SysFailureKind.offline, onRetry: () {}))));
    await tester.pumpWidget(scene(true));
    expect(find.byKey(const ValueKey('sys/waiting-extra-text')), findsOneWidget);
    await tester.pumpWidget(scene(false));
    await tester.pump();
    expect(find.byType(SysFailureView), findsOneWidget);
    expect(find.byKey(const ValueKey('sys/waiting-extra-text')), findsNothing);
    expect(find.byKey(const ValueKey('sys/waiting-paper')), findsNothing);
    expect(tester.binding.hasScheduledFrame, isFalse);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox()); c.dispose();
  });
  testWidgets('reduced motion and extra copy off preserve the actual status semantics', (tester) async {
    final c = Sys05AppearanceController(storage: _Store());
    await c.update(waitingTone: WaitingTone.off, reducedMotion: true);
    final semantics = tester.ensureSemantics();
    await tester.pumpWidget(host(c, reduced: true));
    await tester.pump();
    expect(find.byType(SysLoadingView), findsOneWidget);
    expect(find.byKey(const ValueKey('sys/waiting-extra-text')), findsNothing);
    expect(find.byKey(const ValueKey('sys/waiting-paper')), findsOneWidget);
    final context = tester.element(find.byType(SysLoadingView));
    expect(find.bySemanticsLabel(SysSystemCopy.text(context, 'sys.common.loading')),
        findsWidgets);
    expect(tester.binding.hasScheduledFrame, isFalse);
    await tester.pumpWidget(const SizedBox());
    semantics.dispose(); c.dispose();
  });

  for (final scene in WaitingScene.values) {
    testWidgets('scene ${scene.name} preserves owner status and stops on removal', (tester) async {
      final c = Sys05AppearanceController(storage: _Store());
      await c.update(waitingTone: WaitingTone.playful, reducedMotion: true);
      await tester.pumpWidget(MaterialApp(home: Sys05AppearanceScope(
        controller: c, child: Scaffold(body: Column(children: [
          const Text('owner running'), WaitingFeedback(scene: scene),
        ])))));
      await tester.pump();
      expect(find.text('owner running'), findsOneWidget);
      expect(find.byKey(const ValueKey('sys/waiting-paper')), findsOneWidget);
      expect(find.byKey(const ValueKey('sys/waiting-extra-text')), findsOneWidget);
      expect(tester.binding.hasScheduledFrame, isFalse);
      await tester.pumpWidget(const SizedBox());
      expect(tester.takeException(), isNull); c.dispose();
    });
  }
  testWidgets('scene changes repaint and off preserves owner action', (tester) async {
    final c = Sys05AppearanceController(storage: _Store());
    await c.update(reducedMotion: true);
    var cancelled = false;
    Widget scene(WaitingScene value) => MaterialApp(home: Sys05AppearanceScope(
      controller: c, child: Scaffold(body: Column(children: [
        WaitingFeedback(scene: value),
        TextButton(onPressed: () => cancelled = true, child: const Text('Cancel owner task')),
      ]))));
    await tester.pumpWidget(scene(WaitingScene.search));
    final first = tester.widget<CustomPaint>(find.byKey(const ValueKey('sys/waiting-paper'))).painter!;
    await tester.pumpWidget(scene(WaitingScene.export));
    final second = tester.widget<CustomPaint>(find.byKey(const ValueKey('sys/waiting-paper'))).painter!;
    expect(second.shouldRepaint(first), isTrue);
    await c.update(waitingTone: WaitingTone.off); await tester.pump();
    expect(find.byKey(const ValueKey('sys/waiting-extra-text')), findsNothing);
    await tester.tap(find.text('Cancel owner task')); expect(cancelled, isTrue);
    await tester.pumpWidget(const SizedBox()); c.dispose();
  });

}
