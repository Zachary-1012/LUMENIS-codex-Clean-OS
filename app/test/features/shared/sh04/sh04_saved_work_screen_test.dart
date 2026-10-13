import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/read_aloud_action.dart';
import 'package:lumenis_app/features/shared/sh04/sh04_screen.dart';

import '../shared_test_support.dart';

const _title = 'Saved work reading path';
const _firstBody = 'First saved body for the reader.';
const _secondBody = 'Revised saved body for comparison.';
const _focusId = 'subject-one';
const _parentId = 'ART-0000000000000001';
const _currentId = 'ART-0000000000000002';

void main() {
  testWidgets('390px list opens by fresh read and returns to results', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final row = _record(artifactId: _currentId, markdown: _firstBody);
    final client = _clientWith(row)
      ..reopenResults[_currentId] = _withReceipt(row);

    await tester.pumpWidget(_app(client));
    await tester.pumpAndSettle();

    expect(find.text(_title), findsOneWidget);
    expect(_hasReaderText(tester, _firstBody), isFalse);
    expect(find.byType(PopupMenuButton<String>), findsNothing);
    expect(find.byType(ReadAloudAction), findsNothing);

    await tester.tap(find.text(_title));
    await tester.pumpAndSettle();

    expect(client.reopenCalls, [_currentId]);
    expect(_hasReaderText(tester, _title), isTrue);
    expect(_hasReaderText(tester, _firstBody), isTrue);
    expect(find.byType(PopupMenuButton<String>), findsOneWidget);
    expect(find.byType(ReadAloudAction), findsOneWidget);

    await tester.tap(find.byTooltip('返回成果'));
    await tester.pumpAndSettle();

    expect(find.text(_title), findsOneWidget);
    expect(_hasReaderText(tester, _firstBody), isFalse);
    expect(find.byType(PopupMenuButton<String>), findsNothing);
    expect(find.byType(ReadAloudAction), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('wide layout keeps the queue beside a freshly reopened reader', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final row = _record(artifactId: _currentId, markdown: _firstBody);
    final client = _clientWith(row)
      ..reopenResults[_currentId] = _withReceipt(row);

    await tester.pumpWidget(_app(client));
    await tester.pumpAndSettle();
    await tester.tap(find.text(_title));
    await tester.pumpAndSettle();

    expect(
      find.descendant(of: find.byType(ListView), matching: find.text(_title)),
      findsOneWidget,
    );
    expect(_hasReaderText(tester, _title), isTrue);
    expect(_hasReaderText(tester, _firstBody), isTrue);
    expect(find.byType(PopupMenuButton<String>), findsOneWidget);
    expect(find.byType(ReadAloudAction), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('200% text scale failure state fits zh, en, and ko', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    for (final locale in const [
      Locale('zh', 'CN'),
      Locale('en'),
      Locale('ko'),
    ]) {
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump();
      final client = _SavedWorkClient()
        ..listResults['CTH'] = LumenisCoreException(
          'HTTP 403 isolated failure fixture',
          statusCode: 403,
        );

      await tester.pumpWidget(_app(client, locale: locale, textScale: 2));
      await tester.pumpAndSettle();

      expect(find.byType(OutlinedButton), findsOneWidget, reason: '$locale');
      expect(tester.takeException(), isNull, reason: '$locale');
    }
  });

  testWidgets('freshly reopened title and body are exposed to accessibility', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final semantics = tester.ensureSemantics();
    try {
      final row = _record(artifactId: _currentId, markdown: _firstBody);
      final client = _clientWith(row)
        ..reopenResults[_currentId] = _withReceipt(row);

      await tester.pumpWidget(_app(client));
      await tester.pumpAndSettle();
      await tester.tap(find.text(_title));
      await tester.pumpAndSettle();

      expect(client.reopenCalls, [_currentId]);
      expect(find.bySemanticsLabel(_title), findsOneWidget);
      expect(find.bySemanticsLabel(_firstBody), findsOneWidget);
      expect(tester.takeException(), isNull);
    } finally {
      semantics.dispose();
    }
  });

  testWidgets('390px ready reader fits 200% text in zh, en, and ko', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    for (final locale in const [
      Locale('zh', 'CN'),
      Locale('en'),
      Locale('ko'),
    ]) {
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump();
      final row = _record(artifactId: _currentId, markdown: _firstBody);
      final client = _clientWith(row)
        ..reopenResults[_currentId] = _withReceipt(row);

      await tester.pumpWidget(_app(client, locale: locale, textScale: 2));
      await tester.pumpAndSettle();
      await tester.tap(find.text(_title));
      await tester.pumpAndSettle();

      expect(client.reopenCalls, [_currentId], reason: '$locale');
      expect(_hasReaderText(tester, _title), isTrue, reason: '$locale');
      expect(_hasReaderText(tester, _firstBody), isTrue, reason: '$locale');
      expect(tester.takeException(), isNull, reason: '$locale');
    }
  });

  testWidgets('comparison displays both verified parent and current versions', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final parent = _record(artifactId: _parentId, markdown: _firstBody);
    final current = _record(
      artifactId: _currentId,
      markdown: _secondBody,
      version: 2,
      parentArtifactId: _parentId,
      parentSha256: 'a' * 64,
    );
    final client = _clientWith(current)
      ..reopenResults[_currentId] = _withReceipt(current)
      ..reopenResults[_parentId] = _withReceipt(parent);

    await tester.pumpWidget(_app(client));
    await tester.pumpAndSettle();
    await tester.tap(find.text(_title));
    await tester.pumpAndSettle();
    await tester.tap(_compareButton());
    await tester.pumpAndSettle();

    expect(client.reopenCalls, [_currentId, _parentId]);
    expect(_readerText(tester), contains(_firstBody));
    expect(_readerText(tester), contains(_secondBody));
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'parent comparison denial stays retryable and shows no parent body',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      final current = _record(
        artifactId: _currentId,
        markdown: _secondBody,
        version: 2,
        parentArtifactId: _parentId,
        parentSha256: 'a' * 64,
      );
      final client = _clientWith(current)
        ..reopenResults[_currentId] = _withReceipt(current)
        ..reopenResults[_parentId] = LumenisCoreException(
          'HTTP 403 isolated parent fixture',
          statusCode: 403,
        );

      await tester.pumpWidget(_app(client));
      await tester.pumpAndSettle();
      await tester.tap(find.text(_title));
      await tester.pumpAndSettle();
      await tester.tap(_compareButton());
      await tester.pumpAndSettle();

      expect(client.reopenCalls, [_currentId, _parentId]);
      expect(find.byType(OutlinedButton), findsOneWidget);
      expect(_hasReaderText(tester, _firstBody), isFalse);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('failed fresh reopen never exposes download or read aloud', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final row = _record(artifactId: _currentId, markdown: _firstBody);
    final client = _clientWith(row)
      ..reopenResults[_currentId] = LumenisCoreException(
        'HTTP 403 isolated reopen fixture',
        statusCode: 403,
      );

    await tester.pumpWidget(_app(client));
    await tester.pumpAndSettle();
    expect(find.byType(PopupMenuButton<String>), findsNothing);
    expect(find.byType(ReadAloudAction), findsNothing);

    await tester.tap(find.text(_title));
    await tester.pumpAndSettle();

    expect(client.reopenCalls, [_currentId]);
    expect(find.byType(OutlinedButton), findsOneWidget);
    expect(find.byType(PopupMenuButton<String>), findsNothing);
    expect(find.byType(ReadAloudAction), findsNothing);
    expect(_hasReaderText(tester, _firstBody), isFalse);
    expect(tester.takeException(), isNull);
  });
}

Widget _app(
  _SavedWorkClient client, {
  Locale locale = const Locale('zh', 'CN'),
  double textScale = 1,
}) => sharedTestApp(
  Builder(
    builder: (context) => MediaQuery(
      data: MediaQuery.of(
        context,
      ).copyWith(textScaler: TextScaler.linear(textScale)),
      child: Sh04Screen(client: client),
    ),
  ),
  locale: locale,
);

Finder _compareButton() => find.ancestor(
  of: find.byIcon(Icons.compare_arrows_rounded),
  matching: find.byType(TextButton),
);

bool _hasReaderText(WidgetTester tester, String value) =>
    _readerText(tester).contains(value);

List<String> _readerText(WidgetTester tester) {
  final selectionArea = find.byType(SelectionArea);
  if (selectionArea.evaluate().isEmpty) return const <String>[];
  return tester
      .widgetList<Text>(
        find.descendant(of: selectionArea, matching: find.byType(Text)),
      )
      .map((widget) => widget.data ?? widget.textSpan?.toPlainText() ?? '')
      .toList(growable: false);
}

_SavedWorkClient _clientWith(Map<String, dynamic> record) =>
    _SavedWorkClient()..listResults['CTH'] = _page([record]);

class _SavedWorkClient extends LumenisCoreClient {
  _SavedWorkClient() : super(baseUrl: 'http://127.0.0.1:1');

  @override
  Map<String, dynamic>? get currentContextEnvelope => {
    'ok': true,
    'contract': 'lumenis.context.v1',
    'selection_only': true,
    'context': {'mode': 'FOCUS', 'domain_id': 'CTH', 'subject_id': _focusId},
  };

  @override
  List<String> get savedWorkDomains => const ['CTH'];

  final Map<String, Object> listResults = {};
  final Map<String, Object> reopenResults = {};
  final List<String> reopenCalls = [];

  @override
  Future<Map<String, dynamic>> listSavedWorks({
    required String domainId,
    String query = '',
    int limit = 30,
    String? cursor,
  }) async {
    final result = listResults[domainId];
    if (result == null) return _page(const []);
    if (result is Exception) throw result;
    return Map<String, dynamic>.from(result as Map);
  }

  @override
  Future<Map<String, dynamic>> reopenSavedWork({
    required String domainId,
    required String artifactId,
  }) async {
    reopenCalls.add(artifactId);
    final result = reopenResults[artifactId];
    if (result == null) throw StateError('Missing reopen fixture: $artifactId');
    if (result is Exception) throw result;
    return Map<String, dynamic>.from(result as Map);
  }
}

Map<String, dynamic> _page(List<Map<String, dynamic>> items) => {
  'items': items,
  'has_more': false,
  'next_cursor': null,
  'verification_complete': true,
  'unverified_candidates': 0,
};

Map<String, dynamic> _record({
  required String artifactId,
  required String markdown,
  int version = 1,
  String? parentArtifactId,
  String? parentSha256,
}) {
  final workId = 'WORK-000000000000000000000001';
  final scope = <String, dynamic>{
    'domain_id': 'cth',
    'subject_id': _focusId,
    'brand_focus_id': null,
    'global_scope': false,
  };
  final contract = <String, dynamic>{
    'id': 'lumenis.saved-work',
    'version': '1',
    'required_payload_paths': <String>[],
  };
  final document = <String, dynamic>{
    'schema': 'lumenis.saved-work/v1',
    'context': {...scope, 'actor_id': 'actor-1'},
    'work_id': workId,
    'version': version,
    'parent_artifact_id': parentArtifactId,
    'parent_sha256': parentSha256,
    'request_id': 'request-$artifactId',
    'input_hash': 'b' * 64,
    'draft_digest': 'c' * 64,
    'contract': contract,
    'task_id': null,
    'assertion_id': null,
    'kind': 'report',
    'title': _title,
    'markdown': markdown,
    'payload': <String, dynamic>{},
    'citations': <Map<String, dynamic>>[],
    'created_at': '2026-10-11T00:00:00+00:00',
    'authorship': 'user-supplied; source facts require citations',
  };
  final artifact = <String, dynamic>{
    'artifact_id': artifactId,
    'kind': 'saved_document',
    'product_id': 'CTH',
    'domain_id': 'cth',
    'source_execution_id': workId,
    'sha256': 'a' * 64,
    'size_bytes': 100,
    'created_at': '2026-10-11T00:00:00+00:00',
    'status': 'staged',
    'approval_required': true,
    'approval_status': 'pending',
  };
  return {
    'artifact': artifact,
    'document': document,
    'return_ref': {
      'artifact_id': artifactId,
      'work_id': workId,
      'version': version,
      'scope': scope,
    },
  };
}

Map<String, dynamic> _withReceipt(Map<String, dynamic> source) {
  final artifact = source['artifact'] as Map<String, dynamic>;
  final document = source['document'] as Map<String, dynamic>;
  final returnRef = source['return_ref'] as Map<String, dynamic>;
  final contract = document['contract'] as Map<String, dynamic>;
  final scope = returnRef['scope'] as Map<String, dynamic>;
  return {
    ...source,
    'receipt': {
      'schema': 'lumenis.committed-saved-work/v1',
      'task_id': document['task_id'],
      'assertion_id': document['assertion_id'],
      'contract': contract,
      'scope': scope,
      'ref': artifact['artifact_id'],
      'work_id': document['work_id'],
      'version': document['version'],
      'parent': {
        'ref': document['parent_artifact_id'],
        'sha256': document['parent_sha256'],
      },
      'sha256': artifact['sha256'],
      'size_bytes': artifact['size_bytes'],
      'draft_digest': document['draft_digest'],
      'sources': <Map<String, dynamic>>[],
      'constraint_observations': {
        'committed_bytes_match': true,
        'parent_chain_verified': true,
        'required_payload_paths_present': contract['required_payload_paths'],
        'source_authorization': 'fresh-per-source',
        'source_count': 0,
        'factual_verification': 'NOT_ESTABLISHED_BY_STORAGE',
        'learning_admission': 'NOT_ESTABLISHED_BY_STORAGE',
        'training_eligible': false,
        'held_out': false,
        'assertion_binding': 'absent',
        'media_lineage': 'not_applicable',
      },
      'commit_state': 'registry_committed_artifact_staged',
    },
  };
}
