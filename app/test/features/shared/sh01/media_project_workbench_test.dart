import 'dart:async';
import 'dart:io';
import 'audio_comparison_fixture.dart';
import 'dart:ui' show Tristate, ImageByteFormat;

import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart' show RenderRepaintBoundary;
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/shared/sh01/media_project_controller.dart';
import 'package:lumenis_app/features/shared/sh01/media_project_files.dart';
import 'package:lumenis_app/features/shared/sh01/media_preview.dart';
import 'package:lumenis_app/features/shared/sh01/media_project_snapshot.dart';
import 'package:lumenis_app/features/shared/sh01/media_project_workbench.dart';
import 'package:lumenis_app/features/system/sys02/sys_system_foundation.dart'
    show WaitingFeedback;
import 'package:lumenis_app/l10n/lumenis_localizations.dart';
import 'package:lumenis_app/navigation/lumenis_leave_guard.dart';

// Contract fixture only; real backend behavior is covered by TC02 Python tests.
MediaProjectSnapshot _batchFixture(
  MediaProjectSnapshot snapshot,
  List<Map<String, dynamic>> commands,
) {
  var current = snapshot;
  for (final command in commands) {
    final id = command['clip_id'] as String;
    current = switch (command['op']) {
      'trim' => current.trimClip(
        id,
        sourceIn: (command['source_in'] as num).toDouble(),
        sourceOut: (command['source_out'] as num).toDouble(),
      ),
      'move_audio_clip' => current.moveAudioClip(
        id,
        timelineStart: (command['timeline_start'] as num).toDouble(),
      ),
      'audio_mix' => current.setAudioMix(
        id,
        MediaProjectAudioMix.fromJson(
          command['mix'],
          clipDuration: current.tracks
              .expand((t) => t.clips)
              .firstWhere((c) => c.clipId == id)
              .durationSec,
        ),
      ),
      'split' => current.splitClip(
        id,
        atSec: (command['at_sec'] as num).toDouble(),
      ),
      _ => throw const FormatException('Unsupported fixture command'),
    };
  }
  return current;
}

Map<String, dynamic> _batchResponse(
  MediaProjectSnapshot base,
  MediaProjectSnapshot candidate,
  List<String>? refs,
) => {
  'ok': true,
  'assets': base.assets.map((asset) => asset.toJson()).toList(),
  'source_artifact_refs': refs ?? <String>[],
  'rights_state': 'unknown',
  'external_fetch': false,
  'edit_batch': {
    'state': 'preview',
    'base_version': base.version,
    'base_digest': 'a' * 64,
    'timeline_digest': 'b' * 64,
    'timeline': candidate.toJson(),
    'persisted': false,
    'export_performed': false,
    'approval_required': true,
    'undo_scope': 'session_per_operation_not_persisted',
  },
};

// These are widget contract fixtures, never media/render or user E2E evidence.
class _Client extends LumenisCoreClient {
  Completer<ContentProjectFile>? sourcePreviewPending;
  int sourcePreviewCalls = 0;
  String? previewSourceRef;
  String? previewSourceSha;
  bool sourcePreviewFailure = false;

  @override
  Future<ContentProjectFile> contentSourcePreview({
    required String? domainId,
    required String artifactId,
    required String expectedSha256,
  }) async {
    sourcePreviewCalls++;
    previewSourceRef = artifactId;
    previewSourceSha = expectedSha256;
    if (sourcePreviewPending != null) return sourcePreviewPending!.future;
    if (sourcePreviewFailure) throw const FormatException();
    return ContentProjectFile(
      bytes: Uint8List.fromList([1, 2]),
      filename: 'source.mp4',
      mediaType: 'video/mp4',
    );
  }

  @override
  Future<Map<String, dynamic>> inspectAudioProcessing({
    required String? domainId,
    List<String>? assetPaths,
    List<String>? assetRefs,
    required Map<String, dynamic> timeline,
    required Map<String, double> renderOptions,
    required double startSec,
    required double endSec,
  }) async => audioComparisonFixture(
    timeline,
    assetRefs,
    renderOptions,
    startSec,
    endSec,
  );

  int imports = 0;
  int importCalls = 0;
  int inspectCalls = 0;
  int batchCalls = 0;
  List<Map<String, dynamic>>? batchCommands;
  Completer<void>? pendingBatch;
  String? batchFailureCode;

  @override
  Future<Map<String, dynamic>> inspectContentWaveform({
    required String? domainId,
    required String assetRef,
    required double startSec,
    required double endSec,
    required int audioStreamIndex,
  }) async => {
    'ok': true,
    'assets': [asset],
    'source_artifact_refs': [assetRef],
    'waveforms': [
      {
        'state': 'measured',
        'stage': 'source_pre_mix',
        'source_sha256': asset['sha256'],
        'audio_stream_index': audioStreamIndex,
        'start_sec': startSec,
        'end_sec': endSec,
        'sample_rate': 8000,
        'decoded_samples': ((endSec - startSec) * 8000).round(),
        'bins': [
          {'min': -.25, 'max': .4, 'rms': .2},
        ],
      },
    ],
  };

  @override
  Future<Map<String, dynamic>> inspectContentEditBatch({
    required String? domainId,
    List<String>? assetPaths,
    List<String>? assetRefs,
    required Map<String, dynamic> timeline,
    required List<Map<String, dynamic>> commands,
    required int expectedVersion,
  }) async {
    batchCalls++;
    batchCommands = commands;
    await pendingBatch?.future;
    if (batchFailureCode != null) {
      throw LumenisCoreException(
        'private batch diagnostic',
        statusCode: 403,
        errorCode: batchFailureCode,
      );
    }
    final base = MediaProjectSnapshot.fromJson(
      timeline,
      inspectedAssets: (timeline['assets'] as List).map(
        MediaProjectAsset.fromJson,
      ),
    );
    expect(expectedVersion, base.version);
    return _batchResponse(base, _batchFixture(base, commands), assetRefs);
  }

  int exports = 0;
  int confirmationCalls = 0;
  bool? confirmedImport;
  bool approvalRequired = false;
  bool successfulExport = false;
  String? exportFailureCode;
  Duration confirmationLifetime = const Duration(minutes: 5);
  Completer<void>? pendingImport;
  Completer<void>? pendingConfirmation;
  String? confirmationResource;
  Completer<void>? pendingRetrieval;
  String? retrievalFailureCode;
  int retrievalCalls = 0;
  String? confirmationFilename;
  int? confirmationSizeBytes;
  Completer<void>? pendingExport;
  String? lastImportDomain;
  final importedBytes = <List<int>>[];
  Map<String, dynamic>? contextEnvelope;
  List<String>? exportedRefs;
  String? exportedOutputKind;
  Map<String, dynamic>? savedExport;
  String? reopenedReference;
  String? reopenFailure;
  int reopenCalls = 0;
  final reopenBundles = <String, Map<String, dynamic>>{};
  String? listingFailure;
  final asset = <String, Object?>{
    'asset_id': 'MEDIA-aaaaaaaaaaaaaaaa',
    'filename': 'interview.mp4',
    'sha256': 'a' * 64,
    'duration_sec': 20.0,
    'media_kind': 'video_audio',
    'has_video': true,
    'audio_stream_count': 1,
    'evidence_refs': [],
    'rights_status': 'unknown',
  };
  final alternateAsset = <String, Object?>{
    'asset_id': 'MEDIA-bbbbbbbbbbbbbbbb',
    'filename': 'alternate.mp4',
    'sha256': 'b' * 64,
    'duration_sec': 20.0,
    'media_kind': 'video_audio',
    'has_video': true,
    'audio_stream_count': 1,
    'evidence_refs': [],
    'rights_status': 'unknown',
  };

  @override
  Map<String, dynamic>? get currentContextEnvelope => contextEnvelope;

  @override
  Future<ContentProjectFile> contentProjectFile({
    required String? domainId,
    required String artifactId,
    required bool package,
  }) async {
    retrievalCalls++;
    await pendingRetrieval?.future;
    final failureCode = retrievalFailureCode;
    if (failureCode != null) {
      throw LumenisCoreException(
        'private retrieval diagnostic',
        statusCode: 503,
        errorCode: failureCode,
      );
    }
    return ContentProjectFile(
      bytes: Uint8List.fromList([1, 2]),
      filename: 'project.mp4',
      mediaType: 'video/mp4',
    );
  }

  @override
  Future<Map<String, dynamic>> inspectContentMedia({
    required String? domainId,
    List<String>? assetPaths,
    List<String>? assetRefs,
  }) async {
    inspectCalls++;
    return {
      'ok': true,
      'assets': [asset],
    };
  }

  @override
  Future<Map<String, dynamic>> importContentSource({
    required String? domainId,
    required String filename,
    required Uint8List bytes,
  }) async {
    imports++;
    importCalls++;
    lastImportDomain = domainId;
    importedBytes.add(List<int>.unmodifiable(bytes));
    await pendingImport?.future;
    if (approvalRequired && importCalls == 1) {
      throw LumenisCoreException(
        'approval required',
        statusCode: 403,
        errorCode: 'CONTENT_SOURCE_APPROVAL_REQUIRED',
        sourceConfirmation: ContentSourceConfirmation(
          confirmationId: 'CONF-widget',
          resource:
              confirmationResource ??
              'content-source-import:${domainId == null ? 'shared-workspace:' : ''}v1:${'b' * 64}',
          expiresAt: DateTime.now().add(confirmationLifetime),
          filename: confirmationFilename ?? filename,
          sizeBytes: confirmationSizeBytes ?? bytes.length,
          bodySha256: 'd' * 64,
        ),
      );
    }
    return {
      'ok': true,
      'publish_status': 'not_performed',
      'result': {
        'artifact': {
          'artifact_id': filename == 'alternate.mp4'
              ? 'ART-source-alternate'
              : 'ART-source',
        },
        'asset': filename == 'alternate.mp4' ? alternateAsset : asset,
      },
    };
  }

  @override
  Future<Map<String, dynamic>> confirmContentSource({
    required String? domainId,
    required String confirmationId,
    required bool confirmed,
  }) async {
    confirmationCalls++;
    confirmedImport = confirmed;
    lastImportDomain = domainId;
    await pendingConfirmation?.future;
    return confirmed
        ? {
            'ok': true,
            'status': 'ready_for_retry',
            'purpose': 'local_content_draft',
          }
        : {'ok': true, 'status': 'cancelled'};
  }

  @override
  Future<Map<String, dynamic>> exportContentProject({
    required String? domainId,
    List<String>? assetPaths,
    List<String>? assetRefs,
    required Map<String, dynamic> timeline,
    required String outputKind,
    bool? demoAcknowledged,
    String? previousArtifactId,
    String? title,
    bool renderMedia = true,
    Map<String, double> renderOptions = const {},
    Map<String, dynamic> deliveryOptions = const {},
  }) async {
    exports++;
    exportedRefs = assetRefs;
    exportedOutputKind = outputKind;
    await pendingExport?.future;
    final failureCode = exportFailureCode;
    if (failureCode != null) {
      throw LumenisCoreException(
        'private parent revision diagnostic',
        statusCode: 409,
        errorCode: failureCode,
      );
    }
    if (successfulExport) {
      final response = <String, dynamic>{
        'ok': true,
        'publish_status': 'not_performed',
        'evidence_recorded': true,
        'result': {
          'status': renderMedia ? 'rendered_staged' : 'project_saved',
          'artifact': {'artifact_id': 'ART-version'},
          'project': {
            'schema_version': title == null ? 1 : 2,
            'title': ?title,
            if (title != null) 'project_revision': 1,
            'output_kind': outputKind,
            'timeline': timeline,
            'render_options': renderOptions,
            'delivery_options': deliveryOptions,
            'rights': {'state': 'unknown', 'label': 'rights unknown'},
            'source_artifact_refs': assetRefs ?? const <String>[],
          },
          'render': !renderMedia
              ? {
                  'state': 'not_rendered',
                  'output_kind': outputKind,
                  'timeline_version': timeline['version'],
                }
              : {
                  'state': 'rendered_verified',
                  'output_kind': outputKind,
                  'measurement': {'actual_duration_sec': 1.0},
                  'size_bytes': 2,
                  'media_sha256': 'f' * 64,
                },
        },
      };
      savedExport = response;
      return response;
    }
    throw const LumenisCoreException(
      'private decoder detail',
      statusCode: 503,
      errorCode: 'CONTENT_RENDER_FAILED',
    );
  }

  @override
  Future<Map<String, dynamic>> listContentProjects({
    required String? domainId,
    int limit = 20,
    String? cursor,
  }) async {
    if (listingFailure != null) {
      throw LumenisCoreException(
        'private diagnostic',
        errorCode: listingFailure,
      );
    }
    return {
      'ok': true,
      'publish_status': 'not_performed',
      'status': savedExport == null ? 'empty' : 'ok',
      'projects': [
        if (savedExport != null)
          {
            'artifact_id': 'ART-version',
            'output_kind':
                ((savedExport!['result'] as Map)['project']
                    as Map)['output_kind'],
            'created_at': '2026-10-02 09:00:00',
            'updated_at': '2026-10-02 09:00:00',
            'status': 'staged',
            'title':
                ((savedExport!['result'] as Map)['project'] as Map)['title'],
            'project_revision':
                ((savedExport!['result'] as Map)['project']
                    as Map)['project_revision'],
          },
      ],
      'next_cursor': null,
    };
  }

  @override
  Future<Map<String, dynamic>> reopenContentProject({
    required String? domainId,
    required String artifactId,
  }) async {
    reopenCalls++;
    reopenedReference = artifactId;
    if (reopenFailure != null) {
      throw LumenisCoreException(
        'private diagnostic',
        statusCode: 403,
        errorCode: reopenFailure,
      );
    }
    if (reopenBundles[artifactId] case final response?) return response;
    final result = savedExport!['result'] as Map;
    return {
      'ok': true,
      'project': {'project': result['project'], 'render': result['render']},
    };
  }
}

class _Files extends MediaProjectFiles {
  int saves = 0;

  @override
  bool get canSave => true;

  @override
  Future<List<XFile>> choose() async => [
    XFile.fromData(
      Uint8List.fromList([1, 2]),
      path: 'interview.mp4',
      name: 'interview.mp4',
    ),
  ];

  @override
  Future<bool> save(ContentProjectFile content) async {
    saves++;
    return true;
  }
}

Widget _app(
  _Client client,
  MediaProjectController? controller, {
  String? invokingDomain,
  bool sharedWorkspace = false,
  Locale locale = const Locale('zh', 'CN'),
  double scale = 1,
  double sidebar = 0,
  EdgeInsets viewInsets = EdgeInsets.zero,
  bool contextAvailable = true,
  String initialOutputKind = 'video',
  LumenisLeaveGuard? guard,
  VoidCallback? onBack,
  MediaProjectFiles? files,
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
    ).copyWith(textScaler: TextScaler.linear(scale), viewInsets: viewInsets),
    child: RepaintBoundary(
      key: const Key('media-workbench-test-capture'),
      child: sidebar == 0
          ? child!
          : Row(
              children: [
                SizedBox(width: sidebar),
                Expanded(child: child!),
              ],
            ),
    ),
  ),
  home: guard == null
      ? _workbenchHome(
          client,
          controller,
          invokingDomain: invokingDomain,
          sharedWorkspace: sharedWorkspace,
          contextAvailable: contextAvailable,
          initialOutputKind: initialOutputKind,
          onBack: onBack,
          files: files ?? _Files(),
        )
      : LumenisLeaveScope(
          guard: guard,
          child: _workbenchHome(
            client,
            controller,
            invokingDomain: invokingDomain,
            sharedWorkspace: sharedWorkspace,
            contextAvailable: contextAvailable,
            initialOutputKind: initialOutputKind,
            onBack: onBack,
            files: files ?? _Files(),
          ),
        ),
);

