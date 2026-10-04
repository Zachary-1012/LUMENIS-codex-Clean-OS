import 'dart:async';
import 'dart:ui' show SemanticsAction;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/shared/sh01/media_preview.dart';
import 'package:lumenis_app/features/shared/sh01/media_preview_native.dart'
    show WindowsMediaPreview;
import 'package:lumenis_app/features/shared/sh01/native_media_cache.dart';
import 'package:lumenis_app/features/shared/sh01/native_media_player.dart';
import 'package:lumenis_app/features/shared/sh01/native_media_preview_controller.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';
import 'package:video_player/video_player.dart';

const _previewKey = ValueKey<String>('sh01-native-preview');
const _duration = Duration(seconds: 20);
const _position = Duration(seconds: 6);

ContentProjectFile _file(String name) => ContentProjectFile(
  bytes: Uint8List.fromList(const [0x00, 0x01, 0x02]),
  filename: name,
  mediaType: 'video/mp4',
);

class _FakeLease implements NativeMediaFileLease {
  _FakeLease({required this.path, required this.events, this.releaseGate});

  @override
  final String path;
  final List<String> events;
  Completer<void>? releaseGate;
  final Completer<void> releaseStarted = Completer<void>();
  int releaseCalls = 0;
  bool released = false;

  @override
  Future<void> release() async {
    releaseCalls++;
    events.add('lease:release-start:$path');
    if (!releaseStarted.isCompleted) releaseStarted.complete();
    await releaseGate?.future;
    released = true;
    events.add('lease:release-done:$path');
  }
}

/// Deterministic presentation fake. It owns no plugin, channel, or real media.
class _FakeNativeMediaPlayer extends NativeMediaPlayer {
  _FakeNativeMediaPlayer({required this.path, required this.events});

  final String path;
  final List<String> events;
  int initializeCalls = 0;
  int playCalls = 0;
  int pauseCalls = 0;
  int seekCalls = 0;
  int releaseCalls = 0;
  bool released = false;

  @override
  Future<void> initialize() async {
    initializeCalls++;
    value = const VideoPlayerValue(
      duration: _duration,
      position: Duration.zero,
      size: Size(160, 90),
      isInitialized: true,
      isPlaying: false,
      volume: 1,
      errorDescription: null,
    );
    events.add('player:initialized:$path');
  }

  @override
  Future<void> play() async {
    playCalls++;
    value = value.copyWith(isPlaying: true, isCompleted: false);
    events.add('player:play:$path');
  }

  @override
  Future<void> pause() async {
    pauseCalls++;
    value = value.copyWith(isPlaying: false);
    events.add('player:pause:$path');
  }

  @override
  Future<void> seekTo(Duration position) async {
    seekCalls++;
    value = value.copyWith(position: position, isCompleted: false);
    events.add('player:seek:$path:${position.inMilliseconds}');
  }

  @override
  Future<void> setVolume(double volume) async {
    value = value.copyWith(volume: volume);
    events.add('player:volume:$path:$volume');
  }

  void emitDecodeError() {
    value = value.copyWith(errorDescription: 'decoder failed');
    events.add('player:decode-error:$path');
  }

  @override
  Future<void> release() async {
    releaseCalls++;
    released = true;
    events.add('player:release:$path');
  }

  @override
  Widget buildView() =>
      const SizedBox.expand(child: ColoredBox(color: Color(0xff315a82)));
}

class _PreviewHarness {
  final NativePlaybackSlot slot = NativePlaybackSlot();
  final List<NativeMediaPreviewController> controllers = [];
  final List<ContentProjectFile> requestedFiles = [];
  final List<_FakeLease> leases = [];
  final List<_FakeNativeMediaPlayer> players = [];
  final List<String> playerPaths = [];
  final List<String> events = [];
  final Map<int, Completer<void>> leaseReleaseGates = {};

  NativeMediaPreviewController createController(ContentProjectFile file) {
    final controller = NativeMediaPreviewController(
      file: file,
      slot: slot,
      createFile: (source) async {
        requestedFiles.add(source);
        final index = leases.length;
        final path = 'test-cache/$index/${source.filename}';
        events.add('lease:create:${source.filename}:$path');
        final lease = _FakeLease(
          path: path,
          events: events,
          releaseGate: leaseReleaseGates[index],
        );
        leases.add(lease);
        return lease;
      },
      createPlayer: (path) {
        playerPaths.add(path);
        events.add('player:create:$path');
        final player = _FakeNativeMediaPlayer(path: path, events: events);
        players.add(player);
        return player;
      },
    );
    controllers.add(controller);
    return controller;
  }
}

