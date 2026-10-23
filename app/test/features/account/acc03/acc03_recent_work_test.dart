import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/account/acc03/acc03_recent_work.dart';

import '../../shared/shared_test_support.dart';

const _id = 'ART-0123456789abcdef';
Map<String, dynamic> _item({String kind = 'research'}) => {
  'artifact': {'artifact_id': _id, 'sha256': 'a' * 64},
  'document': {
    'schema': 'lumenis.saved-work/v1',
    'work_id': 'WORK-${'b' * 24}',
    'title': '已保存的研究',
    'kind': kind,
    'version': 3,
    'draft_digest': 'c' * 64,
    'payload': {
      'source_brief_reference': {'job_id': 'brief-${'d' * 32}'},
    },
    'context': {'scope_kind': 'shared_workspace', 'version': 1, 'actor_id': 1},
    'contract': {'id': 'lumenis.internal-pitch', 'version': '4'},
  },
  'resume': {
    'artifact_id': _id,
    'work_id': 'WORK-${'b' * 24}',
    'expected_sha256': 'a' * 64,
    'expected_draft_digest': 'c' * 64,
    'version': 3,
    'state': 'ready_to_reopen',
    'execution': 'not_started',
  },
};

Map<String, dynamic> _page(
  List<Object?> items, {
  bool complete = true,
  String? cursor,
}) => {
  'ok': true,
  'result': {
    'items': items,
    'verification_complete': complete,
    'has_more': cursor != null,
    'next_cursor': cursor,
  },
};

class _Client extends LumenisCoreClient {
  final reads = <Completer<Map<String, dynamic>>>[];
  final cursors = <String?>[];
  @override
  Future<Map<String, dynamic>> listLatestSharedWork({String? cursor}) {
    cursors.add(cursor);
    final pending = Completer<Map<String, dynamic>>();
    reads.add(pending);
    return pending.future;
  }
}

void main() {
  testWidgets(
    'uploaded material uses the reader rather than research-result editing',
    (tester) async {
      final client = _Client();
      final item = _item();
      (item['document'] as Map)['payload'] = {
        'source_material': {'origin': 'user-upload'},
      };
      final opened = <String>[];
      await tester.pumpWidget(
        sharedTestApp(
          Acc03RecentWork(
            client: client,
            onOpen: (kind, _) => opened.add(kind),
          ),
        ),
      );
      client.reads.single.complete(_page([item]));
      await tester.pumpAndSettle();
      await tester.tap(find.text('已保存的研究'));
      expect(opened, ['material']);
    },
  );

  for (final (storedKind, routeKind) in [
    ('research', 'research'),
    ('report', 'manuscript'),
  ]) {
    testWidgets(
      'opens the exact $routeKind without creating or executing a task',
      (tester) async {
        final client = _Client();
        final opened = <(String, String)>[];
        await tester.pumpWidget(
          sharedTestApp(
            Acc03RecentWork(
              client: client,
              onOpen: (kind, id) => opened.add((kind, id)),
            ),
          ),
        );
        client.reads.single.complete(_page([_item(kind: storedKind)]));
        await tester.pumpAndSettle();
        await tester.tap(find.text('已保存的研究'));
        expect(opened, [(routeKind, _id)]);
        expect(client.reads, hasLength(1));
        expect(find.textContaining('版本 3'), findsOneWidget);
      },
    );
  }

  testWidgets('late old identity results cannot reveal retired content', (
    tester,
  ) async {
    final old = _Client(), current = _Client();
    await tester.pumpWidget(sharedTestApp(Acc03RecentWork(client: old)));
    await tester.pumpWidget(sharedTestApp(Acc03RecentWork(client: current)));
    current.reads.single.completeError(
      const LumenisCoreException('denied', statusCode: 403),
    );
    await tester.pumpAndSettle();
    old.reads.single.complete(_page([_item()]));
    await tester.pumpAndSettle();
    expect(find.text('已保存的研究'), findsNothing);
    expect(find.text('暂时无法读取，重试'), findsOneWidget);
  });

  testWidgets(
    'missing version hashes and partial coverage do not become empty success',
    (tester) async {
      final client = _Client();
      final malformed = _item();
      (malformed['artifact'] as Map).remove('sha256');
      (malformed['resume'] as Map).remove('expected_sha256');
      await tester.pumpWidget(sharedTestApp(Acc03RecentWork(client: client)));
      client.reads.single.complete(_page([malformed], complete: false));
      await tester.pumpAndSettle();
      expect(find.text('已保存的研究'), findsNothing);
      expect(find.text('还没有已保存的工作'), findsNothing);
      expect(find.text('部分工作暂时无法读取'), findsOneWidget);
    },
  );

  testWidgets('repeated continuation cursor clears an unsafe result', (
    tester,
  ) async {
    final client = _Client();
    await tester.pumpWidget(sharedTestApp(Acc03RecentWork(client: client)));
    client.reads.single.complete(_page([_item()], cursor: 'next'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('更多工作'));
    client.reads.last.complete(_page([_item()], cursor: 'next'));
    await tester.pumpAndSettle();
    expect(client.cursors, [null, 'next']);
    expect(find.text('已保存的研究'), findsNothing);
    expect(find.text('暂时无法读取，重试'), findsOneWidget);
  });
}