Widget _workbenchHome(
  _Client client,
  MediaProjectController? controller, {
  String? invokingDomain,
  required bool sharedWorkspace,
  required bool contextAvailable,
  required String initialOutputKind,
  VoidCallback? onBack,
  required MediaProjectFiles files,
}) => Scaffold(
  body: MediaProjectWorkbench(
    client: client,
    invokingDomain: invokingDomain,
    sharedWorkspace: sharedWorkspace,
    controller: controller,
    contextAvailable: contextAvailable,
    initialOutputKind: initialOutputKind,
    files: files,
    onBack: onBack ?? () {},
  ),
);

Future<void> _prepareEditableProject(
  _Client client,
  MediaProjectController controller,
) async {
  await controller.importFile('interview.mp4', Uint8List.fromList([1]));
  controller.edit(
    (snapshot) => snapshot.addClip(
      snapshot.assets.single.assetId,
      trackId: 'video',
      sourceOut: 8,
    ),
  );
  controller.selectClip(controller.timeline!.tracks.single.clips.single.clipId);
}

Map<String, dynamic> _versionBundle(
  _Client client, {
  String? parent,
  int revision = 1,
}) {
  final asset = MediaProjectAsset.fromJson(client.asset);
  final timeline = MediaProjectSnapshot.empty(
    inspectedAssets: [asset],
  ).addClip(asset.assetId, trackId: 'video', sourceOut: 8);
  return {
    'ok': true,
    'project': {
      'project': {
        'schema_version': 2,
        'title': 'Same title and assets',
        'project_revision': revision,
        'parent_artifact_id': parent,
        'output_kind': 'video',
        'timeline': timeline.toJson(),
        'source_artifact_refs': ['ART-same-source'],
        'rights': {'state': 'unknown'},
      },
      'render': {
        'state': 'not_rendered',
        'output_kind': 'video',
        'timeline_version': timeline.version,
      },
    },
  };
}

Future<void> _openActionsForTarget(WidgetTester tester, Finder target) async {
  if (target.evaluate().isNotEmpty) return;
  final opener = find.byKey(const Key('media-open-actions'));
  expect(opener, findsOneWidget);
  await tester.ensureVisible(opener);
  await tester.tap(opener);
  await tester.pumpAndSettle();
  expect(target, findsOneWidget);
}

Future<void> _openPropertiesForField(WidgetTester tester, Finder field) async {
  if (field.evaluate().isNotEmpty) return;
  final opener = find.byKey(const Key('media-open-properties'));
  expect(opener, findsOneWidget);
  await tester.ensureVisible(opener);
  await tester.tap(opener);
  await tester.pumpAndSettle();
  expect(field, findsOneWidget);
}

Future<void> _expandClipOperationsForTarget(
  WidgetTester tester,
  Finder target,
) async {
  if (target.evaluate().isNotEmpty) return;
  final group = find.byKey(const Key('media-clip-operations'));
  await tester.ensureVisible(group);
  await tester.tap(group);
  await tester.pumpAndSettle();
  expect(target, findsOneWidget);
}

// Optional layout-only render of these explicitly synthetic widget fixtures.
// It is never a live product/media acceptance screenshot.
Future<void> _captureWorkbench(WidgetTester tester, String name) async {
  if (!const bool.fromEnvironment('OEVIRA_LAYOUT_CAPTURE')) return;
  await tester.runAsync(() async {
    final boundary = tester.renderObject<RenderRepaintBoundary>(
      find.byKey(const Key('media-workbench-test-capture')),
    );
    final image = await boundary.toImage();
    final bytes = await image.toByteData(format: ImageByteFormat.png);
    await File(
      '../work/media-workbench-layout-20261025-widget-$name.png',
    ).writeAsBytes(bytes!.buffer.asUint8List());
    image.dispose();
  });
}

Future<void> _layoutFonts(WidgetTester tester) async {
  if (!const bool.fromEnvironment('OEVIRA_LAYOUT_CAPTURE')) return;
  await tester.runAsync(() async {
    final icons = FontLoader('MaterialIcons')
      ..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'));
    await icons.load();
    for (final font in [
      ('LumenisSansSC', 'NotoSansSC.ttf'),
      ('LumenisSansKR', 'NotoSansKR.ttf'),
    ]) {
      final loader = FontLoader(font.$1)
        ..addFont(rootBundle.load('assets/fonts/${font.$2}'));
      await loader.load();
    }
  });
}

