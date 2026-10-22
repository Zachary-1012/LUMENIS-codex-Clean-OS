import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh01/media_project_snapshot.dart';
import 'package:lumenis_app/features/shared/sh01/media_source_waveform.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

final asset = MediaProjectAsset(
  assetId: 'MEDIA-aaaaaaaaaaaaaaaa',
  filename: 'long.wav',
  sha256: 'a' * 64,
  durationSec: 140,
  mediaKind: 'audio',
  hasVideo: false,
  audioStreamCount: 2,
);

class Client extends LumenisCoreClient {
  final requests = <(double, double, int)>[];
  String? badField;
  Completer<void>? pending;
  Map<String, dynamic>? scope;
  @override
  Map<String, dynamic>? get currentContextEnvelope => scope;
  @override
  Future<Map<String, dynamic>> inspectContentWaveform({
    required String? domainId,
    required String assetRef,
    required double startSec,
    required double endSec,
    required int audioStreamIndex,
  }) async {
    requests.add((startSec, endSec, audioStreamIndex));
    await pending?.future;
    return {
      'ok': true,
      'assets': [asset.toJson()],
      'source_artifact_refs': [assetRef],
      'waveforms': [
        {
          'state': 'measured',
          'stage': 'source_pre_mix',
          'source_sha256': asset.sha256,
          'audio_stream_index': audioStreamIndex,
          'start_sec': startSec,
          'end_sec': endSec,
          'sample_rate': 8000,
          'decoded_samples': ((endSec - startSec) * 8000).round(),
          'bins': [
            {'min': -.1, 'max': .3, 'rms': .2},
          ],
          ?badField: 'wrong',
        },
      ],
    };
  }
}

Widget app(Client client) => MaterialApp(
  locale: const Locale('en'),
  supportedLocales: LumenisLocalizations.supportedLocales,
  localizationsDelegates: const [
    LumenisLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  home: Scaffold(
    body: SizedBox(
      width: 500,
      height: 320,
      child: MediaSourceWaveform(
        client: client,
        domain: null,
        asset: asset,
        assetRef: 'ART-source',
        sourceIn: 10,
        sourceOut: 140,
        streamIndex: 1,
      ),
    ),
  ),
);

void main() {
  testWidgets(
    'large text and a narrow waveform keep range controls reachable',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(320, 480));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final client = Client();
      await tester.pumpWidget(
        MediaQuery(
          data: const MediaQueryData(textScaler: TextScaler.linear(2)),
          child: app(client),
        ),
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      expect(
        find.byKey(const Key('media-waveform-next')).hitTestable(),
        findsOneWidget,
      );
    },
  );
  testWidgets(
    'measured source windows are bounded and preserve selected stream',
    (tester) async {
      final client = Client();
      await tester.pumpWidget(app(client));
      await tester.pumpAndSettle();
      expect(client.requests, [(10.0, 70.0, 1)]);
      expect(find.byKey(const Key('media-source-waveform')), findsOneWidget);
      await tester.tap(find.byKey(const Key('media-waveform-next')));
      await tester.pumpAndSettle();
      expect(client.requests.last, (70.0, 130.0, 1));
      await tester.tap(find.byKey(const Key('media-waveform-next')));
      await tester.pumpAndSettle();
      expect(client.requests.last, (130.0, 140.0, 1));
      expect(
        tester
            .widget<IconButton>(find.byKey(const Key('media-waveform-next')))
            .onPressed,
        isNull,
      );
    },
  );
  for (final field in [
    'source_sha256',
    'stage',
    'audio_stream_index',
    'start_sec',
    'bins',
  ]) {
    testWidgets('invalid $field never becomes a waveform and can retry', (
      tester,
    ) async {
      final client = Client()..badField = field;
      await tester.pumpWidget(app(client));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('media-source-waveform')), findsNothing);
      client.badField = null;
      await tester.tap(find.byKey(const Key('media-waveform-retry')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('media-source-waveform')), findsOneWidget);
    });
  }
  testWidgets('scope changes discard an outstanding read', (tester) async {
    final client = Client()..pending = Completer<void>();
    await tester.pumpWidget(app(client));
    await tester.pump();
    client.scope = {'context': 'another workspace'};
    client.pending!.complete();
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('media-source-waveform')), findsNothing);
    expect(find.byKey(const Key('media-waveform-retry')), findsOneWidget);
  });
}
