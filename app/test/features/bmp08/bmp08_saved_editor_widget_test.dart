import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/bmp08/bmp08_repository.dart';
import 'package:lumenis_app/features/bmp08/bmp08_screen.dart';
import 'package:lumenis_app/features/bmp08/bmp08_snapshot.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';
import 'bmp08_saved_work_test.dart' show fixture;

void main() {
  testWidgets('incomplete first page stays warned after a clean page and resets on reopen', (tester) async {
    final repo = _Repository()..paginate = true..firstPageIncomplete = true;
    const warning = 'Some records could not be verified; the list may be incomplete.';
    await tester.pumpWidget(_app(repo)); await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('podcast-open-shared'))); await tester.pumpAndSettle();
    expect(find.text(warning), findsOneWidget);
    await tester.tap(find.text('Load more')); await tester.pumpAndSettle();
    expect(repo.cursors, [null, 'opaque-next']);
    expect(find.text(warning), findsOneWidget);
    expect(find.text('Episode'), findsOneWidget);
    await tester.tap(find.text('Close')); await tester.pumpAndSettle();
    repo.paginate = false;
    repo.firstPageIncomplete = false;
    await tester.tap(find.byKey(const ValueKey('podcast-open-shared'))); await tester.pumpAndSettle();
    expect(repo.cursors, [null, 'opaque-next', null]);
    expect(find.text('Episode'), findsOneWidget);
    expect(find.text(warning), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Shared editor works without brand binding; cancel preserves dirty text; failure retries same request', (tester) async {
    final repo = _Repository()..failNextSave = true;
    await tester.pumpWidget(_app(repo)); await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('podcast-open-brand')), findsNothing);
    await tester.tap(find.byKey(const ValueKey('podcast-open-shared'))); await tester.pumpAndSettle();
    await tester.tap(find.text('Episode')); await tester.pumpAndSettle();
    expect(find.text('Original'), findsOneWidget);
    await tester.enterText(find.byType(TextFormField), 'Corrected'); await tester.pump();
    await tester.tap(find.text('Close')); await tester.pumpAndSettle();
    await tester.tap(find.text('Keep editing')); await tester.pumpAndSettle();
    expect(find.text('Corrected'), findsOneWidget);
    final save = find.text('Save new script version');
    await tester.ensureVisible(save); await tester.tap(save); await tester.pumpAndSettle();
    expect(find.textContaining('saved version changed'), findsOneWidget);
    expect(find.text('Corrected'), findsOneWidget);
    await tester.ensureVisible(save); await tester.tap(save); await tester.pumpAndSettle();
    expect(repo.requestIds.length, 2); expect(repo.requestIds.first, repo.requestIds.last);
    expect(repo.domains.every((v) => v == null), isTrue);
    expect(find.text('Script version saved and read back.'), findsOneWidget);
    expect(find.text('Original'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('closing an outstanding list ignores its late result', (tester) async {
    final pending = Completer<Map<String, dynamic>>();
    final repo = _Repository()..pendingList = pending;
    await tester.pumpWidget(_app(repo)); await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('podcast-open-shared'))); await tester.pump();
    await tester.tap(find.text('Close')); await tester.pumpAndSettle();
    pending.complete(repo.listResult); await tester.pumpAndSettle();
    expect(find.text('Episode'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('pending write disables duplicate save and close until readback completes', (tester) async {
    final pending = Completer<Bmp08SavedEpisode>();
    final repo = _Repository()..pendingSave = pending;
    await tester.pumpWidget(_app(repo)); await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('podcast-open-shared'))); await tester.pumpAndSettle();
    await tester.tap(find.text('Episode')); await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextFormField), 'Corrected'); await tester.pump();
    final save = find.widgetWithText(FilledButton, 'Save new script version');
    await tester.ensureVisible(save); await tester.tap(save); await tester.pump();
    expect(tester.widget<FilledButton>(save).onPressed, isNull);
    expect(tester.widget<TextButton>(find.widgetWithText(TextButton, 'Close')).onPressed, isNull);
    expect(repo.requestIds, hasLength(1));
    pending.complete(Bmp08SavedEpisode.fromResponse(fixture(version: 2, corrected: 'Corrected')));
    await tester.pumpAndSettle();
    expect(find.text('Script version saved and read back.'), findsOneWidget);
    expect(repo.requestIds, hasLength(1));
    expect(tester.takeException(), isNull);
  });

  testWidgets('list pagination uses returned cursor and does not duplicate records', (tester) async {
    final repo = _Repository()..paginate = true;
    await tester.pumpWidget(_app(repo)); await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('podcast-open-shared'))); await tester.pumpAndSettle();
    await tester.tap(find.text('Load more')); await tester.pumpAndSettle();
    expect(repo.cursors, [null, 'opaque-next']);
    expect(find.text('Episode'), findsOneWidget);
    expect(find.text('Load more'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  for (final language in ['zh','en','ko']) {
    testWidgets('saved editor $language at narrow width and 200% text', (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(_app(_Repository(), language: language, textScale: 2));
      await tester.pumpAndSettle();
      final open = find.byKey(const ValueKey('podcast-open-shared'));
      await tester.ensureVisible(open); await tester.tap(open); await tester.pumpAndSettle();
      await tester.tap(find.text('Episode')); await tester.pumpAndSettle();
      expect(find.text('Original'), findsOneWidget);
      expect(find.byType(TextFormField), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }
}

Widget _app(_Repository repository, {String language = 'en', double textScale = 1}) => MaterialApp(
  theme: LumenisTheme.light, locale: Locale(language),
  supportedLocales: LumenisLocalizations.supportedLocales,
  localizationsDelegates: const [LumenisLocalizations.delegate, GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate, GlobalCupertinoLocalizations.delegate],
  builder: (context, child) => MediaQuery(data: MediaQuery.of(context).copyWith(textScaler: TextScaler.linear(textScale)), child: child!),
  home: Scaffold(body: Bmp08Screen(client: LumenisCoreClient(), repository: repository)),
);

class _Repository implements Bmp08Repository, Bmp08SavedWorkRepository {
  bool failNextSave = false, paginate = false, firstPageIncomplete = false;
  final cursors = <String?>[];
  Completer<Bmp08SavedEpisode>? pendingSave;
  Completer<Map<String, dynamic>>? pendingList;
  final requestIds = <String>[];
  final domains = <String?>[];
  Map<String, dynamic> get listResult => {'ok': true, 'result': {
    'items': [(fixture()['result'] as Map)], 'has_more': false, 'next_cursor': null, 'verification_complete': true,
  }};
  @override
  Future<Bmp08Snapshot> load() async => Bmp08Snapshot.fromResponse({'ok':true,'screen':'BMP-08'});
  @override
  Future<Map<String, dynamic>> listEpisodes({String? domainId, String? cursor}) async {
    domains.add(domainId); cursors.add(cursor);
    if (paginate && cursor == null) {
      final value = listResult;
      value['result']['verification_complete'] = !firstPageIncomplete;
      value['result']['has_more'] = true; value['result']['next_cursor'] = 'opaque-next'; return value;
    }
    return pendingList == null ? listResult : await pendingList!.future;
  }
  @override
  Future<Bmp08SavedEpisode> reopenEpisode(String artifactId, {String? domainId}) async {
    domains.add(domainId); return Bmp08SavedEpisode.fromResponse(fixture());
  }
  @override
  Future<Bmp08SavedEpisode> saveEpisode(Bmp08SavedEpisode parent, Map<String, String> edits,
      String requestId, {String? domainId}) async {
    domains.add(domainId); requestIds.add(requestId);
    if (failNextSave) { failNextSave = false; throw const LumenisCoreException('Conflict', statusCode:409); }
    if (pendingSave != null) return await pendingSave!.future;
    return Bmp08SavedEpisode.fromResponse(fixture(version:2, corrected:edits['stable-a']!));
  }
}
