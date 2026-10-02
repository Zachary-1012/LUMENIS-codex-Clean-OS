import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh01/saved_media_projects_controller.dart';

const _cursorA = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';
const _cursorB = 'BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB';
const _createdAt = '2026-10-02T10:15:30.000000Z';

Map<String, dynamic> _project({
  String artifactId = 'ART-project-1',
  String outputKind = 'video',
  String createdAt = _createdAt,
  String updatedAt = _createdAt,
  String status = 'staged',
}) => {
  'artifact_id': artifactId,
  'output_kind': outputKind,
  'created_at': createdAt,
  'updated_at': updatedAt,
  'status': status,
};

Map<String, dynamic> _page({
  String status = 'ok',
  List<Map<String, dynamic>> projects = const [],
  String? nextCursor,
  bool ok = true,
  String publishStatus = 'not_performed',
}) => {
  'ok': ok,
  'publish_status': publishStatus,
  'status': status,
  'projects': projects,
  'next_cursor': nextCursor,
};

void main() {
  test(
    'refresh clears old rows and one explicit page appends deduplicated rows',
    () async {
      final requests = <String?>[];
      final controller = SavedMediaProjectsController(
        contextKey: () => 'BMP:GLOBAL',
        loadPage: (cursor) async {
          requests.add(cursor);
          if (cursor == null) {
            return _page(
              status: 'scan_incomplete',
              projects: [_project()],
              nextCursor: _cursorA,
            );
          }
          return _page(
            projects: [
              _project(),
              _project(artifactId: 'ART-project-2', outputKind: 'audio'),
            ],
          );
        },
      );
      addTearDown(controller.dispose);

      await controller.refresh();
      expect(controller.projects.map((project) => project.artifactId), [
        'ART-project-1',
      ]);
      expect(controller.status, SavedMediaProjectsStatus.scanIncomplete);
      expect(controller.nextCursor, _cursorA);
      expect(requests, [null]);

      await controller.loadMore();
      expect(controller.projects.map((project) => project.artifactId), [
        'ART-project-1',
        'ART-project-2',
      ]);
      expect(controller.projects.last.outputKind, 'audio');
      expect(controller.projects.first.createdAt, _createdAt);
      // A later clean page cannot erase an earlier partial-scan state.
      expect(controller.status, SavedMediaProjectsStatus.scanIncomplete);
      expect(controller.nextCursor, isNull);
      expect(requests, [null, _cursorA]);
      await controller.loadMore();
      expect(requests, [null, _cursorA]);
    },
  );

  test('refresh resets page state and distinguishes an empty result', () async {
    final pending = Completer<Map<String, dynamic>>();
    var call = 0;
    final controller = SavedMediaProjectsController(
      contextKey: () => 'CTH:GLOBAL',
      loadPage: (_) {
        call++;
        if (call == 1) return Future.value(_page(projects: [_project()]));
        return pending.future;
      },
    );
    addTearDown(controller.dispose);

    await controller.refresh();
    final refreshing = controller.refresh();
    expect(controller.busy, isTrue);
    expect(controller.loaded, isFalse);
    expect(controller.projects, isEmpty);
    expect(controller.nextCursor, isNull);

    pending.complete(_page(status: 'empty'));
    await refreshing;
    expect(controller.loaded, isTrue);
    expect(controller.busy, isFalse);
    expect(controller.status, SavedMediaProjectsStatus.empty);
    expect(controller.errorCode, isNull);
  });

  test(
    'integrity incomplete remains distinct from empty and scan incomplete',
    () async {
      final controller = SavedMediaProjectsController(
        contextKey: () => 'CTH:GLOBAL',
        loadPage: (_) async => _page(
          status: 'integrity_incomplete',
          projects: [_project()],
          nextCursor: _cursorB,
        ),
      );
      addTearDown(controller.dispose);

      await controller.refresh();
      expect(controller.status, SavedMediaProjectsStatus.integrityIncomplete);
      expect(controller.projects, hasLength(1));
      expect(controller.nextCursor, _cursorB);
      expect(controller.errorCode, isNull);
    },
  );

  test('backend naive timestamp is retained for display', () async {
    const timestamp = '2026-10-02 10:15:30';
    final controller = SavedMediaProjectsController(
      contextKey: () => 'CTH:GLOBAL',
      loadPage: (_) async => _page(
        projects: [_project(createdAt: timestamp, updatedAt: timestamp)],
      ),
    );
    addTearDown(controller.dispose);

    await controller.refresh();

    expect(controller.projects.single.createdAt, timestamp);
  });

  test('empty response cannot contain rows or a continuation cursor', () async {
    final controller = SavedMediaProjectsController(
      contextKey: () => 'BMP:GLOBAL',
      loadPage: (_) async =>
          _page(status: 'empty', projects: [_project()], nextCursor: _cursorA),
    );
    addTearDown(controller.dispose);

    await controller.refresh();

    expect(controller.status, SavedMediaProjectsStatus.error);
    expect(controller.errorCode, 'CONTENT_RESPONSE_INVALID');
    expect(controller.projects, isEmpty);
  });

  test('denied list read is an error and never an empty result', () async {
    final controller = SavedMediaProjectsController(
      contextKey: () => 'BMP:GLOBAL',
      loadPage: (_) async => throw const LumenisCoreException(
        'private diagnostic text',
        statusCode: 403,
      ),
    );
    addTearDown(controller.dispose);

    await controller.refresh();
    expect(controller.loaded, isTrue);
    expect(controller.status, SavedMediaProjectsStatus.error);
    expect(controller.errorCode, 'CONTENT_SCOPE_DENIED');
    expect(controller.projects, isEmpty);
  });

  test('malformed page and conflicting duplicate rows are rejected', () async {
    final replies = <String, Map<String, dynamic>>{
      'first': _page(projects: [_project()], nextCursor: _cursorA),
      'bad_kind': _page(projects: [_project(outputKind: 'document')]),
      'conflict': _page(
        projects: [
          _project(
            artifactId: 'ART-project-1',
            createdAt: '2026-10-03T10:15:30Z',
          ),
        ],
      ),
    };
    var selected = 'bad_kind';
    final controller = SavedMediaProjectsController(
      contextKey: () => 'BMP:GLOBAL',
      loadPage: (cursor) async =>
          cursor == null ? replies[selected]! : replies[selected]!,
    );
    addTearDown(controller.dispose);

    await controller.refresh();
    expect(controller.status, SavedMediaProjectsStatus.error);
    expect(controller.errorCode, 'CONTENT_RESPONSE_INVALID');
    expect(controller.projects, isEmpty);

    selected = 'first';
    await controller.refresh();
    selected = 'conflict';
    await controller.loadMore();
    expect(controller.status, SavedMediaProjectsStatus.error);
    expect(controller.errorCode, 'CONTENT_RESPONSE_INVALID');
    expect(controller.projects, isEmpty);
    expect(controller.nextCursor, isNull);
  });

  test('obsolete response cannot populate a new scope after refresh', () async {
    final oldPage = Completer<Map<String, dynamic>>();
    var scope = 'BMP:GLOBAL';
    var requestCount = 0;
    final controller = SavedMediaProjectsController(
      contextKey: () => scope,
      loadPage: (_) {
        requestCount++;
        if (requestCount == 1) return oldPage.future;
        return Future.value(
          _page(projects: [_project(artifactId: 'ART-new-scope')]),
        );
      },
    );
    addTearDown(controller.dispose);

    final firstRead = controller.refresh();
    scope = 'BMP:FOCUS:BRAND-2';
    await controller.refresh();
    expect(controller.projects.single.artifactId, 'ART-new-scope');

    oldPage.complete(_page(projects: [_project(artifactId: 'ART-old-scope')]));
    await firstRead;
    expect(controller.projects.single.artifactId, 'ART-new-scope');
    expect(controller.errorCode, isNull);
  });

  test('context change during a page read clears the old scope list', () async {
    final pending = Completer<Map<String, dynamic>>();
    var scope = 'BMP:GLOBAL';
    var calls = 0;
    final controller = SavedMediaProjectsController(
      contextKey: () => scope,
      loadPage: (_) {
        calls++;
        if (calls == 1) return Future.value(_page(projects: [_project()]));
        return pending.future;
      },
    );
    addTearDown(controller.dispose);

    await controller.refresh();
    final refresh = controller.refresh();
    scope = 'BMP:FOCUS:BRAND-3';
    pending.complete(_page(projects: [_project(artifactId: 'ART-stale')]));
    await refresh;

    expect(controller.projects, isEmpty);
    expect(controller.status, SavedMediaProjectsStatus.error);
    expect(controller.errorCode, 'CONTENT_CONTEXT_CHANGED');
    expect(controller.nextCursor, isNull);
  });

  test(
    'dispose prevents a late page response from notifying or committing',
    () async {
      final pending = Completer<Map<String, dynamic>>();
      final controller = SavedMediaProjectsController(
        contextKey: () => 'CTH:GLOBAL',
        loadPage: (_) => pending.future,
      );
      var notifications = 0;
      controller.addListener(() => notifications++);

      final read = controller.refresh();
      expect(notifications, 1);
      controller.dispose();
      pending.complete(_page(projects: [_project()]));
      await read;
      expect(notifications, 1);
    },
  );

  test(
    'invalidate resets rows and makes an in-flight response stale',
    () async {
      final pending = Completer<Map<String, dynamic>>();
      final controller = SavedMediaProjectsController(
        contextKey: () => 'CTH:GLOBAL',
        loadPage: (_) => pending.future,
      );
      addTearDown(controller.dispose);

      final read = controller.refresh();
      controller.invalidate();
      pending.complete(_page(projects: [_project()]));
      await read;

      expect(controller.projects, isEmpty);
      expect(controller.loaded, isFalse);
      expect(controller.busy, isFalse);
      expect(controller.status, SavedMediaProjectsStatus.idle);
    },
  );
}