void main() {
  late _Client client;
  late MediaProjectController controller;
  setUp(() {
    client = _Client();
    controller = MediaProjectController(
      repository: CoreMediaProjectRepository(client),
      domain: 'BMP',
    );
  });
  tearDown(() => controller.dispose());

  testWidgets(
    'narrow source query refreshes its sheet and keeps the existing edit',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await _prepareEditableProject(client, controller);
      await tester.pumpWidget(_app(client, controller));
      await tester.pumpAndSettle();
      final original = controller.timeline!.toJson();
      final selection = controller.selectedClipId;
      await tester.tap(find.byKey(const Key('media-open-sources')));
      await tester.pumpAndSettle();
      final item = find.byKey(
        ValueKey(
          'media-bin-item/${controller.timeline!.assets.single.assetId}',
        ),
      );
      expect(item, findsOneWidget);
      await tester.enterText(
        find.byKey(const Key('media-source-search')),
        'no-match',
      );
      await tester.pumpAndSettle();
      expect(item, findsNothing);
      expect(find.text('没有匹配的素材。'), findsOneWidget);
      await tester.tap(find.byTooltip('清除搜索'));
      await tester.pumpAndSettle();
      expect(item, findsOneWidget);
      await tester.tap(find.byKey(const Key('media-close-layer')));
      await tester.pumpAndSettle();
      expect(controller.timeline!.toJson(), original);
      expect(controller.selectedClipId, selection);
      expect(client.sourcePreviewCalls, 0);
      expect(tester.takeException(), isNull);
    },
  );

  for (final locale in const [Locale('zh', 'CN'), Locale('en'), Locale('ko')]) {
    testWidgets(
      'editing desk at 1280 with shell keeps task tools monitor inspector and full timeline in $locale',
      (tester) async {
        await tester.binding.setSurfaceSize(const Size(1280, 800));
        addTearDown(() => tester.binding.setSurfaceSize(null));
        await _layoutFonts(tester);
        await _prepareEditableProject(client, controller);
        await tester.pumpWidget(
          _app(client, controller, locale: locale, sidebar: 248),
        );
        await tester.pumpAndSettle();
        final spine = find.byKey(const Key('media-tool-spine'));
        final source = find.byKey(const Key('media-source-rail'));
        final monitor = find.byKey(const ValueKey('media-preview-stage'));
        final properties = find.byKey(const Key('media-property-rail'));
        final timeline = find.byKey(const Key('media-timeline-region'));
        expect(spine, findsOneWidget);
        for (final field in [source, monitor, properties, timeline]) {
          expect(field, findsOneWidget);
          expect(tester.getRect(field).bottom, lessThanOrEqualTo(800));
        }
        expect(
          tester.getRect(spine).right,
          lessThan(tester.getRect(source).left),
        );
        expect(
          tester.getRect(source).right,
          lessThanOrEqualTo(tester.getRect(monitor).left),
        );
        expect(
          tester.getRect(monitor).right,
          lessThanOrEqualTo(tester.getRect(properties).left),
        );
        expect(
          tester.getSize(monitor).width,
          greaterThan(tester.getSize(source).width * 1.8),
        );
        expect(
          tester.getRect(timeline).left,
          lessThanOrEqualTo(tester.getRect(source).left),
        );
        expect(
          tester.getRect(timeline).right,
          greaterThanOrEqualTo(tester.getRect(properties).right),
        );
        final selection = controller.selectedClipId;
        final geometry = controller.timeline!.toJson();
        final query = find.byKey(const Key('media-source-search'));
        await tester.enterText(query, 'not-present-in-library');
        await tester.pump();
        expect(
          find.byKey(
            ValueKey(
              'media-bin-item/${controller.timeline!.assets.single.assetId}',
            ),
          ),
          findsNothing,
        );
        expect(find.byKey(ValueKey('media-clip-$selection')), findsOneWidget);
        expect(controller.timeline!.toJson(), geometry);
        await tester.enterText(
          query,
          controller.timeline!.assets.single.filename,
        );
        await tester.pump();
        expect(
          find.byKey(
            ValueKey(
              'media-bin-item/${controller.timeline!.assets.single.assetId}',
            ),
          ),
          findsOneWidget,
        );
        expect(controller.selectedClipId, selection);
        expect(client.sourcePreviewCalls, 0);
        await tester.tap(find.byKey(const Key('media-open-sources')));
        await tester.pumpAndSettle();
        expect(source, findsNothing);
        expect(tester.getSize(monitor).width, greaterThan(600));
        await tester.tap(find.byKey(const Key('media-open-sources')));
        await tester.pumpAndSettle();
        expect(source, findsOneWidget);
        expect(controller.timeline!.toJson(), geometry);
        await tester.enterText(query, '');
        FocusManager.instance.primaryFocus?.unfocus();
        await tester.pumpAndSettle();
        await _captureWorkbench(tester, locale.languageCode);
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets(
    'version chain excludes unrelated works with identical metadata',
    (tester) async {
      client.reopenBundles.addAll({
        'ART-a1': _versionBundle(client),
        'ART-b1': _versionBundle(client),
      });
      await controller.reopen('ART-a1');
      await tester.binding.setSurfaceSize(const Size(1440, 1100));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(_app(client, controller));
      await _openActionsForTarget(
        tester,
        find.byKey(const Key('media-reopen-ART-a1')),
      );
      await controller.reopen('ART-b1');
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('media-reopen-ART-a1')), findsNothing);
      final current = find.byKey(const Key('media-reopen-ART-b1'));
      expect(current, findsOneWidget);
      await tester.ensureVisible(current);
      await tester.tap(current);
      await tester.pumpAndSettle();
      expect(client.reopenedReference, 'ART-b1');
      expect(controller.version?.projectRevision, 1);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('version chain retains explicit parents children and siblings', (
    tester,
  ) async {
    client.reopenBundles.addAll({
      'ART-a1': _versionBundle(client),
      'ART-a2': _versionBundle(client, parent: 'ART-a1', revision: 2),
      'ART-a3': _versionBundle(client, parent: 'ART-a1', revision: 2),
    });
    await controller.reopen('ART-a1');
    await tester.binding.setSurfaceSize(const Size(1440, 1100));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(_app(client, controller));
    await _openActionsForTarget(
      tester,
      find.byKey(const Key('media-reopen-ART-a1')),
    );
    await controller.reopen('ART-a2');
    await tester.pumpAndSettle();
    expect(controller.version?.parentArtifactId, 'ART-a1');
    expect(find.byKey(const Key('media-reopen-ART-a1')), findsOneWidget);
    expect(find.byKey(const Key('media-reopen-ART-a2')), findsOneWidget);
    await controller.reopen('ART-a3');
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('media-reopen-ART-a2')), findsOneWidget);
    final parent = find.byKey(const Key('media-reopen-ART-a1'));
    await tester.ensureVisible(parent);
    await tester.tap(parent);
    await tester.pumpAndSettle();
    expect(client.reopenedReference, 'ART-a1');
    expect(controller.version?.artifactId, 'ART-a1');
    expect(find.byKey(const Key('media-reopen-ART-a2')), findsOneWidget);
    expect(find.byKey(const Key('media-reopen-ART-a3')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('version chain clears on new import and context quarantine', (
    tester,
  ) async {
    client.reopenBundles.addAll({
      'ART-a1': _versionBundle(client),
      'ART-a2': _versionBundle(client, parent: 'ART-a1', revision: 2),
    });
    await controller.reopen('ART-a1');
    await tester.binding.setSurfaceSize(const Size(1440, 1100));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(_app(client, controller));
    await _openActionsForTarget(
      tester,
      find.byKey(const Key('media-reopen-ART-a1')),
    );
    await controller.reopen('ART-a2');
    await tester.pumpAndSettle();
    await controller.importFile('another.mp4', Uint8List.fromList([1]));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('media-reopen-ART-a1')), findsNothing);
    expect(find.byKey(const Key('media-reopen-ART-a2')), findsOneWidget);
    await tester.pumpWidget(_app(client, controller, contextAvailable: false));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('media-reopen-ART-a2')), findsNothing);
    await tester.pumpWidget(_app(client, controller));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('media-reopen-ART-a2')), findsNothing);
    expect(controller.sourcesNeedRevalidation, isTrue);
    expect(tester.takeException(), isNull);
  });

  testWidgets('version chain rebinds a changed controller without old cache', (
    tester,
  ) async {
    client.reopenBundles.addAll({
      'ART-a1': _versionBundle(client),
      'ART-b1': _versionBundle(client),
    });
    final next = MediaProjectController(
      repository: CoreMediaProjectRepository(client),
      domain: 'BMP',
    );
    addTearDown(next.dispose);
    await controller.reopen('ART-a1');
    await next.reopen('ART-b1');
    await tester.binding.setSurfaceSize(const Size(1440, 1100));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(_app(client, controller));
    await _openActionsForTarget(
      tester,
      find.byKey(const Key('media-reopen-ART-a1')),
    );
    await tester.pumpWidget(_app(client, next));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('media-reopen-ART-a1')), findsNothing);
    expect(find.byKey(const Key('media-reopen-ART-b1')), findsOneWidget);
    // A late update from the detached, caller-owned controller cannot repopulate it.
    controller.setTitle('Unrelated old edit');
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('media-reopen-ART-a1')), findsNothing);
    expect(next.title, 'Same title and assets');
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'source preview preserves the edit and returns after narrow layout',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await controller.importFile('chosen.mp4', Uint8List.fromList([1]));
      controller.edit(
        (s) =>
            s.addClip(s.assets.single.assetId, trackId: 'video', sourceOut: 1),
      );
      final before = controller.timeline!.toJson();
      await tester.pumpWidget(_app(client, controller));
      await tester.tap(
        find.byKey(
          Key(
            'media-preview-source-${controller.timeline!.assets.single.assetId}',
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(client.previewSourceRef, controller.sourceRefs.single);
      expect(
        client.previewSourceSha,
        controller.timeline!.assets.single.sha256,
      );
      final player = tester.widget<MediaPreview>(find.byType(MediaPreview));
      expect(player.onPositionChanged, isNull);
      expect(player.seekPosition, isNull);
      expect(controller.timeline!.toJson(), before);
      tester.view.physicalSize = const Size(390, 844);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('media-source-monitor')), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.tap(find.byKey(const Key('media-close-source-preview')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('media-source-monitor')), findsNothing);
      expect(controller.timeline!.toJson(), before);
      expect(controller.hasUnsavedChanges, isTrue);
      expect(client.retrievalCalls, 0);
    },
  );

  testWidgets(
    'source preview retries without editing and discards revoked response',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await controller.importFile('chosen.mp4', Uint8List.fromList([1]));
      final before = controller.timeline!.toJson();
      client.sourcePreviewFailure = true;
      await tester.pumpWidget(_app(client, controller));
      await tester.tap(
        find.byKey(
          Key(
            'media-preview-source-${controller.timeline!.assets.single.assetId}',
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(
        find.byKey(const Key('media-retry-source-preview')),
        findsOneWidget,
      );
      expect(controller.timeline!.toJson(), before);
      client.sourcePreviewPending = Completer<ContentProjectFile>();
      await tester.tap(find.byKey(const Key('media-retry-source-preview')));
      await tester.pump();
      await tester.pumpWidget(
        _app(client, controller, contextAvailable: false),
      );
      await tester.pump();
      client.sourcePreviewPending!.complete(
        ContentProjectFile(
          bytes: Uint8List.fromList([1]),
          filename: 'source.mp4',
          mediaType: 'video/mp4',
        ),
      );
      await tester.pumpAndSettle();
      expect(find.byType(MediaPreview), findsNothing);
      expect(find.byKey(const Key('media-source-monitor')), findsNothing);
      expect(client.sourcePreviewCalls, 2);
      expect(tester.takeException(), isNull);
    },
  );

  Future<void> prepareAudioProject() async {
    client.asset
      ..['filename'] = 'voice.wav'
      ..['media_kind'] = 'audio'
      ..['has_video'] = false;
    await controller.importFile('voice.wav', Uint8List.fromList([1]));
    controller.edit(
      (snapshot) => snapshot
          .addAudioTrack('voiceover', audioRole: 'voiceover')
          .addClip(
            snapshot.assets.single.assetId,
            trackId: 'voiceover',
            sourceOut: 8,
          ),
    );
  }

  testWidgets('named project saves independently with no rendered preview', (
    tester,
  ) async {
    client.successfulExport = true;
    await controller.importFile('chosen.mp4', Uint8List.fromList([1]));
    controller.edit(
      (s) => s.addClip(s.assets.single.assetId, trackId: 'video', sourceOut: 1),
    );
    await tester.pumpWidget(_app(client, controller));
    await tester.tap(find.byKey(const Key('media-project-name')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('media-project-name-input')),
      'An editable film',
    );
    await tester.tap(find.text('应用调整').last);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('media-save-project')));
    await tester.pumpAndSettle();
    expect(controller.version!.title, 'An editable film');
    expect(controller.version!.rendered, isFalse);
    expect(controller.hasUnsavedChanges, isFalse);
    expect(find.text('An editable film'), findsOneWidget);
    await _openActionsForTarget(
      tester,
      find.byKey(const Key('media-version-preview')),
    );
    expect(
      tester
          .widget<OutlinedButton>(
            find.byKey(const Key('media-version-preview')),
          )
          .onPressed,
      isNull,
    );
  });

  testWidgets('selected landscape format is exported and can be undone', (
    tester,
  ) async {
    await _prepareEditableProject(client, controller);
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(_app(client, controller));
    await tester.tap(find.byKey(const Key('media-format-ratio')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('media-format-16:9')));
    await tester.pumpAndSettle();
    expect(controller.timeline!.formatRatio, '16:9');
    client.successfulExport = true;
    await controller.export(outputKind: 'video');
    await tester.pumpAndSettle();
    expect(controller.version!.timelineJson['format_ratio'], '16:9');
    controller.edit((s) => s.undo());
    await tester.pumpAndSettle();
    expect(controller.timeline!.formatRatio, '9:16');
    expect(controller.hasUnsavedChanges, isTrue);
    expect(controller.version!.timelineJson['format_ratio'], '16:9');
  });

  testWidgets(
    'podcast delivery format choice stays local until save or export',
    (tester) async {
      await prepareAudioProject();
      await tester.binding.setSurfaceSize(const Size(1440, 1100));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(
        _app(client, controller, initialOutputKind: 'audio'),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('media-open-actions')));
      await tester.pumpAndSettle();
      for (final format in ['mp3', 'm4a']) {
        final checkbox = find.byKey(Key('media-format-$format'));
        expect(tester.widget<CheckboxListTile>(checkbox).value, isFalse);
        await tester.ensureVisible(checkbox);
        await tester.tap(checkbox);
        await tester.pumpAndSettle();
      }
      expect(controller.deliveryOptions['audio_formats'], ['m4a', 'mp3']);
      expect(client.exports, 0);
      controller.setTitle('Audio delivery');
      client.successfulExport = true;
      await controller.export(outputKind: 'audio', renderMedia: false);
      await tester.pumpAndSettle();
      expect(controller.version!.rendered, isFalse);
      expect(controller.version!.deliveryOptions['audio_formats'], [
        'm4a',
        'mp3',
      ]);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'podcast desk keeps the real waveform and voice tools instead of video controls',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1280, 800));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await _layoutFonts(tester);
      await prepareAudioProject();
      await tester.pumpWidget(
        _app(client, controller, initialOutputKind: 'audio', sidebar: 248),
      );
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('media-tool-spine')), findsOneWidget);
      expect(find.byKey(const Key('media-source-waveform')), findsOneWidget);
      expect(find.byKey(const Key('media-format-ratio')), findsNothing);
      await _openPropertiesForField(
        tester,
        find.byKey(const Key('media-mastering')),
      );
      expect(find.byKey(const Key('media-mastering')), findsOneWidget);
      expect(find.byKey(const Key('media-timeline-region')), findsOneWidget);
      await _captureWorkbench(tester, 'podcast');
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('podcast does not expose video format controls', (tester) async {
    await prepareAudioProject();
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      _app(client, controller, initialOutputKind: 'audio'),
    );
    expect(find.byKey(const Key('media-format-ratio')), findsNothing);
    await tester.pumpAndSettle();
    expect(find.text('画面'), findsNothing);
    expect(find.byKey(const Key('media-source-waveform')), findsOneWidget);
  });

  testWidgets('new voiceover follows the existing clip and undo preserves it', (
    tester,
  ) async {
    await prepareAudioProject();
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      _app(client, controller, initialOutputKind: 'audio'),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('添加片段 · voice.wav'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('添加片段').last);
    await tester.pumpAndSettle();
    final clips = controller.timeline!.tracks
        .singleWhere((t) => t.trackId == 'voiceover')
        .clips;
    expect(clips.length, 2);
    expect(clips.last.timelineStart, 8);
    controller.edit((s) => s.undo());
    await tester.pumpAndSettle();
    expect(
      controller.timeline!.tracks
          .singleWhere((t) => t.trackId == 'voiceover')
          .clips
          .length,
      1,
    );
  });

  testWidgets('saved project chooser shows its real name and revision', (
    tester,
  ) async {
    client.successfulExport = true;
    await prepareAudioProject();
    controller.setTitle('An actual programme');
    await controller.export(outputKind: 'audio', renderMedia: false);
    await tester.pumpWidget(
      _app(client, controller, initialOutputKind: 'audio'),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('media-open-saved')));
    await tester.pumpAndSettle();
    final row = find.byKey(const Key('media-saved-project-ART-version'));
    expect(
      find.descendant(of: row, matching: find.text('An actual programme')),
      findsOneWidget,
    );
    expect(find.descendant(of: row, matching: find.text('v1')), findsOneWidget);
    expect(
      find.descendant(of: row, matching: find.text('ART-version')),
      findsNothing,
    );
  });

  Future<void> prepareBatch(WidgetTester tester) async {
    await _prepareEditableProject(client, controller);
    controller.edit(
      (s) => s.addClip(s.assets.single.assetId, trackId: 'video', sourceOut: 8),
    );
    await tester.binding.setSurfaceSize(const Size(1440, 1100));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(_app(client, controller));
    await tester.pumpAndSettle();
  }

  Finder sourceEnd() => find.byWidgetPredicate(
    (w) => w is TextField && w.decoration?.labelText == '素材终点（秒）',
  );

  Future<void> draftBoth(WidgetTester tester) async {
    final ids = controller.timeline!.tracks.single.clips
        .map((c) => c.clipId)
        .toList();
    for (var i = 0; i < ids.length; i++) {
      final clip = find.byKey(ValueKey('media-clip-${ids[i]}'));
      await tester.ensureVisible(clip);
      await tester.tap(clip);
      await tester.pumpAndSettle();
      await tester.enterText(sourceEnd(), i == 0 ? '6' : '7');
      tester.testTextInput.hide();
      await tester.pumpAndSettle();
    }
  }

  Future<void> previewBatch(WidgetTester tester) async {
    final button = find.byKey(const Key('media-batch-preview'));
    await tester.ensureVisible(button);
    await tester.tap(button);
    await tester.pumpAndSettle();
    expect(controller.busy, isFalse);
    expect(find.byType(WaitingFeedback), findsNothing);
    expect(find.byType(LinearProgressIndicator), findsNothing);
  }

  testWidgets(
    'multi-clip drafts preview cancel adopt and undo through existing inspector',
    (tester) async {
      await prepareBatch(tester);
      final base = controller.timeline!;
      await draftBoth(tester);
      await previewBatch(tester);
      expect(client.batchCalls, 1);
      expect(client.batchCommands, hasLength(2));
      expect(controller.timeline, same(base));
      expect(client.exports, 0);
      expect(
        find.byKey(const Key('media-batch-preview-dialog')),
        findsOneWidget,
      );
      expect(
        tester
            .widget<OutlinedButton>(
              find.byKey(const Key('media-batch-preview')),
            )
            .onPressed,
        isNull,
      );
      expect(
        tester
            .widget<FilledButton>(find.byKey(const Key('media-batch-adopt')))
            .onPressed,
        isNotNull,
      );
      expect(
        tester
            .widget<TextButton>(find.byKey(const Key('media-batch-cancel')))
            .onPressed,
        isNotNull,
      );
      await tester.tap(find.byKey(const Key('media-batch-cancel')));
      await tester.pumpAndSettle();
      expect(controller.timeline, same(base));
      expect(tester.widget<TextField>(sourceEnd()).controller!.text, '7');
      expect(
        tester
            .widget<OutlinedButton>(
              find.byKey(const Key('media-batch-preview')),
            )
            .onPressed,
        isNotNull,
      );
      await previewBatch(tester);
      await tester.tap(find.byKey(const Key('media-batch-adopt')));
      await tester.pumpAndSettle();
      expect(controller.timeline!.tracks.single.clips.map((c) => c.sourceOut), [
        6,
        7,
      ]);
      expect(client.exports, 0);
      final undo = find.byKey(const Key('media-toolbar-undo'));
      await tester.ensureVisible(undo);
      await tester.tap(undo);
      await tester.pumpAndSettle();
      expect(controller.timeline!.tracks.single.clips.map((c) => c.sourceOut), [
        8,
        8,
      ]);
      expect(controller.timeline!.canUndo, isTrue);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('batch denial retains every pending field and supports retry', (
    tester,
  ) async {
    await prepareBatch(tester);
    await draftBoth(tester);
    final base = controller.timeline;
    client.batchFailureCode = 'CONTENT_SCOPE_DENIED';
    await previewBatch(tester);
    expect(find.byKey(const Key('media-batch-preview-dialog')), findsNothing);
    expect(controller.timeline, same(base));
    expect(tester.widget<TextField>(sourceEnd()).controller!.text, '7');
    expect(find.textContaining('private batch diagnostic'), findsNothing);
    client.batchFailureCode = null;
    await previewBatch(tester);
    expect(client.batchCommands, hasLength(2));
    await tester.tap(find.byKey(const Key('media-batch-cancel')));
    await tester.pumpAndSettle();
  });

  testWidgets(
    'a changed split draft blocks batch without dropping adjustments',
    (tester) async {
      await prepareBatch(tester);
      await draftBoth(tester);
      final field = find.byWidgetPredicate(
        (w) => w is TextField && w.decoration?.labelText == '分割位置（素材秒）',
      );
      final operations = find.byKey(const Key('media-clip-operations'));
      await tester.ensureVisible(operations);
      await tester.tap(operations);
      await tester.pumpAndSettle();
      await tester.enterText(field, '3');
      tester.testTextInput.hide();
      await tester.pumpAndSettle();
      await previewBatch(tester);
      expect(client.batchCalls, 0);
      expect(tester.widget<TextField>(sourceEnd()).controller!.text, '7');
      expect(controller.timeline!.tracks.single.clips.map((c) => c.sourceOut), [
        8,
        8,
      ]);
    },
  );

  testWidgets('a newer draft while preview awaits cannot be adopted', (
    tester,
  ) async {
    await prepareBatch(tester);
    await draftBoth(tester);
    client.pendingBatch = Completer<void>();
    final button = find.byKey(const Key('media-batch-preview'));
    await tester.ensureVisible(button);
    await tester.tap(button);
    await tester.pump();
    expect(controller.busy, isTrue);
    expect(find.byType(LinearProgressIndicator), findsWidgets);
    await tester.enterText(sourceEnd(), '5');
    client.pendingBatch!.complete();
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('media-batch-preview-dialog')), findsNothing);
    expect(tester.widget<TextField>(sourceEnd()).controller!.text, '5');
    expect(controller.timeline!.tracks.single.clips.map((c) => c.sourceOut), [
      8,
      8,
    ]);
  });

  testWidgets('context invalidation disables an already visible adoption', (
    tester,
  ) async {
    await prepareBatch(tester);
    await draftBoth(tester);
    await previewBatch(tester);
    controller.quarantineDraftSources();
    controller.selectClip(controller.selectedClipId);
    await tester.pumpAndSettle();
    final adopt = tester.widget<FilledButton>(
      find.byKey(const Key('media-batch-adopt')),
    );
    expect(adopt.onPressed, isNull);
    await tester.tap(find.byKey(const Key('media-batch-cancel')));
    await tester.pumpAndSettle();
    expect(client.exports, 0);
  });

  testWidgets(
    'video reflow preserves pending clip edits without treating hidden position as intent',
    (tester) async {
      await prepareBatch(tester);
      final ids = controller.timeline!.tracks.single.clips
          .map((c) => c.clipId)
          .toList();
      final second = find.byKey(ValueKey('media-clip-${ids.last}'));
      await tester.ensureVisible(second);
      await tester.tap(second);
      await tester.pumpAndSettle();
      await tester.enterText(sourceEnd(), '7');
      tester.testTextInput.hide();
      final first = find.byKey(ValueKey('media-clip-${ids.first}'));
      await tester.ensureVisible(first);
      await tester.tap(first);
      await tester.pumpAndSettle();
      await tester.enterText(sourceEnd(), '6');
      tester.testTextInput.hide();
      final apply = find.text('应用调整');
      await tester.ensureVisible(apply);
      await tester.tap(apply);
      await tester.pumpAndSettle();
      expect(controller.timeline!.tracks.single.clips.last.timelineStart, 6);
      await tester.ensureVisible(second);
      await tester.tap(second);
      await tester.pumpAndSettle();
      expect(tester.widget<TextField>(sourceEnd()).controller!.text, '7');
      await previewBatch(tester);
      expect(client.batchCalls, 1);
      expect(client.batchCommands!.map((c) => c['op']), ['trim']);
      await tester.tap(find.byKey(const Key('media-batch-adopt')));
      await tester.pumpAndSettle();
      expect(controller.timeline!.tracks.single.clips.map((c) => c.sourceOut), [
        6,
        7,
      ]);
      expect(controller.timeline!.tracks.single.clips.last.timelineStart, 6);
    },
  );

  testWidgets(
    'pending stream selection is preserved and blocks partial batch adoption',
    (tester) async {
      await prepareBatch(tester);
      await draftBoth(tester);
      final sound = find.byKey(const Key('media-sound-settings'));
      await tester.ensureVisible(sound);
      await tester.tap(sound);
      await tester.pumpAndSettle();
      final stream = find.byWidgetPredicate(
        (w) => w is DropdownButtonFormField<int>,
      );
      await tester.ensureVisible(stream);
      await tester.tap(stream);
      await tester.pumpAndSettle();
      await tester.tap(find.text('静音').last);
      await tester.pumpAndSettle();
      await previewBatch(tester);
      expect(client.batchCalls, 0);
      expect(tester.widget<TextField>(sourceEnd()).controller!.text, '7');
      expect(
        controller.timeline!.tracks.single.clips.last.audioRole,
        'original',
      );
      expect(find.text('静音'), findsOneWidget);
    },
  );

  testWidgets(
    'pending replacement on another clip is never discarded by batch',
    (tester) async {
      await prepareBatch(tester);
      final ids = controller.timeline!.tracks.single.clips
          .map((c) => c.clipId)
          .toList();
      final replace = find.byKey(const Key('media-replace-source'));
      await tester.ensureVisible(replace);
      await tester.tap(replace);
      await tester.pumpAndSettle();
      final other = find.byKey(ValueKey('media-clip-${ids.last}'));
      await tester.ensureVisible(other);
      await tester.tap(other);
      await tester.pumpAndSettle();
      await tester.enterText(sourceEnd(), '7');
      tester.testTextInput.hide();
      await tester.pumpAndSettle();
      await previewBatch(tester);
      expect(client.batchCalls, 0);
      final first = find.byKey(ValueKey('media-clip-${ids.first}'));
      await tester.ensureVisible(first);
      await tester.tap(first);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('media-replacement-cancel')), findsOneWidget);
      expect(controller.timeline!.tracks.single.clips.map((c) => c.sourceOut), [
        8,
        8,
      ]);
    },
  );

  testWidgets(
    'inspector retains field identity and focus when dirty controls appear',
    (tester) async {
      await _prepareEditableProject(client, controller);
      controller.selectClip(
        controller.timeline!.tracks.single.clips.single.clipId,
      );
      await tester.binding.setSurfaceSize(const Size(1440, 1100));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(_app(client, controller));
      await tester.pumpAndSettle();
      final endField = sourceEnd();
      await tester.ensureVisible(endField);
      await tester.showKeyboard(endField);
      final editable = find.descendant(
        of: endField,
        matching: find.byType(EditableText),
      );
      final state = tester.state<EditableTextState>(editable);
      expect(state.widget.focusNode.hasFocus, isTrue);
      expect(find.byKey(const Key('media-apply-before-replace')), findsNothing);
      await tester.enterText(endField, '7');
      await tester.pump();
      expect(
        find.byKey(const Key('media-apply-before-replace')),
        findsOneWidget,
      );
      expect(
        identical(tester.state<EditableTextState>(editable), state),
        isTrue,
      );
      expect(state.widget.focusNode.hasFocus, isTrue);
      expect(tester.widget<TextField>(endField).controller!.text, '7');
      await tester.enterText(endField, '6');
      await tester.pump();
      expect(
        identical(tester.state<EditableTextState>(editable), state),
        isTrue,
      );
      expect(state.widget.focusNode.hasFocus, isTrue);
      expect(tester.widget<TextField>(endField).controller!.text, '6');
      expect(controller.timeline!.tracks.single.clips.single.sourceOut, 8);
      expect(client.batchCalls, 0);
      expect(client.exports, 0);
    },
  );

  testWidgets('audio range position and fades use ordered batch commands', (
    tester,
  ) async {
    await _prepareEditableProject(client, controller);
    controller.edit(
      (s) => s
          .addAudioTrack('voice', audioRole: 'voiceover')
          .addClip(
            s.assets.single.assetId,
            trackId: 'voice',
            sourceOut: 8,
            audioRole: 'voiceover',
            audioStreamIndex: 0,
          ),
    );
    final id = controller.timeline!.tracks.last.clips.single.clipId;
    controller.edit(
      (s) => s.setAudioMix(id, const MediaProjectAudioMix(fadeInSec: 4)),
    );
    controller.selectClip(id);
    await tester.binding.setSurfaceSize(const Size(1440, 1100));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(_app(client, controller));
    await tester.pumpAndSettle();
    Finder field(String label) => find.byWidgetPredicate(
      (w) => w is TextField && w.decoration?.labelText == label,
    );
    await tester.enterText(sourceEnd(), '3');
    await tester.enterText(field('时间线位置（秒）'), '1');
    final sound = find.byKey(const Key('media-sound-settings'));
    await tester.ensureVisible(sound);
    await tester.tap(sound);
    await tester.pumpAndSettle();
    await tester.enterText(field('音量'), '0.5');
    await tester.enterText(field('淡入（秒）'), '1');
    await tester.enterText(field('淡出（秒）'), '1');
    tester.testTextInput.hide();
    await tester.pumpAndSettle();
    await previewBatch(tester);
    expect(client.batchCommands!.map((c) => c['op']), [
      'audio_mix',
      'trim',
      'move_audio_clip',
    ]);
    await tester.tap(find.byKey(const Key('media-batch-adopt')));
    await tester.pumpAndSettle();
    final clip = controller.timeline!.tracks.last.clips.single;
    expect(clip.sourceOut, 3);
    expect(clip.timelineStart, 1);
    expect(clip.audioMix.toJson(), {
      'volume': .5,
      'fade_in_sec': 1.0,
      'fade_out_sec': 1.0,
      'ducking': false,
    });
    expect(client.exports, 0);
  });

  testWidgets(
    'audio range position and fades retain draft across staged input frames',
    (tester) async {
      await _prepareEditableProject(client, controller);
      controller.edit(
        (s) => s
            .addAudioTrack('voice', audioRole: 'voiceover')
            .addClip(
              s.assets.single.assetId,
              trackId: 'voice',
              sourceOut: 8,
              audioRole: 'voiceover',
              audioStreamIndex: 0,
            ),
      );
      final id = controller.timeline!.tracks.last.clips.single.clipId;
      controller.edit(
        (s) => s.setAudioMix(id, const MediaProjectAudioMix(fadeInSec: 4)),
      );
      controller.selectClip(id);
      await tester.binding.setSurfaceSize(const Size(1440, 1100));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(_app(client, controller));
      await tester.pumpAndSettle();
      Finder field(String label) => find.byWidgetPredicate(
        (w) => w is TextField && w.decoration?.labelText == label,
      );
      expect(controller.timeline!.tracks.last.clips.single.timelineStart, 0);
      await tester.enterText(sourceEnd(), '3');
      await tester.pump();
      final position = field('时间线位置（秒）');
      await tester.ensureVisible(position);
      await tester.enterText(position, '1');
      await tester.pump();
      expect(tester.widget<TextField>(position).controller!.text, '1');
      final sound = find.byKey(const Key('media-sound-settings'));
      await tester.ensureVisible(sound);
      await tester.tap(sound);
      await tester.pumpAndSettle();
      expect(tester.widget<TextField>(position).controller!.text, '1');
      await tester.enterText(field('音量'), '0.5');
      await tester.pump();
      await tester.enterText(field('淡入（秒）'), '1');
      await tester.pump();
      await tester.enterText(field('淡出（秒）'), '1');
      await tester.pump();
      expect(tester.widget<TextField>(position).controller!.text, '1');
      tester.testTextInput.hide();
      await tester.pumpAndSettle();
      await previewBatch(tester);
      expect(client.batchCommands!.map((c) => c['op']), [
        'audio_mix',
        'trim',
        'move_audio_clip',
      ]);
      await tester.tap(find.byKey(const Key('media-batch-adopt')));
      await tester.pumpAndSettle();
      final clip = controller.timeline!.tracks.last.clips.single;
      expect(clip.sourceOut, 3);
      expect(clip.timelineStart, 1);
      expect(clip.audioMix.toJson(), {
        'volume': .5,
        'fade_in_sec': 1.0,
        'fade_out_sec': 1.0,
        'ducking': false,
      });
      expect(client.exports, 0);
    },
  );

  testWidgets('closing the narrow inspector suppresses a late preview dialog', (
    tester,
  ) async {
    await prepareBatch(tester);
    await draftBoth(tester);
    await tester.binding.setSurfaceSize(const Size(390, 844));
    await tester.pumpAndSettle();
    final button = find.byKey(const Key('media-batch-preview'));
    await _openPropertiesForField(tester, button);
    await tester.ensureVisible(button);
    client.pendingBatch = Completer<void>();
    await tester.tap(button);
    await tester.pump();
    await tester.tap(find.byKey(const Key('media-close-layer')));
    await tester.pump(const Duration(milliseconds: 500));
    client.pendingBatch!.complete();
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('media-batch-preview-dialog')), findsNothing);
    expect(find.byKey(const Key('media-close-layer')), findsNothing);
    await _openPropertiesForField(tester, button);
    expect(tester.widget<TextField>(sourceEnd()).controller!.text, '7');
    expect(controller.timeline!.tracks.single.clips.map((c) => c.sourceOut), [
      8,
      8,
    ]);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'source replacement can open on a timeline with a valid dissolve',
    (tester) async {
      await _prepareEditableProject(client, controller);
      await controller.importFile('alternate.mp4', Uint8List.fromList([2]));
      controller.edit((snapshot) {
        final assetId = snapshot.assets.first.assetId;
        return snapshot.addClip(
          assetId,
          trackId: 'video',
          sourceIn: 8,
          sourceOut: 16,
          audioRole: 'muted',
        );
      });
      final current = controller.timeline!;
      final clips = current.tracks.single.clips;
      final payload = current.toJson();
      payload['transitions'] = [
        {
          'from_clip': clips[0].clipId,
          'to_clip': clips[1].clipId,
          'transition_type': 'dissolve',
          'duration_sec': 0.5,
          'reason': 'soft scene change',
        },
      ];
      controller.edit(
        (_) => MediaProjectSnapshot.fromJson(
          payload,
          inspectedAssets: current.assets,
        ),
      );

      await tester.binding.setSurfaceSize(const Size(1440, 1100));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(_app(client, controller));
      final replaceButton = find.byKey(const Key('media-replace-source'));
      await _openPropertiesForField(tester, replaceButton);
      expect(tester.widget<OutlinedButton>(replaceButton).onPressed, isNotNull);
      await tester.ensureVisible(replaceButton);
      await tester.tap(replaceButton);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('media-replacement-apply')), findsOneWidget);
      expect(
        find.byWidgetPredicate(
          (widget) =>
              widget is DropdownButtonFormField<String> &&
              widget.key is ValueKey<String> &&
              (widget.key as ValueKey<String>).value.startsWith(
                'media-replacement-source-',
              ),
        ),
        findsOneWidget,
      );
      expect(controller.timeline!.transitions, hasLength(1));
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('empty source replacement offers a localized import action', (
    tester,
  ) async {
    await _prepareEditableProject(client, controller);
    await tester.binding.setSurfaceSize(const Size(1440, 1100));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    const locales = <(Locale, String)>[
      (Locale('zh', 'CN'), '导入素材'),
      (Locale('en'), 'Import media'),
      (Locale('ko'), '미디어 가져오기'),
    ];
    for (final (locale, expectedLabel) in locales) {
      await tester.pumpWidget(_app(client, controller, locale: locale));
      final replaceButton = find.byKey(const Key('media-replace-source'));
      await _openPropertiesForField(tester, replaceButton);
      await tester.ensureVisible(replaceButton);
      await tester.tap(replaceButton);
      await tester.pumpAndSettle();

      final importButton = find.byKey(const Key('media-replacement-import'));
      expect(importButton, findsOneWidget);
      expect(find.text(expectedLabel), findsOneWidget);
      expect(find.text('sh01.media.import'), findsNothing);
      expect(tester.takeException(), isNull);

      await tester.tap(find.byKey(const Key('media-replacement-cancel')));
      await tester.pumpAndSettle();
    }
  });

  testWidgets(
    'open saved-work dialog clears a completed list on available scope change',
    (tester) async {
      await _prepareEditableProject(client, controller);
      client.successfulExport = true;
      await controller.export(outputKind: 'video');
      client.contextEnvelope = {
        'context': {
          'mode': 'FOCUS',
          'domain_id': 'BMP',
          'subject_id': 'brand-one',
        },
      };
      final fresh = MediaProjectController(
        repository: CoreMediaProjectRepository(client),
        domain: 'BMP',
      );
      addTearDown(fresh.dispose);
      await tester.pumpWidget(_app(client, fresh));
      await tester.tap(find.byKey(const Key('media-open-saved')));
      await tester.pumpAndSettle();
      expect(
        find.byKey(const Key('media-saved-project-ART-version')),
        findsOneWidget,
      );
      client.contextEnvelope = {
        'context': {
          'mode': 'FOCUS',
          'domain_id': 'BMP',
          'subject_id': 'brand-two',
        },
      };
      await tester.pumpWidget(_app(client, fresh));
      await tester.pumpAndSettle();
      expect(
        find.byKey(const Key('media-saved-project-ART-version')),
        findsNothing,
      );
      expect(find.byKey(const Key('media-saved-refresh')), findsOneWidget);
      expect(client.reopenCalls, 0);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'open saved-work dialog hides rows when the shell quarantines scope',
    (tester) async {
      await _prepareEditableProject(client, controller);
      client.successfulExport = true;
      await controller.export(outputKind: 'video');
      await tester.pumpWidget(_app(client, controller));
      await tester.tap(find.byKey(const Key('media-open-saved')));
      await tester.pumpAndSettle();
      expect(
        find.byKey(const Key('media-saved-project-ART-version')),
        findsOneWidget,
      );
      await tester.pumpWidget(
        _app(client, controller, contextAvailable: false),
      );
      await tester.pumpAndSettle();
      expect(
        find.byKey(const Key('media-saved-project-ART-version')),
        findsNothing,
      );
      expect(controller.version, isNull);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'real listing contract opens a saved project without typing its ID',
    (tester) async {
      await _prepareEditableProject(client, controller);
      client.successfulExport = true;
      await controller.export(outputKind: 'video');
      final fresh = MediaProjectController(
        repository: CoreMediaProjectRepository(client),
        domain: 'BMP',
      );
      addTearDown(fresh.dispose);
      await tester.pumpWidget(_app(client, fresh));
      await tester.tap(find.byKey(const Key('media-open-saved')));
      await tester.pumpAndSettle();
      await tester.tap(
        find.byKey(const Key('media-saved-project-ART-version')),
      );
      await tester.pumpAndSettle();
      expect(client.reopenedReference, 'ART-version');
      expect(fresh.timeline!.tracks.single.clips.single.sourceOut, 8);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('listing failure is distinct from empty and can retry in place', (
    tester,
  ) async {
    client.listingFailure = 'CONTENT_PROJECT_LIST_UNAVAILABLE';
    await tester.pumpWidget(_app(client, controller));
    await tester.tap(find.byKey(const Key('media-open-saved')));
    await tester.pumpAndSettle();
    expect(find.text('作品列表暂时无法读取，请重试。'), findsOneWidget);
    expect(find.text('当前范围还没有已保存的作品。'), findsNothing);
    client.listingFailure = null;
    await tester.tap(find.byKey(const Key('media-saved-refresh')));
    await tester.pumpAndSettle();
    expect(find.text('当前范围还没有已保存的作品。'), findsOneWidget);
    expect(find.text('作品列表暂时无法读取，请重试。'), findsNothing);
    expect(find.byKey(const Key('media-saved-reference')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'saved reference reopens into a fresh editor without page history',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 1100));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await _prepareEditableProject(client, controller);
      client.successfulExport = true;
      await controller.export(outputKind: 'video');
      final fresh = MediaProjectController(
        repository: CoreMediaProjectRepository(client),
        domain: 'BMP',
      );
      addTearDown(fresh.dispose);
      await tester.pumpWidget(_app(client, fresh));
      expect(find.byKey(const Key('media-reopen-ART-version')), findsNothing);
      await tester.tap(find.byKey(const Key('media-open-saved')));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const Key('media-saved-reference')),
        '  ART-version  ',
      );
      await tester.tap(find.byKey(const Key('media-confirm-open-saved')));
      await tester.pumpAndSettle();
      expect(client.reopenedReference, 'ART-version');
      expect(fresh.version?.artifactId, 'ART-version');
      expect(fresh.timeline!.tracks.single.clips.single.sourceOut, 8);
      expect(fresh.hasUnsavedChanges, isFalse);
      await _openActionsForTarget(
        tester,
        find.byKey(const Key('media-output-reference')),
      );
      expect(find.byKey(const Key('media-output-reference')), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('invalid reference stays editable and performs no request', (
    tester,
  ) async {
    await tester.pumpWidget(_app(client, controller));
    await tester.tap(find.byKey(const Key('media-open-saved')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('media-saved-reference')),
      'ART-../private',
    );
    await tester.tap(find.byKey(const Key('media-confirm-open-saved')));
    await tester.pumpAndSettle();
    expect(find.text('请填写有效的作品编号。'), findsOneWidget);
    expect(client.reopenCalls, 0);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'failed reference leaves inspector text and edited timeline intact',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 1100));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await _prepareEditableProject(client, controller);
      final original = controller.timeline;
      client.reopenFailure = 'CONTENT_PROJECT_CONTEXT_MISMATCH';
      await tester.pumpWidget(_app(client, controller));
      await tester.pumpAndSettle();
      final endField = find.byWidgetPredicate(
        (w) => w is TextField && w.decoration?.labelText == '素材终点（秒）',
      );
      await tester.enterText(endField, '6.5');
      await tester.tap(find.byKey(const Key('media-open-saved')));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const Key('media-saved-reference')),
        'ART-unavailable',
      );
      await tester.tap(find.byKey(const Key('media-confirm-open-saved')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('放弃修改'));
      await tester.pumpAndSettle();
      expect(controller.timeline, same(original));
      expect(controller.hasUnsavedChanges, isTrue);
      expect(tester.widget<TextField>(endField).controller!.text, '6.5');
      expect(controller.version, isNull);
      expect(client.reopenCalls, 1);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'reference dialog is usable at 320 pixels and 200 percent in all locales',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(320, 720));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      for (final locale in LumenisLocalizations.supportedLocales) {
        await tester.pumpWidget(const SizedBox.shrink());
        await tester.pumpWidget(
          _app(client, controller, locale: locale, scale: 2),
        );
        await tester.ensureVisible(find.byKey(const Key('media-open-saved')));
        await tester.tap(find.byKey(const Key('media-open-saved')));
        await tester.pumpAndSettle();
        await tester.enterText(
          find.byKey(const Key('media-saved-reference')),
          'ART',
        );
        final button = find.byKey(const Key('media-confirm-open-saved'));
        await tester.ensureVisible(button);
        expect(tester.getSize(button).height, greaterThanOrEqualTo(48));
        await tester.tap(button);
        await tester.pumpAndSettle();
        expect(client.reopenCalls, 0);
        expect(tester.takeException(), isNull);
      }
    },
  );

  testWidgets(
    'GLOBAL_ALL independent choice imports without a business domain',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 1000));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      client.contextEnvelope = {
        'contract': 'lumenis.context.v1',
        'selection_only': true,
        'context': {'mode': 'GLOBAL_ALL', 'subject_id': null},
      };
      await tester.pumpWidget(_app(client, null));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('media-workspace-shared')), findsOneWidget);
      expect(client.importCalls, 0);
      await tester.tap(find.byKey(const Key('media-workspace-shared')));
      await tester.pumpAndSettle();
      expect(find.text('独立作品'), findsOneWidget);
      await tester.tap(find.byKey(const Key('media-import')));
      await tester.pumpAndSettle();
      expect(client.importCalls, 1);
      expect(client.lastImportDomain, isNull);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'GLOBAL_ALL offers independent creation alongside business purposes',
    (tester) async {
      client.contextEnvelope = {
        'contract': 'lumenis.context.v1',
        'selection_only': true,
        'context': {'mode': 'GLOBAL_ALL', 'subject_id': null},
      };
      await tester.pumpWidget(_app(client, null));
      await tester.pumpAndSettle();
      expect(find.text('选择独立作品，或将本次剪辑关联到商业运营、品牌市场。'), findsOneWidget);
      expect(find.text('商业运营'), findsOneWidget);
      expect(find.text('品牌市场'), findsOneWidget);
      expect(find.byKey(const Key('media-import')), findsNothing);
      expect(client.importCalls, 0);
      await tester.tap(find.byKey(const Key('media-domain-cth')));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byKey(const Key('media-open-sources')));
      await tester.tap(find.byKey(const Key('media-open-sources')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('media-import')), findsOneWidget);
      await tester.tap(find.byKey(const Key('media-import')));
      await tester.pumpAndSettle();
      expect(client.lastImportDomain, 'CTH');
      expect(client.importCalls, 1);
    },
  );

  testWidgets(
    'GLOBAL purpose choices scroll at 320 pixels and 200 percent text',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(320, 720));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      for (final locale in const [
        Locale('zh', 'CN'),
        Locale('en'),
        Locale('ko'),
      ]) {
        await tester.pumpWidget(const SizedBox.shrink());
        final scopedClient = _Client()
          ..contextEnvelope = {
            'contract': 'lumenis.context.v1',
            'selection_only': true,
            'context': {'mode': 'GLOBAL_ALL', 'subject_id': null},
          };
        await tester.pumpWidget(
          _app(scopedClient, null, locale: locale, scale: 2),
        );
        await tester.pumpAndSettle();
        await tester.ensureVisible(find.byKey(const Key('media-domain-bmp')));
        await tester.tap(find.byKey(const Key('media-domain-bmp')));
        await tester.pumpAndSettle();
        await tester.ensureVisible(find.byKey(const Key('media-open-sources')));
        await tester.tap(find.byKey(const Key('media-open-sources')));
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('media-import')), findsOneWidget);
        expect(tester.takeException(), isNull);
      }
    },
  );

  testWidgets('GLOBAL_ALL CTH and BMP use only the explicit invoking domain', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    client.contextEnvelope = {
      'contract': 'lumenis.context.v1',
      'selection_only': true,
      'context': {'mode': 'GLOBAL_ALL', 'subject_id': null},
    };
    for (final domain in ['CTH', 'BMP']) {
      final candidate = MediaProjectController(
        repository: CoreMediaProjectRepository(client),
        domain: domain,
      );
      await tester.pumpWidget(_app(client, candidate, invokingDomain: domain));
      expect(find.byKey(const Key('media-import')), findsOneWidget);
      await tester.tap(find.byKey(const Key('media-import')));
      await tester.pumpAndSettle();
      expect(client.lastImportDomain, domain);
      await tester.pumpWidget(const SizedBox.shrink());
      candidate.dispose();
    }
  });

  Future<void> openSharedApproval(WidgetTester tester) async {
    await tester.binding.setSurfaceSize(const Size(1200, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    controller.dispose();
    controller = MediaProjectController(
      repository: CoreMediaProjectRepository(client),
      domain: null,
    );
    client.approvalRequired = true;
    await tester.pumpWidget(_app(client, controller, sharedWorkspace: true));
    await tester.tap(find.byKey(const Key('media-import')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
  }

  for (final withBusinessFocus in [false, true]) {
    testWidgets(
      'independent source approval works with business focus $withBusinessFocus',
      (tester) async {
        client.contextEnvelope = withBusinessFocus
            ? {
                'contract': 'lumenis.context.v1',
                'selection_only': true,
                'context': {
                  'mode': 'FOCUS',
                  'domain_id': 'BMP',
                  'subject_id': 'SUBJECT-not-shared',
                  'display_name': {'zh': '不应出现在独立确认中'},
                },
              }
            : null;
        await openSharedApproval(tester);
        expect(find.byType(AlertDialog), findsOneWidget);
        expect(find.text('本次用途：独立视频或音频制作。'), findsOneWidget);
        expect(find.text('当前范围：独立作品'), findsOneWidget);
        expect(find.textContaining('不会公开发布'), findsOneWidget);
        expect(find.textContaining('品牌市场'), findsNothing);
        expect(find.textContaining('不应出现在独立确认中'), findsNothing);
        await tester.tap(
          find.byKey(const Key('media-import-technical-details')),
        );
        await tester.pump(const Duration(milliseconds: 300));
        expect(find.textContaining('SUBJECT-not-shared'), findsNothing);
        expect(
          find.textContaining('content-source-import:shared-workspace:v1:'),
          findsOneWidget,
        );
        expect(client.confirmationCalls, 0);
        expect(client.importCalls, 1);
        await tester.tap(find.text('确认并导入所选文件'));
        await tester.pumpAndSettle();
        expect(client.confirmationCalls, 1);
        expect(client.confirmedImport, isTrue);
        expect(client.importCalls, 2);
        expect(client.lastImportDomain, isNull);
        expect(client.importedBytes[0], client.importedBytes[1]);
        expect(controller.sourceRefs, ['ART-source']);
        expect(controller.failureCode, isNull);
      },
    );
  }

  testWidgets('independent source approval cancellation never retries', (
    tester,
  ) async {
    await openSharedApproval(tester);
    expect(find.byType(AlertDialog), findsOneWidget);
    await tester.tap(find.text('取消'));
    await tester.pumpAndSettle();
    expect(client.confirmationCalls, 1);
    expect(client.confirmedImport, isFalse);
    expect(client.lastImportDomain, isNull);
    expect(client.importCalls, 1);
    expect(controller.sourceRefs, isEmpty);
    expect(controller.failureCode, 'CONTENT_IMPORT_CANCELLED');
  });

  testWidgets('independent approval rejects a business resource', (
    tester,
  ) async {
    client.confirmationResource = 'content-source-import:v1:${'b' * 64}';
    await openSharedApproval(tester);
    await tester.pumpAndSettle();
    expect(find.byType(AlertDialog), findsNothing);
    expect(client.confirmationCalls, 0);
    expect(client.importCalls, 1);
    expect(controller.sourceRefs, isEmpty);
    expect(controller.failureCode, 'CONTENT_APPROVAL_PENDING');
  });

  testWidgets('expired independent approval never authorizes a retry', (
    tester,
  ) async {
    client.confirmationLifetime = const Duration(seconds: -1);
    await openSharedApproval(tester);
    await tester.tap(find.text('确认并导入所选文件'));
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.textContaining('确认已过期'), findsOneWidget);
    expect(client.confirmationCalls, 0);
    expect(client.importCalls, 1);
    await tester.tap(find.text('取消'));
    await tester.pumpAndSettle();
    expect(client.confirmationCalls, 1);
    expect(client.confirmedImport, isFalse);
    expect(client.importCalls, 1);
    expect(controller.sourceRefs, isEmpty);
  });

  for (final availabilityOnly in [false, true]) {
    testWidgets(
      'independent approval blocks changed scope, availability only $availabilityOnly',
      (tester) async {
        await openSharedApproval(tester);
        if (availabilityOnly) {
          await tester.pumpWidget(
            _app(
              client,
              controller,
              sharedWorkspace: true,
              contextAvailable: false,
            ),
          );
        } else {
          client.contextEnvelope = {
            'context': {'mode': 'GLOBAL_ALL'},
          };
        }
        await tester.tap(find.text('确认并导入所选文件'));
        await tester.pump(const Duration(milliseconds: 300));
        expect(find.byType(AlertDialog), findsOneWidget);
        expect(
          find.descendant(
            of: find.byType(AlertDialog),
            matching: find.textContaining('查看范围已改变'),
          ),
          findsOneWidget,
        );
        expect(client.confirmationCalls, 0);
        expect(client.importCalls, 1);
        await tester.tap(find.text('取消'));
        await tester.pumpAndSettle();
        expect(client.confirmationCalls, 0);
        expect(client.importCalls, 1);
        expect(controller.sourceRefs, isEmpty);
        expect(controller.failureCode, 'CONTENT_CONTEXT_CHANGED');
      },
    );

    testWidgets(
      'independent approval ignores late response, availability only $availabilityOnly',
      (tester) async {
        client.pendingConfirmation = Completer<void>();
        await openSharedApproval(tester);
        await tester.tap(find.text('确认并导入所选文件'));
        await tester.pump(const Duration(milliseconds: 400));
        expect(client.confirmationCalls, 1);
        expect(client.confirmedImport, isTrue);
        expect(client.importCalls, 1);
        if (availabilityOnly) {
          await tester.pumpWidget(
            _app(
              client,
              controller,
              sharedWorkspace: true,
              contextAvailable: false,
            ),
          );
        } else {
          client.contextEnvelope = {
            'context': {'mode': 'GLOBAL_ALL'},
          };
        }
        client.pendingConfirmation!.complete();
        await tester.pumpAndSettle();
        expect(client.confirmationCalls, 1);
        expect(client.importCalls, 1);
        expect(client.lastImportDomain, isNull);
        expect(controller.sourceRefs, isEmpty);
        expect(controller.timeline, isNull);
        expect(controller.failureCode, 'CONTENT_CONTEXT_CHANGED');
      },
    );
  }

  testWidgets(
    'source import requires the user confirmation and retries same bytes',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1200, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      client.approvalRequired = true;
      client.contextEnvelope = {
        'contract': 'lumenis.context.v1',
        'selection_only': true,
        'context': {
          'mode': 'FOCUS',
          'domain_id': 'BMP',
          'subject_id': 'SUBJECT-7f23',
          'display_name': {
            'zh': '广州太古汇',
            'en': 'Taikoo Hui Guangzhou',
            'ko': '광저우 타이쿠후이',
          },
        },
      };
      await tester.pumpWidget(_app(client, controller));
      await tester.tap(find.byKey(const Key('media-import')));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));
      expect(find.textContaining('不会公开发布'), findsOneWidget);
      expect(find.textContaining('interview.mp4'), findsOneWidget);
      expect(find.textContaining('本次用途：品牌市场内容制作'), findsOneWidget);
      expect(find.textContaining('品牌市场 · 广州太古汇 · 所选主体范围'), findsOneWidget);
      expect(find.textContaining('SUBJECT-7f23'), findsNothing);
      expect(find.text('d' * 64), findsNothing);
      expect(find.textContaining('确认有效期至'), findsNothing);
      await tester.tap(find.byKey(const Key('media-import-technical-details')));
      await tester.pump(const Duration(milliseconds: 300));
      expect(find.text('d' * 64), findsOneWidget);
      expect(find.textContaining('确认有效期至'), findsOneWidget);
      expect(find.textContaining('确认编号: CONF-widget'), findsOneWidget);
      expect(find.textContaining('主体 ID: SUBJECT-7f23'), findsOneWidget);
      expect(client.importCalls, 1);
      expect(client.confirmationCalls, 0);
      await tester.tap(find.text('确认并导入所选文件'));
      await tester.pumpAndSettle();
      expect(client.confirmationCalls, 1);
      expect(client.confirmedImport, isTrue);
      expect(client.importCalls, 2);
      expect(client.importedBytes[0], client.importedBytes[1]);
      expect(controller.sourceRefs, ['ART-source']);
    },
  );

  testWidgets('canceling source confirmation keeps the source unimported', (
    tester,
  ) async {
    client.approvalRequired = true;
    client.contextEnvelope = {
      'contract': 'lumenis.context.v1',
      'selection_only': true,
      'context': {
        'mode': 'FOCUS',
        'domain_id': 'BMP',
        'subject_id': 'SUBJECT-cancel',
      },
    };
    await tester.pumpWidget(_app(client, controller));
    await tester.ensureVisible(find.byKey(const Key('media-open-sources')));
    await tester.tap(find.byKey(const Key('media-open-sources')));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const Key('media-import')));
    await tester.tap(find.byKey(const Key('media-import')));
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.byType(AlertDialog), findsOneWidget);
    await tester.tap(find.text('取消'));
    await tester.pumpAndSettle();
    expect(client.confirmationCalls, 1);
    expect(client.confirmedImport, isFalse);
    expect(client.importCalls, 1);
    expect(controller.sourceRefs, isEmpty);
    expect(find.textContaining('已取消导入'), findsOneWidget);
  });

  testWidgets('expired confirmation cannot authorize an import', (
    tester,
  ) async {
    client.approvalRequired = true;
    client.confirmationLifetime = const Duration(seconds: -1);
    client.contextEnvelope = {
      'contract': 'lumenis.context.v1',
      'selection_only': true,
      'context': {
        'mode': 'FOCUS',
        'domain_id': 'BMP',
        'subject_id': 'SUBJECT-expired',
      },
    };
    await tester.pumpWidget(_app(client, controller));
    await tester.ensureVisible(find.byKey(const Key('media-open-sources')));
    await tester.tap(find.byKey(const Key('media-open-sources')));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const Key('media-import')));
    await tester.tap(find.byKey(const Key('media-import')));
    await tester.pump(const Duration(milliseconds: 400));
    await tester.tap(find.text('确认并导入所选文件'));
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.textContaining('确认已过期'), findsOneWidget);
    expect(client.confirmationCalls, 0);
    expect(client.importCalls, 1);
    expect(controller.sourceRefs, isEmpty);
    await tester.tap(find.text('取消'));
    await tester.pumpAndSettle();
    expect(client.confirmedImport, isFalse);
    expect(controller.sourceRefs, isEmpty);
  });

  testWidgets('server confirmation filename mismatch is rejected', (
    tester,
  ) async {
    client.approvalRequired = true;
    client.confirmationFilename = 'different.mp4';
    client.contextEnvelope = {
      'contract': 'lumenis.context.v1',
      'selection_only': true,
      'context': {
        'mode': 'FOCUS',
        'domain_id': 'BMP',
        'subject_id': 'SUBJECT-mismatch',
      },
    };
    await tester.pumpWidget(_app(client, controller));
    await tester.ensureVisible(find.byKey(const Key('media-open-sources')));
    await tester.tap(find.byKey(const Key('media-open-sources')));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const Key('media-import')));
    await tester.tap(find.byKey(const Key('media-import')));
    await tester.pumpAndSettle();
    expect(find.byType(AlertDialog), findsNothing);
    expect(client.confirmationCalls, 0);
    expect(client.importCalls, 1);
    expect(controller.sourceRefs, isEmpty);
    expect(find.textContaining('素材导入需要审核批准'), findsOneWidget);
  });

  testWidgets('context change while confirmation is open is rejected', (
    tester,
  ) async {
    client.approvalRequired = true;
    client.contextEnvelope = {
      'contract': 'lumenis.context.v1',
      'selection_only': true,
      'context': {
        'mode': 'FOCUS',
        'domain_id': 'BMP',
        'subject_id': 'SUBJECT-before',
      },
    };
    await tester.pumpWidget(_app(client, controller));
    await tester.ensureVisible(find.byKey(const Key('media-open-sources')));
    await tester.tap(find.byKey(const Key('media-open-sources')));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const Key('media-import')));
    await tester.tap(find.byKey(const Key('media-import')));
    await tester.pump(const Duration(milliseconds: 400));
    client.contextEnvelope = {
      'contract': 'lumenis.context.v1',
      'selection_only': true,
      'context': {
        'mode': 'FOCUS',
        'domain_id': 'BMP',
        'subject_id': 'SUBJECT-after',
      },
    };
    await tester.tap(find.text('确认并导入所选文件'));
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.textContaining('查看范围已改变'), findsOneWidget);
    expect(client.confirmationCalls, 0);
    expect(client.importCalls, 1);
    expect(controller.sourceRefs, isEmpty);
    await tester.tap(find.text('取消'));
    await tester.pumpAndSettle();
    expect(client.confirmationCalls, 0);
    expect(controller.sourceRefs, isEmpty);
  });

  testWidgets(
    'picked bytes create a source; add, edit, undo and failed export preserve draft',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 1100));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(_app(client, controller));
      await tester.tap(find.byKey(const Key('media-import')));
      await tester.pumpAndSettle();
      expect(client.imports, 1);
      expect(controller.timeline!.tracks.single.clips, isEmpty);
      await tester.tap(find.byTooltip('添加片段 · interview.mp4'));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, '添加片段'));
      await tester.pumpAndSettle();
      expect(controller.timeline!.tracks.single.clips.single.sourceOut, 20);
      final endField = find.byWidgetPredicate(
        (w) => w is TextField && w.decoration?.labelText == '素材终点（秒）',
      );
      await tester.enterText(endField, '8');
      await tester.ensureVisible(find.text('应用调整'));
      await tester.tap(find.text('应用调整'));
      await tester.pumpAndSettle();
      expect(controller.timeline!.tracks.single.clips.single.sourceOut, 8);
      final toolbarUndo = find.byKey(const Key('media-toolbar-undo'));
      await tester.ensureVisible(toolbarUndo);
      expect(tester.widget<IconButton>(toolbarUndo).tooltip, '撤销');
      await tester.tap(toolbarUndo);
      await tester.pumpAndSettle();
      expect(controller.timeline!.tracks.single.clips.single.sourceOut, 20);
      final exportButton = find.byKey(const Key('media-export'));
      await _openActionsForTarget(tester, exportButton);
      await tester.ensureVisible(exportButton);
      await tester.tap(exportButton);
      await tester.pumpAndSettle();
      expect(client.exports, 1);
      expect(client.exportedRefs, ['ART-source']);
      expect(controller.timeline!.tracks.single.clips.single.sourceOut, 20);
      expect(controller.version, isNull);
      expect(find.textContaining('private decoder'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'layers return to the same clip, edit draft and timeline position',
    (tester) async {
      await controller.importFile('interview.mp4', Uint8List.fromList([1]));
      controller.edit(
        (s) =>
            s.addClip(s.assets.single.assetId, trackId: 'video', sourceOut: 8),
      );
      controller.selectClip(
        controller.timeline!.tracks.single.clips.single.clipId,
      );
      await tester.binding.setSurfaceSize(const Size(1440, 1100));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(_app(client, controller));
      await tester.pumpAndSettle();
      final desktopField = find.byWidgetPredicate(
        (w) => w is TextField && w.decoration?.labelText == '素材终点（秒）',
      );
      await tester.enterText(desktopField, '6.25');
      tester.testTextInput.hide();
      await tester.pumpAndSettle();
      await tester.binding.setSurfaceSize(const Size(390, 844));
      await tester.pumpAndSettle();

      final timelineScroll = find.byKey(const Key('media-timeline-scroll'));
      await tester.drag(timelineScroll, const Offset(-220, 0));
      await tester.pumpAndSettle();
      final scrollController = tester
          .widget<SingleChildScrollView>(timelineScroll)
          .controller!;
      final preservedOffset = scrollController.offset;
      expect(preservedOffset, greaterThan(0));
      final selectedClipId = controller.selectedClipId;
      expect(selectedClipId, isNotNull);

      await tester.ensureVisible(find.byKey(const Key('media-open-sources')));
      await tester.tap(find.byKey(const Key('media-open-sources')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('media-import')), findsOneWidget);
      await tester.tap(find.byKey(const Key('media-close-layer')));
      await tester.pumpAndSettle();
      expect(scrollController.offset, preservedOffset);

      await tester.ensureVisible(
        find.byKey(const Key('media-open-properties')),
      );
      await tester.tap(find.byKey(const Key('media-open-properties')));
      await tester.pumpAndSettle();
      final sheetField = find.byWidgetPredicate(
        (w) => w is TextField && w.decoration?.labelText == '素材终点（秒）',
      );
      expect(tester.widget<TextField>(sheetField).controller!.text, '6.25');
      await tester.tap(find.byKey(const Key('media-close-layer')));
      await tester.pumpAndSettle();
      await tester.ensureVisible(
        find.byKey(const Key('media-open-properties')),
      );
      await tester.tap(find.byKey(const Key('media-open-properties')));
      await tester.pumpAndSettle();
      expect(tester.widget<TextField>(sheetField).controller!.text, '6.25');
      await tester.ensureVisible(find.text('应用调整'));
      await tester.tap(find.text('应用调整'));
      await tester.pumpAndSettle();
      expect(controller.selectedClipId, selectedClipId);
      expect(scrollController.offset, preservedOffset);
      expect(controller.timeline!.tracks.single.clips.single.sourceOut, 6.25);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('open layers refresh for edits, undo and busy state', (
    tester,
  ) async {
    await controller.importFile('interview.mp4', Uint8List.fromList([1]));
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(_app(client, controller));
    await tester.ensureVisible(find.byKey(const Key('media-open-sources')));
    await tester.tap(find.byKey(const Key('media-open-sources')));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('添加片段 · interview.mp4'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, '添加片段'));
    await tester.pumpAndSettle();
    expect(controller.timeline!.tracks.single.clips, hasLength(1));
    expect(controller.selectedClipId, isNotNull);
    expect(find.byKey(const Key('media-close-layer')), findsOneWidget);
    await tester.tap(find.byKey(const Key('media-close-layer')));
    await tester.pumpAndSettle();

    await _openActionsForTarget(tester, find.byKey(const Key('media-export')));
    expect(find.text('版权状态尚未核实；导出不代表获准发布。'), findsOneWidget);
    expect(find.byKey(const Key('media-rights-unknown')), findsOneWidget);
    expect(find.byType(CheckboxListTile), findsNothing);
    client.pendingExport = Completer<void>();
    await tester.tap(find.byKey(const Key('media-export')));
    await tester.pump();
    expect(controller.busy, isTrue);
    expect(
      tester
          .widget<FilledButton>(find.byKey(const Key('media-export')))
          .onPressed,
      isNull,
    );
    client.pendingExport!.complete();
    await tester.pumpAndSettle();
    expect(controller.busy, isFalse);
    await tester.tap(find.text('撤销'));
    await tester.pumpAndSettle();
    expect(controller.timeline!.tracks.single.clips, isEmpty);
    expect(
      tester
          .widget<OutlinedButton>(find.widgetWithText(OutlinedButton, '撤销'))
          .onPressed,
      isNull,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('audio creation entry exports as an audio project', (
    tester,
  ) async {
    client.successfulExport = true;
    await prepareAudioProject();
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      _app(client, controller, initialOutputKind: 'audio'),
    );
    await tester.pumpAndSettle();

    final workbench = tester.widget<MediaProjectWorkbench>(
      find.byType(MediaProjectWorkbench),
    );
    expect(workbench.initialOutputKind, 'audio');
    await _openActionsForTarget(tester, find.byKey(const Key('media-export')));
    await tester.tap(find.byKey(const Key('media-export')));
    await tester.pumpAndSettle();

    expect(client.exportedOutputKind, 'audio');
    expect(controller.version?.outputKind, 'audio');
    expect(
      ((client.savedExport!['result'] as Map)['project'] as Map)['output_kind'],
      'audio',
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('reopened audio project keeps its kind on a later export', (
    tester,
  ) async {
    client.successfulExport = true;
    await prepareAudioProject();
    await controller.export(outputKind: 'audio');
    await controller.reopen('ART-version');
    expect(controller.version?.outputKind, 'audio');
    controller.edit(
      (snapshot) => snapshot.addAudioTrack('bgm', audioRole: 'bgm'),
    );

    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(_app(client, controller));
    await tester.pumpAndSettle();
    await _openActionsForTarget(tester, find.byKey(const Key('media-export')));
    await tester.tap(find.byKey(const Key('media-export')));
    await tester.pumpAndSettle();

    expect(client.exportedOutputKind, 'audio');
    expect(controller.version?.outputKind, 'audio');
    expect(tester.takeException(), isNull);
  });

  testWidgets('open actions hide cached versions after context quarantine', (
    tester,
  ) async {
    client.contextEnvelope = {
      'contract': 'lumenis.context.v1',
      'selection_only': true,
      'context': {
        'mode': 'FOCUS',
        'domain_id': 'BMP',
        'subject_id': 'SUBJECT-before',
      },
    };
    client.successfulExport = true;
    await controller.importFile('interview.mp4', Uint8List.fromList([1]));
    controller.edit(
      (s) => s.addClip(s.assets.single.assetId, trackId: 'video', sourceOut: 8),
    );
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(_app(client, controller));
    await _openActionsForTarget(tester, find.byKey(const Key('media-export')));
    expect(find.byKey(const Key('media-rights-unknown')), findsOneWidget);
    expect(find.byType(CheckboxListTile), findsNothing);
    await tester.tap(find.byKey(const Key('media-export')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('media-reopen-ART-version')), findsOneWidget);
    expect(find.byKey(const Key('media-version-preview')), findsOneWidget);
    expect(find.byKey(const Key('media-version-download')), findsOneWidget);

    controller.edit(
      (s) => s.addClip(s.assets.single.assetId, trackId: 'video', sourceOut: 5),
    );
    expect(controller.hasUnsavedChanges, isTrue);
    client.contextEnvelope = {
      'contract': 'lumenis.context.v1',
      'selection_only': true,
      'context': {
        'mode': 'FOCUS',
        'domain_id': 'BMP',
        'subject_id': 'SUBJECT-after',
      },
    };
    controller.edit((s) => s.undo());
    await tester.pumpAndSettle();

    expect(controller.contextMatches, isFalse);
    expect(controller.hasUnsavedChanges, isTrue);
    expect(find.byKey(const Key('media-reopen-ART-version')), findsNothing);
    expect(find.byKey(const Key('media-version-preview')), findsNothing);
    expect(find.byKey(const Key('media-version-download')), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('property sheet keeps apply reachable above the keyboard', (
    tester,
  ) async {
    await controller.importFile('interview.mp4', Uint8List.fromList([1]));
    controller.edit(
      (s) => s.addClip(s.assets.single.assetId, trackId: 'video', sourceOut: 8),
    );
    controller.selectClip(
      controller.timeline!.tracks.single.clips.single.clipId,
    );
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      _app(
        client,
        controller,
        scale: 2,
        viewInsets: const EdgeInsets.only(bottom: 320),
      ),
    );
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const Key('media-open-properties')));
    await tester.tap(find.byKey(const Key('media-open-properties')));
    await tester.pumpAndSettle();
    final endField = find.byWidgetPredicate(
      (widget) =>
          widget is TextField && widget.decoration?.labelText == '素材终点（秒）',
    );
    await tester.ensureVisible(endField);
    await tester.enterText(endField, '6.5');
    await tester.ensureVisible(find.text('应用调整'));
    expect(
      tester.getSize(find.widgetWithText(FilledButton, '应用调整')).height,
      greaterThanOrEqualTo(48),
    );
    await tester.tap(find.text('应用调整'));
    await tester.pumpAndSettle();
    expect(controller.timeline!.tracks.single.clips.single.sourceOut, 6.5);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'unapplied clip range blocks split and keeps the entered fields',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await controller.importFile('interview.mp4', Uint8List.fromList([1]));
      controller.edit(
        (snapshot) => snapshot.addClip(
          snapshot.assets.single.assetId,
          trackId: 'video',
          sourceOut: 8,
        ),
      );
      controller.selectClip(
        controller.timeline!.tracks.single.clips.single.clipId,
      );
      await tester.pumpWidget(_app(client, controller));
      await tester.pumpAndSettle();

      final endField = find.byWidgetPredicate(
        (widget) =>
            widget is TextField && widget.decoration?.labelText == '素材终点（秒）',
      );
      await _openPropertiesForField(tester, endField);
      await tester.enterText(endField, '6.5');
      await tester.pump();

      final splitButton = find.byKey(const Key('media-split-clip'));
      await _expandClipOperationsForTarget(tester, splitButton);
      final splitPosition = find.byWidgetPredicate(
        (widget) =>
            widget is TextField && widget.decoration?.labelText == '分割位置（素材秒）',
      );
      await tester.enterText(splitPosition, '4.5');
      await tester.pump();

      expect(tester.widget<OutlinedButton>(splitButton).onPressed, isNull);
      expect(find.byKey(const Key('media-apply-before-split')), findsOneWidget);
      expect(tester.widget<TextField>(endField).controller!.text, '6.5');
      expect(tester.widget<TextField>(splitPosition).controller!.text, '4.5');
      expect(controller.timeline!.tracks.single.clips, hasLength(1));
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'split-position-only edit exports cleanly and does not leave a stale guard',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await controller.importFile('interview.mp4', Uint8List.fromList([1]));
      controller.edit(
        (snapshot) => snapshot.addClip(
          snapshot.assets.single.assetId,
          trackId: 'video',
          sourceOut: 8,
        ),
      );
      controller.selectClip(
        controller.timeline!.tracks.single.clips.single.clipId,
      );
      client.successfulExport = true;
      final guard = LumenisLeaveGuard();
      await tester.pumpWidget(_app(client, controller, guard: guard));
      await tester.pumpAndSettle();

      final splitButton = find.byKey(const Key('media-split-clip'));
      await _expandClipOperationsForTarget(tester, splitButton);
      final splitPosition = find.byWidgetPredicate(
        (widget) =>
            widget is TextField && widget.decoration?.labelText == '分割位置（素材秒）',
      );
      await tester.enterText(splitPosition, '5.5');
      await tester.pump();
      expect(tester.widget<OutlinedButton>(splitButton).onPressed, isNotNull);

      await tester.ensureVisible(splitButton);
      await tester.tap(splitButton);
      await tester.pumpAndSettle();
      expect(controller.timeline!.tracks.single.clips, hasLength(2));
      expect(controller.hasUnsavedChanges, isTrue);
      expect(guard.needsProtection, isTrue);

      await controller.export(outputKind: 'video');
      await tester.pumpAndSettle();
      expect(controller.version?.artifactId, 'ART-version');
      expect(client.exports, 1);
      expect(controller.hasUnsavedChanges, isFalse);
      expect(guard.needsProtection, isFalse);
      expect(await guard.requestLeave(), isTrue);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'editor Back shares the leave decision and keeps unapplied inspector text on cancel',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 1100));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await _prepareEditableProject(client, controller);
      client.successfulExport = true;
      final guard = LumenisLeaveGuard();
      var backCalls = 0;

      await tester.pumpWidget(
        _app(client, controller, guard: guard, onBack: () => backCalls++),
      );
      await tester.pumpAndSettle();
      await controller.export(outputKind: 'video');
      await tester.pumpAndSettle();
      expect(controller.hasUnsavedChanges, isFalse);

      final endField = find.byWidgetPredicate(
        (widget) =>
            widget is TextField && widget.decoration?.labelText == '素材终点（秒）',
      );
      await tester.enterText(endField, '6.5');
      await tester.pump();
      expect(guard.needsProtection, isTrue);
      expect(controller.hasUnsavedChanges, isFalse);

      await tester.tap(
        find.widgetWithIcon(IconButton, Icons.arrow_back_rounded),
      );
      await tester.pumpAndSettle();
      expect(find.text('放弃未导出的修改？'), findsOneWidget);
      await tester.tap(find.text('取消'));
      await tester.pumpAndSettle();

      expect(backCalls, 0);
      expect(tester.widget<TextField>(endField).controller!.text, '6.5');
      expect(controller.timeline!.tracks.single.clips.single.sourceOut, 8);
      expect(guard.needsProtection, isTrue);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('reopen cancel preserves unapplied inspector text and version', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1100));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await _prepareEditableProject(client, controller);
    client.successfulExport = true;
    final guard = LumenisLeaveGuard();

    await tester.pumpWidget(_app(client, controller, guard: guard));
    await tester.pumpAndSettle();
    await controller.export(outputKind: 'video');
    await tester.pumpAndSettle();
    expect(controller.version?.artifactId, 'ART-version');
    expect(controller.hasUnsavedChanges, isFalse);

    final endField = find.byWidgetPredicate(
      (widget) =>
          widget is TextField && widget.decoration?.labelText == '素材终点（秒）',
    );
    await tester.enterText(endField, '6.5');
    await tester.pump();
    final reopen = find.byKey(const Key('media-reopen-ART-version'));
    await _openActionsForTarget(tester, reopen);
    await tester.ensureVisible(reopen);
    await tester.tap(reopen);
    await tester.pumpAndSettle();
    expect(find.text('放弃未导出的修改？'), findsOneWidget);
    await tester.tap(find.text('取消'));
    await tester.pumpAndSettle();

    expect(controller.version?.artifactId, 'ART-version');
    expect(controller.timeline!.tracks.single.clips.single.sourceOut, 8);
    expect(tester.widget<TextField>(endField).controller!.text, '6.5');
    expect(guard.needsProtection, isTrue);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'unavailable context quarantines cached output until sources are confirmed again',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 1100));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await _prepareEditableProject(client, controller);
      client.successfulExport = true;
      final guard = LumenisLeaveGuard();

      await tester.pumpWidget(_app(client, controller, guard: guard));
      await tester.pumpAndSettle();
      await controller.export(outputKind: 'video');
      await tester.pumpAndSettle();
      final endField = find.byWidgetPredicate(
        (widget) =>
            widget is TextField && widget.decoration?.labelText == '素材终点（秒）',
      );
      await tester.enterText(endField, '6.5');
      await tester.pump();
      expect(guard.needsProtection, isTrue);

      await tester.pumpWidget(
        _app(client, controller, guard: guard, contextAvailable: false),
      );
      await tester.pumpAndSettle();
      expect(controller.sourcesNeedRevalidation, isTrue);
      expect(client.inspectCalls, 0);
      expect(find.byKey(const Key('media-reopen-ART-version')), findsNothing);
      expect(find.byKey(const Key('media-timeline-scroll')), findsNothing);
      await _openActionsForTarget(
        tester,
        find.byKey(const Key('media-export')),
      );
      expect(
        tester
            .widget<FilledButton>(find.byKey(const Key('media-export')))
            .onPressed,
        isNull,
      );
      expect(guard.needsProtection, isTrue);

      final leave = guard.requestLeave();
      await tester.pumpAndSettle();
      expect(find.text('放弃未导出的修改？'), findsOneWidget);
      await tester.tap(find.text('取消'));
      await tester.pumpAndSettle();
      expect(await leave, isFalse);
      expect(guard.needsProtection, isTrue);

      await tester.tap(find.byKey(const Key('media-close-layer')));
      await tester.pumpAndSettle();
      await tester.pumpWidget(_app(client, controller, guard: guard));
      await tester.pumpAndSettle();
      expect(controller.contextMatches, isFalse);
      expect(find.byKey(const Key('media-timeline-scroll')), findsNothing);
      expect(
        find.byKey(const Key('media-recover-draft-sources')),
        findsOneWidget,
      );
      expect(client.inspectCalls, 0);
      await tester.tap(find.byKey(const Key('media-recover-draft-sources')));
      await tester.pumpAndSettle();
      expect(client.inspectCalls, 1);
      expect(controller.contextMatches, isTrue);
      expect(controller.timeline, isNotNull);
      expect(
        find.byKey(const Key('media-recover-draft-sources')),
        findsNothing,
      );
      expect(tester.widget<TextField>(endField).controller!.text, '6.5');
      expect(guard.needsProtection, isTrue);

      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump();
      expect(guard.needsProtection, isFalse);
      expect(await guard.requestLeave(), isTrue);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('pending import blocks leaving without calling onBack', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1100));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final guard = LumenisLeaveGuard();
    client.pendingImport = Completer<void>();
    var backCalls = 0;
    await tester.pumpWidget(
      _app(client, controller, guard: guard, onBack: () => backCalls++),
    );
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const Key('media-import')));
    await tester.tap(find.byKey(const Key('media-import')));
    for (var attempt = 0; attempt < 6 && !controller.busy; attempt++) {
      await tester.pump();
    }
    expect(controller.busy, isTrue);
    await tester.pump();
    expect(guard.needsProtection, isTrue);
    final backButton = find.widgetWithIcon(
      IconButton,
      Icons.arrow_back_rounded,
    );
    expect(tester.widget<IconButton>(backButton).onPressed, isNull);
    await tester.tap(backButton, warnIfMissed: false);
    await tester.pump();
    expect(backCalls, 0);
    expect(await guard.requestLeave(), isFalse);
    expect(find.text('放弃未导出的修改？'), findsNothing);
    expect(backCalls, 0);

    client.pendingImport!.complete();
    await tester.pumpAndSettle();
    expect(controller.busy, isFalse);
    expect(backCalls, 0);
    expect(tester.takeException(), isNull);
  });

  testWidgets('pending export blocks leaving without calling onBack', (
    tester,
  ) async {
    await _prepareEditableProject(client, controller);
    await tester.binding.setSurfaceSize(const Size(1440, 1100));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final guard = LumenisLeaveGuard();
    var backCalls = 0;
    await tester.pumpWidget(
      _app(client, controller, guard: guard, onBack: () => backCalls++),
    );
    await tester.pumpAndSettle();
    client.pendingExport = Completer<void>();
    final export = controller.export(outputKind: 'video');
    await tester.pump();
    expect(controller.busy, isTrue);
    expect(guard.needsProtection, isTrue);
    expect(
      tester
          .widget<IconButton>(
            find.widgetWithIcon(IconButton, Icons.arrow_back_rounded),
          )
          .onPressed,
      isNull,
    );
    expect(await guard.requestLeave(), isFalse);
    expect(find.text('放弃未导出的修改？'), findsNothing);
    expect(backCalls, 0);

    client.pendingExport!.complete();
    await export;
    await tester.pumpAndSettle();
    expect(controller.busy, isFalse);
    expect(backCalls, 0);
    expect(tester.takeException(), isNull);
  });

  testWidgets('export progress stays in the active layer and follows return', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await _prepareEditableProject(client, controller);
    client.successfulExport = true;
    await tester.pumpWidget(_app(client, controller));
    await tester.pumpAndSettle();
    final exportButton = find.byKey(const Key('media-export'));
    await _openActionsForTarget(tester, exportButton);
    expect(find.byKey(const Key('media-rights-unknown')), findsOneWidget);
    expect(find.byType(CheckboxListTile), findsNothing);
    client.pendingExport = Completer<void>();
    await tester.ensureVisible(exportButton);
    await tester.tap(exportButton);
    await tester.pump();
    expect(controller.busy, isTrue);
    expect(
      find.descendant(
        of: find.byType(BottomSheet),
        matching: find.text('正在导出，草稿仍保留…'),
      ),
      findsOneWidget,
    );
    await tester.tap(find.byKey(const Key('media-close-layer')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.byType(BottomSheet), findsNothing);
    expect(find.text('正在导出，草稿仍保留…'), findsOneWidget);
    client.pendingExport!.complete();
    await tester.pumpAndSettle();
    expect(controller.busy, isFalse);
    expect(controller.version?.artifactId, 'ART-version');
    expect(find.text('正在导出，草稿仍保留…'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('pending version retrieval blocks leaving without onBack', (
    tester,
  ) async {
    await _prepareEditableProject(client, controller);
    await tester.binding.setSurfaceSize(const Size(1440, 1100));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final guard = LumenisLeaveGuard();
    var backCalls = 0;
    client.successfulExport = true;
    await tester.pumpWidget(
      _app(client, controller, guard: guard, onBack: () => backCalls++),
    );
    await tester.pumpAndSettle();
    await controller.export(outputKind: 'video');
    await tester.pumpAndSettle();

    client.pendingRetrieval = Completer<void>();
    final previewAction = find.byKey(const Key('media-version-preview'));
    await _openActionsForTarget(tester, previewAction);
    await tester.ensureVisible(previewAction);
    await tester.tap(previewAction);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.byKey(const Key('media-close-layer')), findsNothing);
    expect(guard.needsProtection, isTrue);
    expect(find.text('正在读取已保存的作品…'), findsOneWidget);
    expect(find.text('正在导入所选文件…'), findsNothing);
    expect(
      tester
          .widget<IconButton>(
            find.widgetWithIcon(IconButton, Icons.arrow_back_rounded),
          )
          .onPressed,
      isNull,
    );
    expect(await guard.requestLeave(), isFalse);
    expect(backCalls, 0);
    expect(find.text('放弃未导出的修改？'), findsNothing);

    client.pendingRetrieval!.complete();
    await tester.pumpAndSettle();
    expect(guard.needsProtection, isFalse);
    expect(backCalls, 0);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'desktop keeps the loaded preview and timeline in short and tall viewports',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 720));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await _prepareEditableProject(client, controller);
      client.successfulExport = true;
      await tester.pumpWidget(_app(client, controller));
      await tester.pumpAndSettle();
      await controller.export(outputKind: 'video');
      await tester.pumpAndSettle();

      await tester.tap(
        find.byKey(
          Key(
            'media-preview-source-${controller.timeline!.assets.single.assetId}',
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('media-source-monitor')), findsOneWidget);
      final action = find.byKey(const Key('media-version-preview'));
      await _openActionsForTarget(tester, action);
      await tester.ensureVisible(action);
      await tester.tap(action);
      await tester.pumpAndSettle();

      final preview = find.byType(MediaPreview);
      final matte = find.byKey(const Key('media-preview-matte'));
      final timeline = find.byKey(const Key('media-timeline-region'));
      expect(find.byKey(const Key('media-source-monitor')), findsNothing);
      expect(preview, findsOneWidget);
      expect(controller.version?.artifactId, 'ART-version');
      expect(client.retrievalCalls, 1);

      for (final size in const [Size(1440, 720), Size(1440, 1080)]) {
        await tester.binding.setSurfaceSize(size);
        await tester.pumpAndSettle();
        final viewport = tester.getRect(find.byType(Scaffold));
        final previewRect = tester.getRect(matte);
        final timelineRect = tester.getRect(timeline);
        expect(previewRect.width, greaterThan(0));
        expect(previewRect.height, greaterThan(0));
        expect(previewRect.top, greaterThanOrEqualTo(viewport.top));
        expect(previewRect.bottom, lessThanOrEqualTo(viewport.bottom));
        expect(timelineRect.height, greaterThan(0));
        expect(timelineRect.top, greaterThanOrEqualTo(viewport.top));
        expect(timelineRect.bottom, lessThanOrEqualTo(viewport.bottom));
        expect(timelineRect.top, greaterThan(previewRect.top));
        expect(tester.takeException(), isNull);
      }
      final playerElement = tester.element(preview);
      for (final size in const [Size(390, 844), Size(1440, 900)]) {
        await tester.binding.setSurfaceSize(size);
        await tester.pumpAndSettle();
        expect(tester.element(preview), same(playerElement));
        expect(controller.version?.artifactId, 'ART-version');
        expect(client.retrievalCalls, 1);
        expect(tester.takeException(), isNull);
      }
    },
  );

  testWidgets(
    'timeline height follows actual rows until the user chooses a size',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await _prepareEditableProject(client, controller);
      await tester.pumpWidget(_app(client, controller));
      await tester.pumpAndSettle();
      final timeline = find.byKey(const Key('media-timeline-region'));
      final preview = find.byKey(const ValueKey('media-preview-stage'));
      final singleHeight = tester.getSize(timeline).height;
      final singlePreviewHeight = tester.getSize(preview).height;
      expect(singleHeight, 180);
      final selected = controller.selectedClipId;
      controller.edit(
        (s) => s
            .addAudioTrack('voice', audioRole: 'voiceover')
            .addAudioTrack('music', audioRole: 'bgm'),
      );
      await tester.pumpAndSettle();
      final multipleHeight = tester.getSize(timeline).height;
      expect(multipleHeight, greaterThan(singleHeight));
      expect(tester.getSize(preview).height, lessThan(singlePreviewHeight));
      expect(
        find.byKey(const ValueKey('media-track-label/voice')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey('media-track-label/music')),
        findsOneWidget,
      );
      await tester.tap(find.byKey(const Key('media-timeline-larger')));
      await tester.pumpAndSettle();
      final expanded = tester.getSize(timeline).height;
      expect(expanded, greaterThan(multipleHeight));
      controller.edit((s) => s.addAudioTrack('effects', audioRole: 'sfx'));
      await tester.pumpAndSettle();
      expect(tester.getSize(timeline).height, expanded);
      expect(
        find.byKey(const ValueKey('media-track-label/effects')),
        findsOneWidget,
      );
      await tester.tap(find.byKey(const Key('media-timeline-smaller')));
      await tester.pumpAndSettle();
      expect(tester.getSize(timeline).height, lessThan(expanded));
      expect(controller.selectedClipId, selected);
      expect(controller.timeline!.tracks, hasLength(4));
      expect(controller.timeline!.tracks.first.clips.single.sourceOut, 8);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'full-width timeline scales clips together and keeps labels and edit intent stable',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await _prepareEditableProject(client, controller);
      controller.edit(
        (s) => s.addClip(
          s.assets.single.assetId,
          trackId: 'video',
          sourceIn: 8,
          sourceOut: 12,
        ),
      );
      await tester.pumpWidget(_app(client, controller));
      await tester.pumpAndSettle();
      final clips = controller.timeline!.tracks.single.clips;
      final first = find.byKey(ValueKey('media-clip-${clips[0].clipId}'));
      final second = find.byKey(ValueKey('media-clip-${clips[1].clipId}'));
      final timeline = find.byKey(const Key('media-timeline-region'));
      final labels = find.byKey(const Key('media-track-labels'));
      final sourceRail = find.byKey(const Key('media-source-rail'));
      final propertyRail = find.byKey(const Key('media-property-rail'));
      final region = tester.getRect(timeline);
      expect(region.left, lessThanOrEqualTo(tester.getRect(sourceRail).left));
      expect(
        region.right,
        greaterThanOrEqualTo(tester.getRect(propertyRail).right),
      );
      expect(
        region.top,
        greaterThanOrEqualTo(tester.getRect(sourceRail).bottom),
      );
      final originalWidth = tester.getSize(first).width + 2;
      expect(
        originalWidth / (tester.getSize(second).width + 2),
        closeTo(2, .01),
      );
      final originalSelection = controller.selectedClipId;
      final initialHeight = region.height;
      await tester.tap(find.byKey(const Key('media-timeline-larger')));
      await tester.pumpAndSettle();
      expect(tester.getSize(timeline).height, greaterThan(initialHeight));
      expect(controller.selectedClipId, originalSelection);
      await tester.tap(find.byKey(const Key('media-timeline-zoom')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('400%'));
      await tester.pumpAndSettle();
      expect(tester.getSize(first).width + 2, greaterThan(originalWidth));
      final labelOrigin = tester.getTopLeft(labels);
      await tester.drag(
        find.byKey(const Key('media-timeline-scroll')),
        const Offset(-350, 0),
      );
      await tester.pumpAndSettle();
      expect(tester.getTopLeft(labels), labelOrigin);
      expect(controller.selectedClipId, originalSelection);
      expect(controller.timeline!.tracks.single.clips[0].sourceOut, 8);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'wide rail toggles preserve the loaded preview and unapplied inspector text',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await _prepareEditableProject(client, controller);
      client.successfulExport = true;
      await tester.pumpWidget(_app(client, controller));
      await tester.pumpAndSettle();
      await controller.export(outputKind: 'video');
      await tester.pumpAndSettle();

      final previewAction = find.byKey(const Key('media-version-preview'));
      await _openActionsForTarget(tester, previewAction);
      await tester.tap(previewAction);
      await tester.pumpAndSettle();
      final preview = find.byType(MediaPreview);
      final previewElement = tester.element(preview);
      expect(preview, findsOneWidget);

      final endField = find.byWidgetPredicate(
        (widget) =>
            widget is TextField && widget.decoration?.labelText == '素材终点（秒）',
      );
      await _openPropertiesForField(tester, endField);
      await tester.ensureVisible(endField);
      await tester.enterText(endField, '6.25');
      await tester.pump();
      expect(tester.widget<TextField>(endField).controller!.text, '6.25');
      expect(controller.timeline!.tracks.single.clips.single.sourceOut, 8);

      final sources = find.byKey(const Key('media-open-sources'));
      await tester.ensureVisible(sources);
      await tester.tap(sources);
      await tester.pumpAndSettle();
      expect(tester.element(preview), same(previewElement));
      expect(tester.widget<TextField>(endField).controller!.text, '6.25');
      await tester.tap(sources);
      await tester.pumpAndSettle();
      expect(tester.element(preview), same(previewElement));

      final properties = find.byKey(const Key('media-open-properties'));
      await tester.ensureVisible(properties);
      await tester.tap(properties);
      await tester.pumpAndSettle();
      expect(endField, findsNothing);
      expect(tester.element(preview), same(previewElement));
      await tester.tap(properties);
      await tester.pumpAndSettle();
      expect(endField, findsOneWidget);
      expect(tester.widget<TextField>(endField).controller!.text, '6.25');
      expect(tester.element(preview), same(previewElement));
      expect(controller.timeline!.tracks.single.clips.single.sourceOut, 8);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'editing after preview labels the prior render and keeps its bytes unchanged',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await _prepareEditableProject(client, controller);
      client.successfulExport = true;
      await tester.pumpWidget(_app(client, controller));
      await tester.pumpAndSettle();
      await controller.export(outputKind: 'video');
      await tester.pumpAndSettle();

      final previewAction = find.byKey(const Key('media-version-preview'));
      await _openActionsForTarget(tester, previewAction);
      await tester.tap(previewAction);
      await tester.pumpAndSettle();
      final preview = find.byType(MediaPreview);
      expect(preview, findsOneWidget);
      final loadedFile = tester.widget<MediaPreview>(preview).file;
      final originalBytes = List<int>.unmodifiable(loadedFile.bytes);

      final endField = find.byWidgetPredicate(
        (widget) =>
            widget is TextField && widget.decoration?.labelText == '素材终点（秒）',
      );
      await _openPropertiesForField(tester, endField);
      await tester.ensureVisible(endField);
      await tester.enterText(endField, '6.5');
      await tester.ensureVisible(find.text('应用调整'));
      await tester.tap(find.text('应用调整'));
      await tester.pumpAndSettle();

      expect(controller.hasUnsavedChanges, isTrue);
      expect(controller.timeline!.tracks.single.clips.single.sourceOut, 6.5);
      final previousRender = find.byKey(const Key('media-previous-render'));
      expect(previousRender, findsOneWidget);
      expect(tester.widget<Text>(previousRender).data, isNotEmpty);
      expect(tester.widget<MediaPreview>(preview).file, same(loadedFile));
      expect(
        tester.widget<MediaPreview>(preview).file.bytes,
        orderedEquals(originalBytes),
      );
      expect(client.retrievalCalls, 1);
      final priorSeek = tester.widget<MediaPreview>(preview).seekRequest;
      final ruler = find.byKey(const Key('media-timeline-ruler'));
      await tester.ensureVisible(ruler);
      final cursorSemantics = find
          .ancestor(of: ruler, matching: find.byType(Semantics))
          .first;
      final cursorBefore = tester
          .widget<Semantics>(cursorSemantics)
          .properties
          .value;
      tester
          .widget<MediaPreview>(preview)
          .onPositionChanged
          ?.call(const Duration(seconds: 2));
      await tester.pump();
      expect(
        tester.widget<Semantics>(cursorSemantics).properties.value,
        cursorBefore,
      );
      await tester.tap(ruler);
      await tester.pump();
      expect(
        tester.widget<MediaPreview>(preview).seekRequest,
        priorSeek,
        reason:
            'The changed draft must not seek a different saved media version',
      );
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('saved result previews directly and recovers without re-export', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await _prepareEditableProject(client, controller);
    client.successfulExport = true;
    await tester.pumpWidget(_app(client, controller));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('media-monitor-start')), findsOneWidget);
    expect(find.byKey(const Key('media-load-preview')), findsNothing);

    await controller.export(outputKind: 'video');
    await tester.pumpAndSettle();
    final load = find.byKey(const Key('media-load-preview'));
    expect(load, findsOneWidget);
    expect(find.byKey(const Key('media-monitor-start')), findsNothing);
    expect(find.textContaining('成片预览 · v'), findsOneWidget);
    expect(tester.getSize(load).shortestSide, greaterThanOrEqualTo(48));

    client.retrievalFailureCode = 'CONTENT_PROJECT_READ_UNAVAILABLE';
    await tester.tap(load);
    await tester.pumpAndSettle();
    expect(find.byType(MediaPreview), findsNothing);
    expect(controller.version?.artifactId, 'ART-version');
    expect(find.text('操作未完成，草稿和已导出版本仍保留。'), findsOneWidget);
    expect(load, findsOneWidget);

    client.retrievalFailureCode = null;
    client.pendingRetrieval = Completer<void>();
    await tester.tap(load);
    await tester.pump();
    expect(tester.widget<OutlinedButton>(load).onPressed, isNull);
    expect(find.text('正在读取已保存的作品…'), findsOneWidget);
    client.pendingRetrieval!.complete();
    await tester.pumpAndSettle();
    expect(find.byType(MediaPreview), findsOneWidget);
    expect(load, findsNothing);
    expect(find.byType(BottomSheet), findsNothing);
    expect(client.retrievalCalls, 2);
    expect(client.exports, 1);
    expect(tester.takeException(), isNull);
  });

  testWidgets('mobile preview closes actions and reveals the loaded player', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await _prepareEditableProject(client, controller);
    client.successfulExport = true;
    await tester.pumpWidget(_app(client, controller));
    await tester.pumpAndSettle();
    await controller.export(outputKind: 'video');
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.byKey(const Key('media-open-actions')));
    await tester.tap(find.byKey(const Key('media-open-actions')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('media-close-layer')), findsOneWidget);
    await tester.tap(find.byKey(const Key('media-version-preview')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('media-close-layer')), findsNothing);
    expect(client.retrievalCalls, 1);

    await tester.pumpAndSettle();
    final player = find.byType(MediaPreview);
    expect(player, findsOneWidget);
    final rect = tester.getRect(player);
    expect(rect.top, greaterThanOrEqualTo(0));
    expect(
      rect.bottom,
      lessThanOrEqualTo(
        tester.view.physicalSize.height / tester.view.devicePixelRatio,
      ),
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('mobile download keeps actions open with saved-work progress', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await _prepareEditableProject(client, controller);
    client.successfulExport = true;
    final files = _Files();
    await tester.pumpWidget(_app(client, controller, files: files));
    await tester.pumpAndSettle();
    await controller.export(outputKind: 'video');
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.byKey(const Key('media-open-actions')));
    await tester.tap(find.byKey(const Key('media-open-actions')));
    await tester.pumpAndSettle();
    client.pendingRetrieval = Completer<void>();
    await tester.tap(find.byKey(const Key('media-version-download')));
    await tester.pump();
    expect(find.byKey(const Key('media-close-layer')), findsOneWidget);
    expect(find.text('正在读取已保存的作品…'), findsOneWidget);
    expect(find.text('正在导入所选文件…'), findsNothing);

    client.pendingRetrieval!.complete();
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('media-close-layer')), findsOneWidget);
    expect(files.saves, 1);
    expect(controller.version?.artifactId, 'ART-version');
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'failed mobile preview keeps the saved result and shows failure',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await _prepareEditableProject(client, controller);
      client.successfulExport = true;
      await tester.pumpWidget(_app(client, controller));
      await tester.pumpAndSettle();
      await controller.export(outputKind: 'video');
      await tester.pumpAndSettle();

      await tester.ensureVisible(find.byKey(const Key('media-open-actions')));
      await tester.tap(find.byKey(const Key('media-open-actions')));
      await tester.pumpAndSettle();
      client.retrievalFailureCode = 'CONTENT_PROJECT_READ_UNAVAILABLE';
      await tester.tap(find.byKey(const Key('media-version-preview')));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('media-close-layer')), findsNothing);
      expect(find.text('操作未完成，草稿和已导出版本仍保留。'), findsOneWidget);
      expect(find.byType(MediaPreview), findsNothing);
      expect(controller.version?.artifactId, 'ART-version');
      expect(client.retrievalCalls, 1);
      expect(find.text('文件已保存到所选位置。'), findsNothing);
      expect(find.text('已交给浏览器下载，请检查下载记录。'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );

  for (final adopt in [false, true]) {
    testWidgets(
      'audio preview ${adopt ? "adopts" : "cancels"} explicit settings without exporting',
      (tester) async {
        await tester.binding.setSurfaceSize(const Size(1440, 1100));
        addTearDown(() => tester.binding.setSurfaceSize(null));
        await _prepareEditableProject(client, controller);
        await tester.pumpWidget(_app(client, controller));
        await tester.pumpAndSettle();
        await tester.ensureVisible(find.byKey(const Key('media-mastering')));
        await tester.tap(find.byKey(const Key('media-mastering')));
        await tester.pumpAndSettle();
        await tester.ensureVisible(find.byKey(const Key('media-audio-adjust')));
        await tester.tap(find.byKey(const Key('media-audio-adjust')));
        await tester.pumpAndSettle();
        await tester.tap(find.byKey(const Key('audio-preview-target')));
        await tester.pumpAndSettle();
        await tester.tap(find.text('-16 LUFS').last);
        await tester.pumpAndSettle();
        await tester.tap(find.byKey(const Key('audio-preview-denoise')));
        await tester.pumpAndSettle();
        expect(controller.renderOptions, isEmpty);
        await tester.ensureVisible(
          find.byKey(const Key('audio-preview-prepare')),
        );
        await tester.tap(find.byKey(const Key('audio-preview-prepare')));
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('audio-preview-select')), findsOneWidget);
        expect(controller.renderOptions, isEmpty);
        await tester.tap(
          find.byKey(
            Key(adopt ? 'audio-preview-adopt' : 'audio-preview-cancel'),
          ),
        );
        await tester.pumpAndSettle();
        expect(
          controller.renderOptions,
          adopt
              ? {
                  'loudness_target_lufs': -16,
                  'noise_reduction_db': 12,
                  'noise_floor_db': -50,
                }
              : isEmpty,
        );
        expect(client.exports, 0);
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets('no-change and stale-parent rejects use safe editor copy', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1100));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await _prepareEditableProject(client, controller);
    client.successfulExport = true;
    await tester.pumpWidget(_app(client, controller));
    await tester.pumpAndSettle();

    await controller.export(outputKind: 'video');
    await tester.pumpAndSettle();
    expect(controller.version?.artifactId, 'ART-version');
    expect(client.exports, 1);

    await controller.export(outputKind: 'video');
    await tester.pumpAndSettle();
    expect(controller.failureCode, 'CONTENT_PROJECT_NO_CHANGES');
    expect(find.text('先修改内容，再保存新版本。当前作品已保留。'), findsOneWidget);
    expect(client.exports, 1);

    controller.edit((snapshot) => snapshot.undo());
    expect(controller.hasUnsavedChanges, isTrue);
    client.exportFailureCode = 'CONTENT_PROJECT_PARENT_REVISION_REQUIRED';
    await controller.export(outputKind: 'video');
    await tester.pumpAndSettle();

    expect(controller.failureCode, 'CONTENT_PROJECT_PARENT_REVISION_REQUIRED');
    expect(find.text('先修改内容，再保存新版本。当前作品已保留。'), findsOneWidget);
    expect(
      find.textContaining('private parent revision diagnostic'),
      findsNothing,
    );
    expect(
      find.textContaining('CONTENT_PROJECT_PARENT_REVISION_REQUIRED'),
      findsNothing,
    );
    expect(client.exports, 2);
    expect(tester.takeException(), isNull);
  });

  for (final locale in const [Locale('zh', 'CN'), Locale('en'), Locale('ko')]) {
    testWidgets('mobile 200 percent text remains operable in $locale', (
      tester,
    ) async {
      final semantics = tester.ensureSemantics();
      try {
        await tester.binding.setSurfaceSize(const Size(320, 720));
        addTearDown(() => tester.binding.setSurfaceSize(null));
        await tester.pumpWidget(
          _app(client, controller, locale: locale, scale: 2),
        );
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('media-import')), findsNothing);
        final sources = find.byKey(const Key('media-open-sources'));
        final properties = find.byKey(const Key('media-open-properties'));
        final actions = find.byKey(const Key('media-open-actions'));
        for (final control in [sources, properties, actions]) {
          final node = tester.getSemantics(control);
          expect(node.flagsCollection.isButton, isTrue);
          expect(
            node.getSemanticsData().hasAction(SemanticsAction.tap),
            isTrue,
          );
        }

        await tester.ensureVisible(sources);
        var sourcesFocused = false;
        for (var attempt = 0; attempt < 64 && !sourcesFocused; attempt++) {
          sourcesFocused =
              tester.getSemantics(sources).flagsCollection.isFocused ==
              Tristate.isTrue;
          if (!sourcesFocused) {
            await tester.sendKeyEvent(LogicalKeyboardKey.tab);
            await tester.pump();
          }
        }
        expect(sourcesFocused, isTrue);
        await tester.sendKeyEvent(LogicalKeyboardKey.enter);
        await tester.pumpAndSettle();
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('media-import')), findsOneWidget);
        expect(tester.takeException(), isNull);
        await tester.tap(find.byKey(const Key('media-close-layer')));
        await tester.pumpAndSettle();
        await tester.ensureVisible(properties);
        await tester.tap(properties);
        await tester.pumpAndSettle();
        expect(
          tester
              .getSize(find.byKey(const Key('media-close-layer')))
              .shortestSide,
          greaterThanOrEqualTo(48),
        );
        await tester.tap(find.byKey(const Key('media-close-layer')));
        await tester.pumpAndSettle();
        await _openActionsForTarget(
          tester,
          find.byKey(const Key('media-export')),
        );
        await tester.ensureVisible(find.byKey(const Key('media-export')));
        expect(
          tester.getSize(find.byKey(const Key('media-export'))).shortestSide,
          greaterThanOrEqualTo(48),
        );
        expect(tester.takeException(), isNull);
      } finally {
        semantics.dispose();
      }
    });
  }
}