Widget _app({
  required Widget home,
  Locale locale = const Locale('zh', 'CN'),
  double textScale = 1,
}) => MaterialApp(
  theme: LumenisTheme.dark,
  locale: locale,
  supportedLocales: LumenisLocalizations.supportedLocales,
  localizationsDelegates: const [
    LumenisLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  builder: (context, child) => MediaQuery(
    data: MediaQuery.of(
      context,
    ).copyWith(textScaler: TextScaler.linear(textScale)),
    child: child!,
  ),
  home: home,
);

Widget _nativePreviewApp(
  ContentProjectFile file,
  _PreviewHarness harness, {
  Locale locale = const Locale('zh', 'CN'),
  double textScale = 1,
}) => _app(
  locale: locale,
  textScale: textScale,
  home: Scaffold(
    body: WindowsMediaPreview(
      key: _previewKey,
      file: file,
      controllerFactory: harness.createController,
    ),
  ),
);

String _copy(WidgetTester tester, String key) => LumenisLocalizations.of(
  tester.element(find.byKey(_previewKey)),
).text('sh01.media.player.$key');

Future<NativeMediaPreviewController> _startPreview(
  WidgetTester tester,
  ContentProjectFile file,
  _PreviewHarness harness,
) async {
  await tester.pumpWidget(_nativePreviewApp(file, harness));
  final controller = harness.controllers.single;
  await controller.start();
  await tester.pump();
  return controller;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets(
    'native preview is paused, accessible by keyboard, and fits narrow 200% text',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(280, 230));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final semantics = tester.ensureSemantics();
      try {
        final harness = _PreviewHarness();
        await _startPreview(tester, _file('keyboard.mp4'), harness);
        final player = harness.players.single;

        expect(player.initializeCalls, 1);
        expect(player.value.duration, _duration);
        expect(player.value.size, const Size(160, 90));
        expect(player.value.isPlaying, isFalse);
        expect(harness.controllers.single.playing, isFalse);
        expect(tester.getSize(find.byKey(_previewKey)), const Size(280, 230));

        final playLabel = _copy(tester, 'play');
        final playButton = find.byTooltip(playLabel);
        expect(playButton, findsOneWidget);
        final playSemantics = tester
            .getSemantics(playButton)
            .getSemanticsData();
        expect(playSemantics.label, playLabel);
        expect(playSemantics.hasAction(SemanticsAction.tap), isTrue);

        await tester.sendKeyEvent(LogicalKeyboardKey.tab);
        await tester.pump();
        await tester.sendKeyEvent(LogicalKeyboardKey.space);
        await tester.pump();

        expect(player.playCalls, 1);
        expect(player.value.isPlaying, isTrue);
        expect(find.byTooltip(_copy(tester, 'pause')), findsOneWidget);
        expect(tester.takeException(), isNull);
      } finally {
        semantics.dispose();
      }
    },
  );

  testWidgets('zh to ko to en keeps the same paused driver and position', (
    tester,
  ) async {
    final locale = ValueNotifier(const Locale('zh', 'CN'));
    addTearDown(locale.dispose);
    final harness = _PreviewHarness();
    final file = _file('localized.mp4');

    await tester.pumpWidget(
      ValueListenableBuilder<Locale>(
        valueListenable: locale,
        builder: (context, current, _) =>
            _nativePreviewApp(file, harness, locale: current),
      ),
    );
    final controller = harness.controllers.single;
    await controller.start();
    await controller.seek(_position);
    await tester.pump();
    final player = harness.players.single;
    final zhPlay = _copy(tester, 'play');
    expect(player.value.position, _position);
    expect(player.value.isPlaying, isFalse);

    locale.value = const Locale('ko');
    await tester.pump();
    final koPlay = _copy(tester, 'play');
    expect(koPlay, isNot(zhPlay));
    expect(find.byTooltip(koPlay), findsOneWidget);
    expect(harness.controllers, hasLength(1));
    expect(harness.players, hasLength(1));
    expect(identical(harness.controllers.single, controller), isTrue);
    expect(identical(controller.player, player), isTrue);
    expect(player.value.position, _position);
    expect(player.value.isPlaying, isFalse);

    locale.value = const Locale('en');
    await tester.pump();
    final enPlay = _copy(tester, 'play');
    expect(enPlay, isNot(koPlay));
    expect(find.byTooltip(enPlay), findsOneWidget);
    expect(harness.requestedFiles, hasLength(1));
    expect(identical(harness.requestedFiles.single, file), isTrue);
    expect(identical(controller.player, player), isTrue);
    expect(player.value.position, _position);
    expect(player.value.isPlaying, isFalse);
    expect(player.playCalls, 0);
    expect(tester.takeException(), isNull);
  });

  testWidgets('dialog cover pauses and hides preview input and semantics', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    try {
      final harness = _PreviewHarness();
      final file = _file('covered.mp4');
      await tester.pumpWidget(
        _app(
          home: Scaffold(
            body: Column(
              children: [
                Expanded(
                  child: WindowsMediaPreview(
                    key: _previewKey,
                    file: file,
                    controllerFactory: harness.createController,
                  ),
                ),
                Builder(
                  builder: (context) => TextButton(
                    key: const Key('cover-preview'),
                    onPressed: () => showDialog<void>(
                      context: context,
                      builder: (dialogContext) => AlertDialog(
                        content: const Text('Dialog covers preview'),
                        actions: [
                          TextButton(
                            key: const Key('return-to-preview'),
                            onPressed: () => Navigator.of(dialogContext).pop(),
                            child: const Text('Return'),
                          ),
                        ],
                      ),
                    ),
                    child: const Text('Cover preview'),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
      final controller = harness.controllers.single;
      await controller.start();
      final player = harness.players.single;
      await controller.seek(_position);
      await controller.togglePlayback();
      await tester.pump();
      expect(player.value.isPlaying, isTrue);

      final playCountBeforeCover = player.playCalls;
      await tester.tap(find.byKey(const Key('cover-preview')));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 350));
      await tester.pump();

      expect(player.value.isPlaying, isFalse);
      expect(controller.playing, isFalse);
      expect(player.value.position, _position);
      expect(
        tester
            .widget<IgnorePointer>(
              find
                  .descendant(
                    of: find.byKey(_previewKey),
                    matching: find.byType(IgnorePointer),
                  )
                  .first,
            )
            .ignoring,
        isTrue,
      );
      expect(
        tester
            .widget<ExcludeSemantics>(
              find
                  .descendant(
                    of: find.byKey(_previewKey),
                    matching: find.byType(ExcludeSemantics),
                  )
                  .first,
            )
            .excluding,
        isTrue,
      );
      expect(find.bySemanticsLabel(_copy(tester, 'pause')), findsNothing);
      expect(player.playCalls, playCountBeforeCover);

      await tester.tap(find.byKey(const Key('return-to-preview')));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 350));
      await tester.pump();

      expect(identical(controller.player, player), isTrue);
      expect(player.value.position, _position);
      expect(player.value.isPlaying, isFalse);
      expect(controller.playing, isFalse);
      expect(player.playCalls, playCountBeforeCover);
      expect(
        tester
            .widget<IgnorePointer>(
              find
                  .descendant(
                    of: find.byKey(_previewKey),
                    matching: find.byType(IgnorePointer),
                  )
                  .first,
            )
            .ignoring,
        isFalse,
      );
      expect(find.bySemanticsLabel(_copy(tester, 'play')), findsOneWidget);
      expect(tester.takeException(), isNull);
    } finally {
      semantics.dispose();
    }
  });

  testWidgets('inactive then resumed remains paused on the same driver', (
    tester,
  ) async {
    final harness = _PreviewHarness();
    final controller = await _startPreview(
      tester,
      _file('lifecycle.mp4'),
      harness,
    );
    final player = harness.players.single;
    await controller.seek(_position);
    await controller.togglePlayback();
    await tester.pump();
    expect(player.value.isPlaying, isTrue);

    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
    await tester.pump();
    expect(player.value.isPlaying, isFalse);
    expect(player.value.position, _position);

    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump();
    expect(identical(controller.player, player), isTrue);
    expect(player.value.position, _position);
    expect(player.value.isPlaying, isFalse);
    expect(controller.playing, isFalse);
    expect(player.playCalls, 1);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'source replacement waits for old player and file lease release',
    (tester) async {
      final harness = _PreviewHarness();
      final oldFile = _file('old.mp4');
      final newFile = _file('new.mp4');
      final releaseGate = Completer<void>();
      harness.leaseReleaseGates[0] = releaseGate;
      final oldController = await _startPreview(tester, oldFile, harness);
      final oldPlayer = harness.players.single;
      final oldLease = harness.leases.single;

      await tester.pumpWidget(_nativePreviewApp(newFile, harness));
      await oldLease.releaseStarted.future;
      await tester.pump();

      expect(oldPlayer.released, isTrue);
      expect(oldLease.released, isFalse);
      expect(harness.controllers, hasLength(2));
      expect(harness.requestedFiles, hasLength(1));
      expect(harness.players, hasLength(1));
      expect(
        harness.events.any(
          (event) => event.startsWith('lease:create:new.mp4:'),
        ),
        isFalse,
      );

      releaseGate.complete();
      await oldController.close();
      final newController = harness.controllers.last;
      await newController.start();
      await tester.pump();

      expect(oldLease.released, isTrue);
      expect(harness.requestedFiles, hasLength(2));
      expect(identical(harness.requestedFiles[0], oldFile), isTrue);
      expect(identical(harness.requestedFiles[1], newFile), isTrue);
      expect(harness.players, hasLength(2));
      expect(
        harness.events.indexOf('lease:release-done:${oldLease.path}'),
        lessThan(
          harness.events.indexWhere(
            (event) => event.startsWith('lease:create:new.mp4:'),
          ),
        ),
      );
      expect(newController.phase, NativePreviewPhase.ready);
      expect(harness.players.last.value.isPlaying, isFalse);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('decoder failure retry reuses the original source bytes', (
    tester,
  ) async {
    final harness = _PreviewHarness();
    final file = _file('retry-source.mp4');
    final controller = await _startPreview(tester, file, harness);
    final failedPlayer = harness.players.single;
    failedPlayer.emitDecodeError();
    await tester.pump();
    await tester.pump();

    expect(controller.phase, NativePreviewPhase.failed);
    expect(controller.canRetry, isTrue);
    expect(failedPlayer.released, isTrue);
    expect(harness.leases.single.released, isTrue);
    final failureLabel = _copy(tester, 'failure');
    final retryLabel = _copy(tester, 'retry');
    expect(find.text(failureLabel), findsOneWidget);
    expect(find.text(retryLabel), findsOneWidget);

    await tester.tap(find.text(retryLabel));
    await controller.start();
    await tester.pump();

    expect(harness.requestedFiles, hasLength(2));
    expect(
      harness.requestedFiles.every((source) => identical(source, file)),
      isTrue,
    );
    expect(harness.playerPaths, hasLength(2));
    expect(harness.playerPaths[0], 'test-cache/0/retry-source.mp4');
    expect(harness.playerPaths[1], 'test-cache/1/retry-source.mp4');
    expect(harness.players, hasLength(2));
    expect(controller.file, same(file));
    expect(controller.phase, NativePreviewPhase.ready);
    expect(harness.players.last.value.isPlaying, isFalse);
    expect(tester.takeException(), isNull);
  });

  testWidgets('non Windows default preview uses the localized stub only', (
    tester,
  ) async {
    final priorPlatform = debugDefaultTargetPlatformOverride;
    debugDefaultTargetPlatformOverride = TargetPlatform.android;
    try {
      final harness = _PreviewHarness();

      await tester.pumpWidget(
        _app(
          home: Scaffold(body: MediaPreview(file: _file('stub.mp4'))),
        ),
      );

      final expected = LumenisLocalizations.of(
        tester.element(find.byType(Scaffold)),
      ).text('sh01.media.native_preview');
      expect(find.text(expected), findsOneWidget);
      expect(harness.controllers, isEmpty);
      expect(harness.requestedFiles, isEmpty);
      expect(harness.players, isEmpty);
      expect(tester.takeException(), isNull);
    } finally {
      debugDefaultTargetPlatformOverride = priorPlatform;
    }
  });
}
