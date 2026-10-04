import 'dart:async';
import 'dart:ui' show Tristate;

import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/shared/sh01/media_project_controller.dart';
import 'package:lumenis_app/features/shared/sh01/media_project_files.dart';
import 'package:lumenis_app/features/shared/sh01/media_preview.dart';
import 'package:lumenis_app/features/shared/sh01/media_project_workbench.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';
import 'package:lumenis_app/navigation/lumenis_leave_guard.dart';

// These are widget contract fixtures, never media/render or user E2E evidence.
class _Client extends LumenisCoreClient {
  int imports = 0;
  int importCalls = 0;
  int inspectCalls = 0;
  int exports = 0;
  int confirmationCalls = 0;
  bool? confirmedImport;
  bool approvalRequired = false;
  bool successfulExport = false;
  String? exportFailureCode;
  Duration confirmationLifetime = const Duration(minutes: 5);
  Completer<void>? pendingImport;
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
  Map<String, dynamic>? savedExport;
  String? reopenedReference;
  String? reopenFailure;
  int reopenCalls = 0;
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

  @override
  Map<String, dynamic>? get currentContextEnvelope => contextEnvelope;

  @override
  Future<ContentProjectFile> contentProjectFile({
    required String domainId,
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
    required String domainId,
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
    required String domainId,
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
          resource: 'content-source-import:v1:${'b' * 64}',
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
        'artifact': {'artifact_id': 'ART-source'},
        'asset': asset,
      },
    };
  }

  @override
  Future<Map<String, dynamic>> confirmContentSource({
    required String domainId,
    required String confirmationId,
    required bool confirmed,
  }) async {
    confirmationCalls++;
    confirmedImport = confirmed;
    lastImportDomain = domainId;
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
    required String domainId,
    List<String>? assetPaths,
    List<String>? assetRefs,
    required Map<String, dynamic> timeline,
    required String outputKind,
    required bool demoAcknowledged,
    String? previousArtifactId,
  }) async {
    exports++;
    exportedRefs = assetRefs;
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
          'status': 'rendered_staged',
          'artifact': {'artifact_id': 'ART-version'},
          'project': {
            'schema_version': 1,
            'output_kind': outputKind,
            'timeline': timeline,
            'rights': {'state': 'unknown', 'demo_acknowledged': true},
            'source_artifact_refs': assetRefs ?? const <String>[],
          },
          'render': {
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
    required String domainId,
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
            'output_kind': 'video',
            'created_at': '2026-10-02 09:00:00',
            'updated_at': '2026-10-02 09:00:00',
            'status': 'staged',
          },
      ],
      'next_cursor': null,
    };
  }

  @override
  Future<Map<String, dynamic>> reopenContentProject({
    required String domainId,
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
  Locale locale = const Locale('zh', 'CN'),
  double scale = 1,
  EdgeInsets viewInsets = EdgeInsets.zero,
  bool contextAvailable = true,
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
    child: child!,
  ),
  home: guard == null
      ? _workbenchHome(
          client,
          controller,
          invokingDomain: invokingDomain,
          contextAvailable: contextAvailable,
          onBack: onBack,
          files: files ?? _Files(),
        )
      : LumenisLeaveScope(
          guard: guard,
          child: _workbenchHome(
            client,
            controller,
            invokingDomain: invokingDomain,
            contextAvailable: contextAvailable,
            onBack: onBack,
            files: files ?? _Files(),
          ),
        ),
);

Widget _workbenchHome(
  _Client client,
  MediaProjectController? controller, {
  String? invokingDomain,
  required bool contextAvailable,
  VoidCallback? onBack,
  required MediaProjectFiles files,
}) => Scaffold(
  body: MediaProjectWorkbench(
    client: client,
    invokingDomain: invokingDomain,
    controller: controller,
    contextAvailable: contextAvailable,
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
    'open saved-work dialog clears a completed list on available scope change',
    (tester) async {
      await _prepareEditableProject(client, controller);
      client.successfulExport = true;
      await controller.export(outputKind: 'video', demoAcknowledged: true);
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
      await controller.export(outputKind: 'video', demoAcknowledged: true);
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
      await controller.export(outputKind: 'video', demoAcknowledged: true);
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
      await controller.export(outputKind: 'video', demoAcknowledged: true);
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

  testWidgets('GLOBAL_ALL asks for an explicit business purpose', (
    tester,
  ) async {
    client.contextEnvelope = {
      'contract': 'lumenis.context.v1',
      'selection_only': true,
      'context': {'mode': 'GLOBAL_ALL', 'subject_id': null},
    };
    await tester.pumpWidget(_app(client, null));
    await tester.pumpAndSettle();
    expect(find.text('请选择本次剪辑的用途：商业运营或品牌市场。'), findsOneWidget);
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
  });

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
      expect(client.exports, 0);
      await tester.ensureVisible(find.byType(CheckboxListTile));
      await tester.tap(find.byType(CheckboxListTile));
      await tester.pumpAndSettle();
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
    await tester.tap(find.byType(CheckboxListTile));
    await tester.pumpAndSettle();
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
    await tester.tap(find.byType(CheckboxListTile));
    await tester.pumpAndSettle();
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

      await tester.tap(splitButton);
      await tester.pumpAndSettle();
      expect(controller.timeline!.tracks.single.clips, hasLength(2));
      expect(controller.hasUnsavedChanges, isTrue);
      expect(guard.needsProtection, isTrue);

      await controller.export(outputKind: 'video', demoAcknowledged: true);
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
      await controller.export(outputKind: 'video', demoAcknowledged: true);
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
    await controller.export(outputKind: 'video', demoAcknowledged: true);
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
      await controller.export(outputKind: 'video', demoAcknowledged: true);
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
    final export = controller.export(
      outputKind: 'video',
      demoAcknowledged: true,
    );
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
    await tester.tap(find.byType(CheckboxListTile));
    await tester.pump();
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
    await controller.export(outputKind: 'video', demoAcknowledged: true);
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
      await controller.export(outputKind: 'video', demoAcknowledged: true);
      await tester.pumpAndSettle();

      final action = find.byKey(const Key('media-version-preview'));
      await _openActionsForTarget(tester, action);
      await tester.ensureVisible(action);
      await tester.tap(action);
      await tester.pumpAndSettle();

      final preview = find.byType(MediaPreview);
      final matte = find.byKey(const Key('media-preview-matte'));
      final timeline = find.byKey(const Key('media-timeline-region'));
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
      await controller.export(outputKind: 'video', demoAcknowledged: true);
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
      await controller.export(outputKind: 'video', demoAcknowledged: true);
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
    expect(find.text('导出后可预览真实成片。'), findsOneWidget);
    expect(find.byKey(const Key('media-load-preview')), findsNothing);

    await controller.export(outputKind: 'video', demoAcknowledged: true);
    await tester.pumpAndSettle();
    final load = find.byKey(const Key('media-load-preview'));
    expect(load, findsOneWidget);
    expect(find.text('导出后可预览真实成片。'), findsNothing);
    expect(find.textContaining('已导出成片 · v'), findsOneWidget);
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
    await controller.export(outputKind: 'video', demoAcknowledged: true);
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
    await controller.export(outputKind: 'video', demoAcknowledged: true);
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
      await controller.export(outputKind: 'video', demoAcknowledged: true);
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

  testWidgets('no-change and stale-parent rejects use safe editor copy', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1100));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await _prepareEditableProject(client, controller);
    client.successfulExport = true;
    await tester.pumpWidget(_app(client, controller));
    await tester.pumpAndSettle();

    await controller.export(outputKind: 'video', demoAcknowledged: true);
    await tester.pumpAndSettle();
    expect(controller.version?.artifactId, 'ART-version');
    expect(client.exports, 1);

    await controller.export(outputKind: 'video', demoAcknowledged: true);
    await tester.pumpAndSettle();
    expect(controller.failureCode, 'CONTENT_PROJECT_NO_CHANGES');
    expect(find.text('先修改内容，再保存新版本。当前作品已保留。'), findsOneWidget);
    expect(client.exports, 1);

    controller.edit((snapshot) => snapshot.undo());
    expect(controller.hasUnsavedChanges, isTrue);
    client.exportFailureCode = 'CONTENT_PROJECT_PARENT_REVISION_REQUIRED';
    await controller.export(outputKind: 'video', demoAcknowledged: true);
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
