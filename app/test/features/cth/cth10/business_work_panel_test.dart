// Consumer widget regressions with an isolated client; these are not user E2E.
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/cth/cth10/business_work_panel.dart';
import 'package:lumenis_app/features/shared/sh04/sh04_export_files.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

const _workId =
    'work-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';
const _question = 'Private operating decision';
const _revision = 'app_evidence_records:10';
const _artifact = 'ART-0123456789abcdef';
const _secondArtifact = 'ART-0123456789abcde2';
const _internalArtifact = 'ART-1111111111111111';
const _internalTask = 'internal-pitch-task-not-user-copy';
const _internalWork = 'internal-writing-work-not-user-copy';
const _internalTitle = 'Permitted operating manuscript';
const _internalBody = 'The original internal material is available for review.';
const _copy = LumenisLocalizations(Locale('en'));
String _label(String key) => _copy.text('business.work.$key');

void main() {
  _internalCreationTests();
  _decisionDateTests();
  _decisionEditTests();
  _savedExportTests();
  _questionPresentationTests();
  testWidgets('report reading fits narrow and wide layouts in three locales', (
    tester,
  ) async {
    for (final locale in LumenisLocalizations.supportedLocales) {
      for (final width in [390.0, 1440.0]) {
        await tester.pumpWidget(const SizedBox.shrink());
        await _openWork(
          tester,
          _BusinessClient()..addReport(),
          locale: locale,
          surface: Size(width, 1100),
        );
        await tester.scrollUntilVisible(
          find.text('Report states 103 posts and 205 comments.'),
          160,
          scrollable: find
              .descendant(
                of: find.byKey(const ValueKey('business/main-scroll')),
                matching: find.byType(Scrollable),
              )
              .first,
        );
        expect(
          find.text('Report states 103 posts and 205 comments.'),
          findsOneWidget,
        );
        expect(tester.takeException(), isNull);
      }
    }
  });

  testWidgets(
    'report answers and grounded checks are visible without engineering labels',
    (tester) async {
      final client = _BusinessClient()..addReport();
      await _openWork(tester, client);
      expect(find.text('Report answers'), findsOneWidget);
      expect(
        find.text('Report states 103 posts and 205 comments.'),
        findsOneWidget,
      );
      await tester.scrollUntilVisible(
        find.text('12 + 41 + 20 = 73; reported total 103.'),
        180,
        scrollable: find
            .descendant(
              of: find.byKey(const ValueKey('business/main-scroll')),
              matching: find.byType(Scrollable),
            )
            .first,
      );
      expect(
        find.text('12 + 41 + 20 = 73; reported total 103.'),
        findsOneWidget,
      );
      expect(find.textContaining('VENUE_OPERATOR_DISCLOSURE'), findsNothing);
      expect(find.textContaining('SRC-internal-report'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'saved result reads headings and body with a short accessible title',
    (tester) async {
      final semantics = tester.ensureSemantics();
      try {
        final client = _BusinessClient()..markSaved();
        final longQuestion = List.filled(
          8,
          'A detailed operating question.',
        ).join(' ');
        client.work['question'] = longQuestion;
        await _openWork(tester, client);
        expect(
          find.byKey(const ValueKey('business/question-summary')),
          findsOneWidget,
        );
        expect(
          find.byKey(const ValueKey('business/full-question')),
          findsNothing,
        );
        await tester.tap(
          find.byKey(const ValueKey('business/question-toggle')),
        );
        await tester.pumpAndSettle();
        final question = tester.widget<SelectableText>(
          find.byWidgetPredicate(
            (widget) => widget is SelectableText && widget.data == longQuestion,
          ),
        );
        expect(
          question.style,
          Theme.of(
            tester.element(find.byType(BusinessWorkPanel)),
          ).textTheme.bodyLarge,
        );
        await tester.tap(find.text(_label('versions')));
        await tester.pumpAndSettle();
        await tester.tap(find.widgetWithText(TextButton, _label('open')).last);
        await tester.pumpAndSettle();
        final dialog = tester.widget<AlertDialog>(find.byType(AlertDialog));
        expect((dialog.title! as Text).data, 'Operations · v1');
        expect(find.text('Numeric checks'), findsOneWidget);
        expect(find.text('The retained report result.'), findsOneWidget);
        expect(find.text('## Numeric checks'), findsNothing);
        expect(
          find.textContaining('source_bound_business_question_analysis'),
          findsNothing,
        );
        expect(
          find.bySemanticsLabel(RegExp('The retained report result')),
          findsAtLeastNWidgets(1),
        );
        await tester.tap(
          find.descendant(
            of: find.byType(AlertDialog),
            matching: find.widgetWithText(TextButton, _label('close')),
          ),
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      } finally {
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'rechecking material explicitly adopts a new undecided analysis',
    (tester) async {
      final client = _BusinessClient();
      await _openWork(tester, client);
      await tester.tap(find.byKey(const ValueKey('business-recheck-material')));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.widgetWithText(TextField, _label('revisionReason')),
        'Use the current report checks.',
      );
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, _label('confirm')));
      await tester.pumpAndSettle();
      final call = client.transitions.single;
      final payload = call['payload'] as Map;
      expect(call['operation'], 'adopt');
      expect(payload['source_job_id'], 'job-widget-only');
      expect(payload['options'], isNull);
      expect(payload['decision'], isNull);
      expect(payload['reason'], 'Use the current report checks.');
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('permission withdrawal clears loaded work and recent contents', (
    tester,
  ) async {
    final client = _BusinessClient();
    await _openWork(tester, client);
    expect(find.text(_question, findRichText: true), findsOneWidget);
    client.denyRead = true;
    await tester.tap(find.text(_label('refresh')));
    await tester.pumpAndSettle();
    expect(find.text(_question, findRichText: true), findsNothing);
    expect(find.text('Private proposal'), findsNothing);
    expect(find.text(_label('accessChanged')), findsOneWidget);
    expect(find.text(_label('saveResult')), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'explicit save confirms the exact request then reads saved work',
    (tester) async {
      final client = _BusinessClient();
      await _openWork(tester, client);
      await tester.tap(find.text(_label('saveResult')));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      expect(find.byType(AlertDialog), findsOneWidget);
      expect(client.saves, hasLength(1));
      expect(client.saves.single['confirmedResource'], isNull);
      expect(client.committedSaves, 0);
      await tester.tap(
        find.descendant(
          of: find.byType(AlertDialog),
          matching: find.widgetWithText(FilledButton, _label('saveResult')),
        ),
      );
      await tester.pumpAndSettle();
      expect(client.saves, hasLength(2));
      expect(client.saves.last['confirmedResource'], 'exact-reviewed-resource');
      expect(client.saves.last['requestId'], client.saves.first['requestId']);
      expect(client.saves.last['citations'], client.saves.first['citations']);
      expect(client.committedSaves, 1);
      expect(client.reads, 2);
      expect(find.text(_label('saved')), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('already saved exact revision does not create another version', (
    tester,
  ) async {
    final client = _BusinessClient()..markSaved();
    await _openWork(tester, client);
    await tester.tap(find.text(_label('saveResult')));
    await tester.pumpAndSettle();
    await tester.tap(find.text(_label('saveResult')));
    await tester.pumpAndSettle();
    expect(client.saves, isEmpty);
    expect(client.committedSaves, 0);
    expect(client.reads, 3);
    expect(client.savedReads, 2);
    expect(find.byType(AlertDialog), findsNothing);
    expect(find.text(_label('saved')), findsOneWidget);
  });

  for (final sharedDenied in [false, true]) {
    testWidgets(
      'saved revision rechecks ${sharedDenied ? 'Shared' : 'domain'} permission',
      (tester) async {
        final client = _BusinessClient()..markSaved();
        await _openWork(tester, client);
        if (sharedDenied) {
          client.denySavedRead = true;
        } else {
          client.denyRead = true;
        }
        await tester.tap(find.text(_label('saveResult')));
        await tester.pumpAndSettle();
        expect(client.saves, isEmpty);
        expect(client.committedSaves, 0);
        expect(find.text(_label('saved')), findsNothing);
        expect(find.text(_question, findRichText: true), findsNothing);
        expect(find.text('Private proposal'), findsNothing);
        expect(find.text(_label('accessChanged')), findsOneWidget);
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets('saved revision rejects an exact Artifact hash mismatch', (
    tester,
  ) async {
    final client = _BusinessClient()
      ..markSaved()
      ..alterSavedHash = true;
    await _openWork(tester, client);
    await tester.tap(find.text(_label('saveResult')));
    await tester.pumpAndSettle();
    expect(client.savedReads, 1);
    expect(client.saves, isEmpty);
    expect(find.text(_label('saved')), findsNothing);
    expect(find.text(_label('retryMessage')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'a newer business revision is not reported saved from stale state',
    (tester) async {
      final client = _BusinessClient()..markSaved();
      await _openWork(tester, client);
      client.work['revision'] = 'app_evidence_records:11';
      await tester.tap(find.text(_label('saveResult')));
      await tester.pumpAndSettle();
      expect(client.saves, isEmpty);
      expect(client.savedReads, 0);
      expect(find.text(_label('saved')), findsNothing);
      expect(find.text(_label('conflict')), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('unknown costs stay unavailable while a real zero is rendered', (
    tester,
  ) async {
    final client = _BusinessClient();
    client.work['state'] = 'OUTCOME_RECORDED';
    client.work['observation'] = {
      'window': {
        'start': '2026-10-10T00:00:00Z',
        'end': '2026-10-11T00:00:00Z',
      },
      'metrics': <Object>[],
      'cost_ledger': <Object>[],
      'limits': 'No payment or refund evidence supplied.',
      'adoption_lineage': {'prior_revision': 'app_evidence_records:9'},
      'cost_totals': {
        'CNY': {
          'ESTIMATE': '0',
          'COMMITTED': '10',
          'ACTUAL': null,
          'REFUND': null,
          'net_actual': null,
        },
      },
    };
    await _openWork(tester, client);
    await tester.tap(find.text(_label('execution')));
    await tester.pumpAndSettle();
    expect(find.text('—'), findsAtLeastNWidgets(3));
    expect(find.text('0'), findsOneWidget);
    expect(find.text('10'), findsOneWidget);
    expect(
      find.text('${_label('historical')} · ${_label('observation')}'),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'retry of an uncertain transition retains its submission identity',
    (tester) async {
      final client = _BusinessClient()..failNextTransition = true;
      client.work['state'] = 'INTERRUPTED';
      await _openWork(tester, client);
      await tester.tap(find.text(_label('resume')));
      await tester.pumpAndSettle();
      expect(find.text(_label('retryMessage')), findsOneWidget);
      await tester.tap(find.text(_label('resume')));
      await tester.pumpAndSettle();
      expect(client.transitions, hasLength(2));
      expect(
        client.transitions.last['submissionId'],
        client.transitions.first['submissionId'],
      );
      expect(client.transitions.last['revision'], _revision);
      expect(client.transitions.last['payload'], isEmpty);
      expect(find.text(_label('decided')), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
}

void _decisionDateTests() {
  for (final invalid in [
    '',
    'not a date',
    '2026-02-31T11:00:00+08:00',
    '2026-10-25T11:00:00',
    'append-to-default',
  ]) {
    testWidgets(
      'review time rejects "$invalid" without falling back, preserving the entered correction',
      (tester) async {
        final client = _BusinessClient();
        client.work['state'] = 'PREPARED';
        await _openWork(tester, client);
        await tester.tap(find.text(_label('decide')));
        await tester.pumpAndSettle();
        Finder field(String label) => find.descendant(
          of: find.byType(AlertDialog),
          matching: find.byWidgetPredicate(
            (widget) =>
                widget is TextField && widget.decoration?.labelText == label,
          ),
        );
        await tester.enterText(
          field(_label('reason')),
          'Review the original material.',
        );
        await tester.enterText(field(_label('owner')), 'Declared operator');
        final date = field(_label('reviewAt'));
        final original = tester.widget<TextField>(date);
        expect(original.readOnly, isFalse);
        const intended = '2026-10-25T11:00:00+08:00';
        final entered = invalid == 'append-to-default'
            ? '${original.controller!.text}$intended'
            : invalid;
        await tester.enterText(date, entered);
        await tester.pump();
        expect(find.text(_label('dateInvalid')), findsOneWidget);
        final confirm = find.widgetWithText(FilledButton, _label('confirm'));
        expect(tester.widget<FilledButton>(confirm).onPressed, isNull);
        expect(client.transitions, isEmpty);
        expect(tester.widget<TextField>(date).controller!.text, entered);
        expect(find.byType(AlertDialog), findsOneWidget);
        await tester.enterText(date, intended);
        await tester.pump();
        expect(find.text(_label('dateInvalid')), findsNothing);
        await tester.tap(confirm);
        await tester.pumpAndSettle();
        expect(client.transitions, hasLength(1));
        final payload =
            client.transitions.single['payload'] as Map<String, dynamic>;
        expect(payload['review_at'], '2026-10-25T03:00:00.000Z');
        expect(find.byType(AlertDialog), findsNothing);
        expect(tester.takeException(), isNull);
      },
    );
  }
}

Finder _decisionField(String label) => find.descendant(
  of: find.byType(AlertDialog),
  matching: find.byWidgetPredicate(
    (widget) => widget is TextField && widget.decoration?.labelText == label,
  ),
);

Future<void> _openDecisionEdit(WidgetTester tester) async {
  final edit = find.byKey(const ValueKey('business/edit-decision'));
  await tester.ensureVisible(edit);
  await tester.tap(edit);
  await tester.pumpAndSettle();
}

Future<void> _fillDecisionEdit(
  WidgetTester tester, {
  String date = '2026-10-25T11:00:00+08:00',
}) async {
  for (final item in {
    _label('reason'): 'Corrected decision reason.',
    _label('owner'): 'Corrected responsible person',
    _label('reviewAt'): date,
    _label('revisionReason'):
        'Correct the review date without changing the plan.',
  }.entries) {
    await tester.ensureVisible(_decisionField(item.key));
    await tester.enterText(_decisionField(item.key), item.value);
  }
  await tester.pump();
}

void _decisionEditTests() {
  testWidgets(
    'decision revision preserves original options resources and saved Artifact history',
    (tester) async {
      final client = _BusinessClient()..markSaved();
      final oldDecision = Map<String, dynamic>.from(
        client.work['decision'] as Map,
      );
      client.work['decision'] = oldDecision;
      oldDecision['resource_constraints'] = {
        'budget_amount': '1000',
        'estimated_cost_amount': '250',
        'currency': 'CNY',
        'as_of': '2026-10-24T00:00:00Z',
        'limits': 'Declared resource scope.',
      };
      final before = _clone(client.work);
      await _openWork(tester, client);
      await tester.tap(find.text(_label('saveResult')));
      await tester.pumpAndSettle();
      expect(find.text(_label('saved')), findsOneWidget);
      await _openDecisionEdit(tester);
      expect(
        tester
            .widget<TextField>(_decisionField(_label('reviewAt')))
            .controller!
            .text,
        oldDecision['review_at'],
      );
      await _fillDecisionEdit(tester);
      final confirm = find.widgetWithText(FilledButton, _label('confirm'));
      await tester.ensureVisible(confirm);
      await tester.tap(confirm);
      await tester.pumpAndSettle();
      final call = client.transitions.single;
      final payload = call['payload'] as Map;
      final decision = payload['decision'] as Map;
      expect(call['operation'], 'adopt');
      expect(call['revision'], _revision);
      expect(payload['source_job_id'], 'job-widget-only');
      expect(payload['question'], before['question']);
      expect(payload['options'], before['options']);
      expect(
        payload['reason'],
        'Correct the review date without changing the plan.',
      );
      expect(decision['option_id'], oldDecision['option_id']);
      expect(decision['reason'], 'Corrected decision reason.');
      expect(decision['owner'], 'Corrected responsible person');
      expect(decision['review_at'], '2026-10-25T03:00:00.000Z');
      expect(
        decision['resource_constraints'],
        oldDecision['resource_constraints'],
      );
      expect(oldDecision, before['decision']);
      expect(client.work['saved_results'], before['saved_results']);
      expect(find.text(_label('saved')), findsNothing);
      expect(find.text('Corrected responsible person'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  for (final invalid in [
    '',
    '2026-02-31T11:00:00+08:00',
    '2026-10-25T11:00:00',
  ]) {
    testWidgets(
      'existing decision rejects invalid edited review time "$invalid"',
      (tester) async {
        final client = _BusinessClient();
        await _openWork(tester, client);
        await _openDecisionEdit(tester);
        await _fillDecisionEdit(tester, date: invalid);
        final confirm = find.widgetWithText(FilledButton, _label('confirm'));
        expect(tester.widget<FilledButton>(confirm).onPressed, isNull);
        expect(find.text(_label('dateInvalid')), findsOneWidget);
        expect(client.transitions, isEmpty);
        expect(
          tester
              .widget<TextField>(_decisionField(_label('reviewAt')))
              .controller!
              .text,
          invalid,
        );
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets(
    'decision conflict retains the correction and never reports it saved',
    (tester) async {
      final client = _BusinessClient()
        ..transitionError = const LumenisCoreException(
          'Concurrent revision',
          statusCode: 409,
        );
      final original = _clone(client.work);
      await _openWork(tester, client);
      await _openDecisionEdit(tester);
      await _fillDecisionEdit(tester);
      await tester.tap(find.widgetWithText(FilledButton, _label('confirm')));
      await tester.pumpAndSettle();
      expect(find.text(_label('conflict')), findsOneWidget);
      expect(client.work, original);
      expect(find.text(_label('saved')), findsNothing);
      await _openDecisionEdit(tester);
      expect(
        tester
            .widget<TextField>(_decisionField(_label('owner')))
            .controller!
            .text,
        'Corrected responsible person',
      );
      expect(
        tester
            .widget<TextField>(_decisionField(_label('reviewAt')))
            .controller!
            .text,
        '2026-10-25T03:00:00.000Z',
      );
      expect(client.transitions, hasLength(1));
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'decision editing obeys withdrawal and historical read-only state',
    (tester) async {
      final client = _BusinessClient()
        ..transitionError = const LumenisCoreException(
          'Withdrawn',
          statusCode: 403,
        );
      await _openWork(tester, client);
      await _openDecisionEdit(tester);
      await _fillDecisionEdit(tester);
      await tester.tap(find.widgetWithText(FilledButton, _label('confirm')));
      await tester.pumpAndSettle();
      expect(find.text(_label('accessChanged')), findsOneWidget);
      expect(
        find.byKey(const ValueKey('business/edit-decision')),
        findsNothing,
      );
      expect(find.text(_question), findsNothing);
      await tester.pumpWidget(const SizedBox.shrink());
      final historical = _BusinessClient();
      historical.work['is_current_revision'] = false;
      await _openWork(tester, historical);
      expect(
        tester
            .widget<OutlinedButton>(
              find.byKey(const ValueKey('business/edit-decision')),
            )
            .onPressed,
        isNull,
      );
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'source rail opens freshly authorized quoted text and rejects withdrawal',
    (tester) async {
      final client = _BusinessClient();
      await _openWork(tester, client);
      final source = find.byKey(
        const ValueKey('business/source/source-widget-only'),
      );
      await tester.tap(source);
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey('business-source-excerpt')),
        findsOneWidget,
      );
      expect(client.reads, 2);
      await tester.tap(find.widgetWithText(TextButton, _label('close')));
      await tester.pumpAndSettle();
      client.denyRead = true;
      await tester.tap(source);
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey('business-source-excerpt')),
        findsNothing,
      );
      expect(find.text('Private proposal'), findsNothing);
      expect(find.text(_label('accessChanged')), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'three panes keep the decision fixed and reflow for narrow or enlarged text',
    (tester) async {
      for (final locale in LumenisLocalizations.supportedLocales) {
        for (final (width, scale, wide) in [
          (1440.0, 1.0, true),
          (960.0, 1.0, true),
          (960.0, 1.25, false),
          (1280.0, 1.25, true),
          (390.0, 1.0, false),
          (390.0, 2.0, false),
          (1440.0, 2.0, false),
        ]) {
          await tester.pumpWidget(const SizedBox.shrink());
          await _openWork(
            tester,
            _BusinessClient()..addReport(),
            locale: locale,
            surface: Size(width, 1100),
            textScale: scale,
          );
          final main = find.byKey(const ValueKey('business/comparison-paper'));
          final edit = find.byKey(const ValueKey('business/edit-decision'));
          if (wide) {
            final source = find.byKey(const ValueKey('business/source-rail'));
            final decision = find.byKey(
              const ValueKey('business/decision-rail'),
            );
            expect(
              tester.getRect(source).right,
              lessThan(tester.getRect(main).left),
            );
            expect(
              tester.getRect(main).right,
              lessThan(tester.getRect(decision).left),
            );
            final position = tester.getTopLeft(edit);
            await tester.drag(
              find.byKey(const ValueKey('business/main-scroll')),
              const Offset(0, -500),
            );
            await tester.pumpAndSettle();
            expect(tester.getTopLeft(edit), position);
          } else {
            expect(
              find.byKey(const ValueKey('business/decision-rail')),
              findsNothing,
            );
            final mainScroll = find
                .descendant(
                  of: find.byKey(const ValueKey('business/main-scroll')),
                  matching: find.byType(Scrollable),
                )
                .first;
            await tester.scrollUntilVisible(
              find.byKey(const ValueKey('business/source-fold')),
              160,
              scrollable: mainScroll,
            );
            expect(
              find.byKey(const ValueKey('business/source-fold')),
              findsOneWidget,
            );
            await tester.scrollUntilVisible(edit, -160, scrollable: mainScroll);
          }
          expect(edit, findsOneWidget);
          expect(
            tester.takeException(),
            isNull,
            reason: '${locale.languageCode} / $width / $scale',
          );
        }
      }
    },
  );

  testWidgets(
    '1280 by 720 workspace shows sources options and decision in the first viewport',
    (tester) async {
      for (final locale in LumenisLocalizations.supportedLocales) {
        for (final scale in [1.0, 1.25, 2.0]) {
          await tester.pumpWidget(const SizedBox.shrink());
          await _openWork(
            tester,
            _BusinessClient()..addReport(),
            locale: locale,
            surface: const Size(1280, 720),
            textScale: scale,
            withWorkspaceShell: true,
          );
          final source = find.byKey(const ValueKey('business/source-rail'));
          final paper = find.byKey(const ValueKey('business/comparison-paper'));
          final decision = find.byKey(const ValueKey('business/decision-rail'));
          final edit = find.byKey(const ValueKey('business/edit-decision'));
          if (scale == 1) {
            expect(tester.getSize(find.byType(BusinessWorkPanel)).width, 1029);
            final sourceRect = tester.getRect(source);
            final paperRect = tester.getRect(paper);
            final decisionRect = tester.getRect(decision);
            expect(sourceRect.left, greaterThanOrEqualTo(237));
            expect(sourceRect.right, lessThan(paperRect.left));
            expect(paperRect.width, greaterThanOrEqualTo(380));
            expect(paperRect.right, lessThan(decisionRect.left));
            expect(decisionRect.right, lessThanOrEqualTo(1280));
            for (final rect in [sourceRect, paperRect, decisionRect]) {
              expect(rect.top, greaterThanOrEqualTo(72));
              expect(rect.bottom, lessThanOrEqualTo(720));
            }
            expect(
              find.text('Approved original').hitTestable(),
              findsOneWidget,
            );
            expect(find.text('Private proposal').hitTestable(), findsOneWidget);
            expect(edit.hitTestable(), findsOneWidget);
            final position = tester.getTopLeft(edit);
            await tester.drag(
              find.byKey(const ValueKey('business/main-scroll')),
              const Offset(0, -400),
            );
            await tester.pumpAndSettle();
            expect(tester.getTopLeft(edit), position);
          } else {
            expect(source, findsNothing);
            expect(decision, findsNothing);
            final mainScroll = find
                .descendant(
                  of: find.byKey(const ValueKey('business/main-scroll')),
                  matching: find.byType(Scrollable),
                )
                .first;
            await tester.scrollUntilVisible(edit, 160, scrollable: mainScroll);
            await tester.pumpAndSettle();
            expect(edit.hitTestable(), findsOneWidget);
            await tester.scrollUntilVisible(
              find.text('Private proposal'),
              160,
              scrollable: mainScroll,
            );
            await tester.pumpAndSettle();
            expect(find.text('Private proposal').hitTestable(), findsOneWidget);
          }
          expect(
            tester.takeException(),
            isNull,
            reason: '${locale.languageCode} / 1280 x 720 / $scale',
          );
        }
      }
    },
  );
}

void _internalCreationTests() {
  for (final locale in LumenisLocalizations.supportedLocales) {
    final title = switch (locale.languageCode) {
      'zh' => '内部制作成果',
      'ko' => '제작 자료',
      _ => 'Created material',
    };
    for (final fresh in [true, false]) {
      final status = switch ((locale.languageCode, fresh)) {
        ('zh', true) => '本次已复查制作成果',
        ('zh', false) => '历史制作记录，尚未重新核验',
        ('ko', true) => '이번에 제작 자료를 다시 확인했습니다',
        ('ko', false) => '이전 제작 기록이며 재확인 전입니다',
        (_, true) => 'Created material rechecked now',
        _ => 'Historical creation record; not rechecked',
      };
      testWidgets(
        'internal material status remains distinct in ${locale.languageCode}, fresh=$fresh',
        (tester) async {
          await _openWork(
            tester,
            _BusinessClient()..markInternal(fresh: fresh),
            locale: locale,
          );
          final labels = LumenisLocalizations(locale);
          await tester.tap(find.text(labels.text('business.work.execution')));
          await tester.pumpAndSettle();
          expect(find.text('$title · v1'), findsOneWidget);
          expect(find.text(status), findsOneWidget);
          expect(
            find.text(labels.text('business.work.noExecution')),
            findsNothing,
          );
          expect(find.textContaining(_internalTask), findsNothing);
          expect(find.textContaining(_internalArtifact), findsNothing);
          expect(find.textContaining('a' * 64), findsNothing);
          expect(tester.takeException(), isNull);
        },
      );
    }
  }

  testWidgets(
    'internal material opens the exact saved result through both read owners',
    (tester) async {
      final client = _BusinessClient()..markInternal();
      await _openWork(tester, client);
      await tester.tap(find.text(_label('execution')));
      await tester.pumpAndSettle();
      expect(
        find.text(
          'Creation does not confirm external action or business results.',
        ),
        findsOneWidget,
      );
      await tester.tap(find.text('Open created material'));
      await tester.pumpAndSettle();
      expect(client.readRevisions.last, _revision);
      expect(client.savedArtifactIds, [_internalArtifact]);
      expect(find.byType(AlertDialog), findsOneWidget);
      expect(find.text(_internalTitle), findsOneWidget);
      expect(find.text(_internalBody), findsOneWidget);
      expect(find.textContaining(_internalTask), findsNothing);
      expect(find.textContaining('a' * 64), findsNothing);
      await tester.tap(
        find.descendant(
          of: find.byType(AlertDialog),
          matching: find.widgetWithText(TextButton, _label('close')),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.byType(AlertDialog), findsNothing);
      expect(find.text('Created material rechecked now'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  for (final sharedDenied in [false, true]) {
    testWidgets(
      'internal material opening rechecks ${sharedDenied ? 'Shared' : 'domain'} permission',
      (tester) async {
        final client = _BusinessClient()..markInternal();
        await _openWork(tester, client);
        await tester.tap(find.text(_label('execution')));
        await tester.pumpAndSettle();
        if (sharedDenied) {
          client.denySavedRead = true;
        } else {
          client.denyRead = true;
        }
        await tester.tap(find.text('Open created material'));
        await tester.pumpAndSettle();
        expect(find.byType(AlertDialog), findsNothing);
        expect(find.text(_internalBody), findsNothing);
        expect(find.text('Created material · v1'), findsNothing);
        expect(find.text(_label('accessChanged')), findsOneWidget);
        expect(client.savedArtifactIds.length, sharedDenied ? 1 : 0);
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets(
    'changed saved material identity never opens unverified content',
    (tester) async {
      final client = _BusinessClient()
        ..markInternal()
        ..alterSavedHash = true;
      await _openWork(tester, client);
      await tester.tap(find.text(_label('execution')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Open created material'));
      await tester.pumpAndSettle();
      expect(client.savedReads, 1);
      expect(find.byType(AlertDialog), findsNothing);
      expect(find.text(_internalBody), findsNothing);
      expect(find.text(_label('retryMessage')), findsOneWidget);
    },
  );

  testWidgets(
    'a changed creation receipt cannot open a different saved material',
    (tester) async {
      final client = _BusinessClient()..markInternal();
      await _openWork(tester, client);
      await tester.tap(find.text(_label('execution')));
      await tester.pumpAndSettle();
      final action = client.work['action'] as Map<String, dynamic>;
      (action['receipt'] as Map<String, dynamic>)['sha256'] = 'd' * 64;
      await tester.tap(find.text('Open created material'));
      await tester.pumpAndSettle();
      expect(client.savedReads, 0);
      expect(find.byType(AlertDialog), findsNothing);
      expect(find.text(_label('conflict')), findsOneWidget);
    },
  );

  testWidgets('empty execution still shows its original empty state', (
    tester,
  ) async {
    await _openWork(tester, _BusinessClient());
    await tester.tap(find.text(_label('execution')));
    await tester.pumpAndSettle();
    expect(find.text(_label('noExecution')), findsOneWidget);
    expect(find.text('Open created material'), findsNothing);
  });
}

void _questionPresentationTests() {
  testWidgets(
    'long operating question leaves the first proposal visible and expands to its exact original',
    (tester) async {
      for (final locale in LumenisLocalizations.supportedLocales) {
        await tester.pumpWidget(const SizedBox.shrink());
        final client = _BusinessClient();
        final question = List.filled(
          10,
          'Review the original source and preserve unresolved claims.',
        ).join(' ');
        client.work['question'] = question;
        await _openWork(
          tester,
          client,
          locale: locale,
          surface: const Size(1280, 720),
          withWorkspaceShell: true,
        );
        final summary = find.byKey(const ValueKey('business/question-summary'));
        expect(tester.widget<Text>(summary).maxLines, 2);
        expect(find.text('Private proposal').hitTestable(), findsOneWidget);
        final toggle = find.byKey(const ValueKey('business/question-toggle'));
        await tester.tap(toggle);
        await tester.pumpAndSettle();
        expect(
          tester
              .widget<SelectableText>(
                find.byKey(const ValueKey('business/full-question')),
              )
              .data,
          question,
        );
        await tester.tap(toggle);
        await tester.pumpAndSettle();
        expect(summary, findsOneWidget);
        expect(client.work['question'], question);
        expect(client.transitions, isEmpty);
        expect(client.saves, isEmpty);
        expect(tester.takeException(), isNull);
      }
    },
  );
}

void _savedExportTests() {
  testWidgets(
    'saved business export keeps the exact old or current version and domain',
    (tester) async {
      for (final domain in ['CTH', 'BMP']) {
        for (final version in [1, 2]) {
          await tester.pumpWidget(const SizedBox.shrink());
          final client = _BusinessClient()..markSaved();
          client.context['product_id'] = domain;
          client.work['revision'] = 'app_evidence_records:11';
          final results = client.work['saved_results'] as Map;
          final rows = results['items'] as List;
          final second = {
            'artifact_id': _secondArtifact,
            'sha256': 'd' * 64,
            'version': 2,
            'title': 'Saved operations result',
            'draft_digest': 'e' * 64,
            'business_revision': 'app_evidence_records:11',
          };
          rows.add(second);
          results['latest'] = second;
          final files = _ExportFiles();
          final artifact = version == 1 ? _artifact : _secondArtifact;
          await _openExportPicker(
            tester,
            client,
            files,
            domainId: domain,
            artifactId: artifact,
          );
          expect(
            tester
                .widget<ChoiceChip>(
                  find.byKey(
                    const ValueKey('business/export-purpose/delivery'),
                  ),
                )
                .selected,
            isTrue,
          );
          if (version == 2) {
            await tester.tap(
              find.byKey(
                const ValueKey('business/export-purpose/audit_snapshot'),
              ),
            );
            await tester.pumpAndSettle();
          }
          await tester.tap(
            find.byKey(const ValueKey('business/export-format/docx')),
          );
          await tester.pumpAndSettle();
          expect(client.exports.single, {
            'domainId': domain,
            'artifactId': artifact,
            'format': 'docx',
            'purpose': version == 1 ? 'delivery' : 'audit_snapshot',
          });
          expect(client.savedArtifactIds, [artifact, artifact]);
          expect(files.contents, hasLength(1));
          expect(
            utf8.decode(files.contents.single.bytes),
            'Exported $artifact',
          );
          expect(
            files.names.single,
            'oevira-${domain == 'CTH' ? 'operations' : 'brand-market'}-v$version.docx',
          );
          expect(
            find.text('The file was saved to the selected location.'),
            findsOneWidget,
          );
          expect(client.saves, isEmpty);
          expect(client.transitions, isEmpty);
          expect(find.byType(AlertDialog), findsNothing);
          expect(tester.takeException(), isNull);
        }
      }
    },
  );

  testWidgets(
    'export picker preserves all formats in narrow and enlarged three locale layouts',
    (tester) async {
      for (final locale in LumenisLocalizations.supportedLocales) {
        for (final scale in [1.0, 2.0]) {
          await tester.pumpWidget(const SizedBox.shrink());
          final client = _BusinessClient()..markSaved();
          final files = _ExportFiles();
          await _openExportPicker(
            tester,
            client,
            files,
            locale: locale,
            surface: const Size(390, 720),
            textScale: scale,
          );
          for (final format in ['docx', 'pdf', 'md', 'txt', 'xlsx', 'pptx']) {
            expect(
              find.byKey(ValueKey('business/export-format/$format')),
              findsOneWidget,
            );
          }
          final cancel = find.widgetWithText(
            TextButton,
            LumenisLocalizations(locale).text('business.work.cancel'),
          );
          await tester.ensureVisible(cancel);
          await tester.tap(cancel);
          await tester.pumpAndSettle();
          expect(client.exports, isEmpty);
          expect(files.contents, isEmpty);
          if (scale == 2) {
            final save = find.widgetWithText(
              FilledButton,
              LumenisLocalizations(locale).text('business.work.saveResult'),
            );
            await tester.scrollUntilVisible(
              save,
              160,
              scrollable: find
                  .descendant(
                    of: find.byKey(const ValueKey('business/main-scroll')),
                    matching: find.byType(Scrollable),
                  )
                  .first,
            );
            await tester.pumpAndSettle();
            expect(save.hitTestable(), findsOneWidget);
          }
          expect(tester.takeException(), isNull);
        }
      }
    },
  );

  testWidgets(
    'cancelling the file destination or a file save failure never confirms export',
    (tester) async {
      for (final fail in [false, true]) {
        await tester.pumpWidget(const SizedBox.shrink());
        final client = _BusinessClient()..markSaved();
        final files = _ExportFiles()
          ..saveResult = false
          ..failSave = fail;
        await _openExportPicker(tester, client, files);
        await tester.tap(
          find.byKey(const ValueKey('business/export-format/pdf')),
        );
        await tester.pumpAndSettle();
        expect(client.exports, hasLength(1));
        expect(files.contents, hasLength(1));
        expect(
          find.text('The file was saved to the selected location.'),
          findsNothing,
        );
        expect(
          find.text('The file was handed to the browser. Check Downloads.'),
          findsNothing,
        );
        expect(find.byType(SnackBar), findsNothing);
        expect(
          find.text('Export did not complete. Please retry.'),
          fail ? findsOneWidget : findsNothing,
        );
        expect(tester.takeException(), isNull);
      }
    },
  );

  testWidgets(
    'a changed report digest or withdrawn source blocks export before the file destination',
    (tester) async {
      for (final denied in [false, true]) {
        await tester.pumpWidget(const SizedBox.shrink());
        final client = _BusinessClient()..markSaved();
        final files = _ExportFiles();
        await _openExportPicker(tester, client, files);
        client.alterSavedHash = !denied;
        client.denySavedRead = denied;
        await tester.tap(
          find.byKey(const ValueKey('business/export-format/docx')),
        );
        await tester.pumpAndSettle();
        expect(client.exports, isEmpty);
        expect(files.contents, isEmpty);
        expect(find.byType(SnackBar), findsNothing);
        expect(
          find.text(
            denied
                ? _label('accessChanged')
                : 'Export did not complete. Please retry.',
          ),
          findsOneWidget,
        );
        if (denied) expect(find.text('Private proposal'), findsNothing);
        expect(tester.takeException(), isNull);
      }
    },
  );

  testWidgets(
    'denied or empty export bytes cannot reach the file destination',
    (tester) async {
      for (final denied in [false, true]) {
        await tester.pumpWidget(const SizedBox.shrink());
        final client = _BusinessClient()..markSaved();
        final files = _ExportFiles();
        await _openExportPicker(tester, client, files);
        client.emptyExport = !denied;
        if (denied) {
          client.exportError = const LumenisCoreException(
            'Access changed',
            statusCode: 403,
          );
        }
        await tester.tap(
          find.byKey(const ValueKey('business/export-format/docx')),
        );
        await tester.pumpAndSettle();
        expect(client.exports, hasLength(1));
        expect(files.contents, isEmpty);
        expect(find.byType(SnackBar), findsNothing);
        if (denied) expect(find.text('Private proposal'), findsNothing);
        expect(tester.takeException(), isNull);
      }
    },
  );

  testWidgets(
    'scope change while choosing a format cancels the original export',
    (tester) async {
      final client = _BusinessClient()..markSaved();
      final files = _ExportFiles();
      await _openExportPicker(tester, client, files);
      client.context = {
        'product_id': 'CTH',
        'subject_id': 'different-focus',
        'global': false,
      };
      await tester.tap(
        find.byKey(const ValueKey('business/export-format/docx')),
      );
      await tester.pumpAndSettle();
      expect(client.exports, isEmpty);
      expect(files.contents, isEmpty);
      expect(find.byType(SnackBar), findsNothing);
      expect(find.text(_label('contextChanged')), findsOneWidget);
      expect(find.text('Private proposal'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'scope change while bytes are pending discards the original export',
    (tester) async {
      final client = _BusinessClient()..markSaved();
      final files = _ExportFiles();
      await _openExportPicker(tester, client, files);
      client.pendingExport = Completer<SavedWorkExportFile>();
      await tester.tap(
        find.byKey(const ValueKey('business/export-format/docx')),
      );
      await tester.pump();
      expect(client.exports, hasLength(1));
      client.context = {
        'product_id': 'BMP',
        'subject_id': 'different-focus',
        'global': false,
      };
      client.pendingExport!.complete(
        SavedWorkExportFile(
          bytes: Uint8List.fromList([1, 2, 3]),
          filename: 'report.docx',
          mediaType: 'application/octet-stream',
        ),
      );
      await tester.pumpAndSettle();
      expect(files.contents, isEmpty);
      expect(find.byType(SnackBar), findsNothing);
      expect(find.text(_label('contextChanged')), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
}

Future<void> _openExportPicker(
  WidgetTester tester,
  _BusinessClient client,
  _ExportFiles files, {
  String domainId = 'CTH',
  String artifactId = _artifact,
  Locale locale = const Locale('en'),
  Size surface = const Size(1400, 1100),
  double textScale = 1,
}) async {
  await _openWork(
    tester,
    client,
    domainId: domainId,
    exportFiles: files,
    locale: locale,
    surface: surface,
    textScale: textScale,
  );
  await tester.tap(
    find.text(LumenisLocalizations(locale).text('business.work.versions')),
  );
  await tester.pumpAndSettle();
  final row = find.byKey(ValueKey('business/saved-version/$artifactId'));
  final open = find.descendant(of: row, matching: find.byType(TextButton));
  await tester.scrollUntilVisible(
    open,
    160,
    scrollable: find
        .descendant(
          of: find.byKey(const ValueKey('business/main-scroll')),
          matching: find.byType(Scrollable),
        )
        .first,
  );
  await tester.pumpAndSettle();
  expect(
    open.hitTestable(),
    findsOneWidget,
    reason:
        '${locale.languageCode} / $surface / $textScale: ${tester.getRect(open)}',
  );
  await tester.tap(open);
  await tester.pumpAndSettle();
  final export = find.byKey(const ValueKey('business/export-saved-version'));
  await tester.ensureVisible(export);
  await tester.tap(export);
  await tester.pumpAndSettle();
}

class _ExportFiles extends Sh04ExportFiles {
  final contents = <SavedWorkExportFile>[];
  final names = <String>[];
  bool saveResult = true;
  bool failSave = false;

  @override
  bool get canSaveFile => true;

  @override
  Future<bool> save(
    SavedWorkExportFile content, {
    required String suggestedName,
  }) async {
    contents.add(content);
    names.add(suggestedName);
    if (failSave) throw const FormatException('The file could not be saved.');
    return saveResult;
  }
}

Future<void> _openWork(
  WidgetTester tester,
  _BusinessClient client, {
  Locale locale = const Locale('en'),
  Size surface = const Size(1400, 1100),
  double textScale = 1,
  bool withWorkspaceShell = false,
  String domainId = 'CTH',
  Sh04ExportFiles? exportFiles,
}) async {
  tester.view.physicalSize = surface;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  final panel = BusinessWorkPanel(
    client: client,
    domainId: domainId,
    exportFiles: exportFiles,
    onReturn: () {},
  );
  await tester.pumpWidget(
    MaterialApp(
      locale: locale,
      theme: LumenisTheme.dark,
      builder: (context, child) => MediaQuery(
        data: MediaQuery.of(
          context,
        ).copyWith(textScaler: TextScaler.linear(textScale)),
        child: child!,
      ),
      supportedLocales: LumenisLocalizations.supportedLocales,
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        LumenisLocalizations.delegate,
      ],
      home: Scaffold(
        // Match the existing wide workspace's navigation, divider, header and
        // stage insets without making the client fixture implement shell APIs.
        body: withWorkspaceShell
            ? Row(
                children: [
                  const SizedBox(width: 224),
                  const VerticalDivider(width: 1),
                  Expanded(
                    child: Column(
                      children: [
                        const SizedBox(height: 72),
                        Expanded(
                          child: Padding(
                            padding: const EdgeInsets.fromLTRB(12, 0, 14, 14),
                            child: panel,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              )
            : panel,
      ),
    ),
  );
  await tester.pumpAndSettle();
  await tester.tap(find.text(_question));
  await tester.pumpAndSettle();
}

Map<String, dynamic> _envelope(Object result) => {'ok': true, 'result': result};
Map<String, dynamic> _clone(Map<String, dynamic> value) =>
    jsonDecode(jsonEncode(value)) as Map<String, dynamic>;

class _BusinessClient extends LumenisCoreClient {
  Map<String, dynamic> context = {
    'product_id': 'CTH',
    'subject_id': 'subject-widget-only',
    'global': false,
  };
  final work = <String, dynamic>{
    'work_id': _workId,
    'revision': _revision,
    'is_current_revision': true,
    'state': 'DECIDED',
    'question': _question,
    'options': [
      {
        'option_id': 'A',
        'proposal': 'Private proposal',
        'rationale': 'Declared source-bounded reasoning.',
        'check': 'Review actual observations.',
        'unknowns': ['Actual consumer effects remain unknown.'],
        'source_ids': ['source-widget-only'],
        'assumptions': ['Declared operating scope.'],
      },
    ],
    'decision': {
      'option_id': 'A',
      'reason': 'Bounded internal selection.',
      'owner': 'Declared operator',
      'review_at': '2026-10-24T12:00:00Z',
    },
    'source_report': {'job_id': 'job-widget-only'},
    'citation_candidates': {
      'save_limit_state': 'WITHIN_SHARED_CITATION_LIMIT',
      'items': [
        {
          'title': 'Approved original',
          'source_job_id': 'job-widget-only',
          'source_id': 'source-widget-only',
          'citation': {
            'evidence_id': 7,
            'start': 0,
            'end': 8,
            'quote': 'Approved',
          },
        },
      ],
    },
    'saved_results': {'items': <Object>[], 'latest': null},
    'timeline': <Object>[],
  };
  bool denyRead = false;
  bool denySavedRead = false;
  bool alterSavedHash = false;
  bool failNextTransition = false;
  LumenisCoreException? transitionError;
  int reads = 0;
  int savedReads = 0;
  int committedSaves = 0;
  final readRevisions = <String?>[];
  final savedArtifactIds = <String>[];
  final saves = <Map<String, Object?>>[];
  final transitions = <Map<String, Object?>>[];
  final exports = <Map<String, Object?>>[];
  LumenisCoreException? exportError;
  bool emptyExport = false;
  Completer<SavedWorkExportFile>? pendingExport;

  void markInternal({bool fresh = true}) {
    work['state'] = 'ACTION_RECORDED';
    work['action_read'] = {
      'state': fresh ? 'FRESH_OWNER_VERIFIED' : 'UNAVAILABLE',
    };
    work['action'] = {
      'option_id': 'A',
      'receipt': {
        'owner': 'Shared ContentCreation/TaskEngine/SavedWork',
        'action_kind': 'INTERNAL_TEXT_CREATION',
        'execution_state': 'ARTIFACT_COMMITTED',
        'external_effect': 'NOT_PERFORMED',
        'business_outcome': 'NOT_OBSERVED',
        'artifact_id': _internalArtifact,
        'sha256': 'a' * 64,
        'work_id': _internalWork,
        'task_id': _internalTask,
        'version': 1,
        'parent_artifact_id': null,
        'parent_sha256': null,
        'output': {
          'artifact_id': 'ART-2222222222222222',
          'sha256': 'b' * 64,
          'name': 'material.docx',
          'media_type':
              'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          'size_bytes': 432,
        },
      },
    };
  }

  void addReport() {
    work['domain_analysis'] = {
      'question_result': {
        'business_report': {
          'answers': [
            {
              'goal': 'REPORT_QUANTITIES',
              'summary': 'Report states 103 posts and 205 comments.',
              'limitations': ['A report is not native observation.'],
              'next_action': 'Reconcile the stated denominator.',
            },
            {
              'goal': 'SOURCE_REVIEW',
              'summary':
                  'Review VENUE_OPERATOR_DISCLOSURE with SRC-internal-report.',
              'limitations': ['Source statement only.'],
              'next_action': 'Check the original material.',
            },
          ],
          'document_reviews': [
            {
              'title': 'Permitted report',
              'method': 'deterministic_explicit_report_groups/1',
              'declared_counts': [
                {'value': '103', 'unit': 'posts'},
                {'value': '205', 'unit': 'comments'},
              ],
              'checks': [
                {
                  'title': 'Time groups',
                  'summary': '12 + 41 + 20 = 73; reported total 103.',
                  'limitation': 'Scope alignment remains unverified.',
                  'next_action': 'Check the original records.',
                  'reference': <String, dynamic>{},
                  'members': <Object>[],
                },
              ],
              'scope_notes': <Object>[],
            },
          ],
          'canonical_inputs': [
            {'source_id': 'SRC-internal-report'},
          ],
        },
      },
    };
  }

  @override
  Map<String, dynamic> get currentContextEnvelope => context;

  @override
  Future<Map<String, dynamic>> listBusinessWork(String domainId) async =>
      _envelope({
        'items': [
          {
            'work_id': _workId,
            'question': _question,
            'availability': 'AVAILABLE',
            'state': work['state'],
          },
        ],
      });

  @override
  Future<Map<String, dynamic>> readBusinessWork({
    required String domainId,
    required String workId,
    String? revision,
  }) async {
    reads += 1;
    readRevisions.add(revision);
    if (denyRead) {
      throw const LumenisCoreException(
        'Scope withdrawn',
        statusCode: 403,
        errorCode: 'BUSINESS_WORK_CONTEXT_CHANGED',
      );
    }
    return _envelope(_clone(work));
  }

  void markSaved() {
    final latest = {
      'artifact_id': _artifact,
      'sha256': 'a' * 64,
      'version': 1,
      'title': 'Saved operations result',
      'draft_digest': 'b' * 64,
      'business_revision': _revision,
    };
    work['saved_results'] = {
      'items': [latest],
      'latest': latest,
      'next_parent_state': 'AVAILABLE',
    };
  }

  @override
  Future<Map<String, dynamic>> reopenSourceBriefSavedWork({
    required String domainId,
    required String artifactId,
  }) async {
    savedReads++;
    savedArtifactIds.add(artifactId);
    if (denySavedRead) {
      throw const LumenisCoreException(
        'Saved source withdrawn',
        statusCode: 403,
      );
    }
    if (artifactId == _internalArtifact) {
      final receipt = (work['action'] as Map)['receipt'] as Map;
      return _envelope({
        'artifact': {
          'artifact_id': _internalArtifact,
          'sha256': (alterSavedHash ? 'c' : 'a') * 64,
        },
        'document': {
          'work_id': _internalWork,
          'task_id': _internalTask,
          'version': 1,
          'parent_artifact_id': null,
          'parent_sha256': null,
          'markdown': '$_internalTitle\n\n## Material\n\n$_internalBody',
          'payload': {
            'manuscript': {'title': _internalTitle},
          },
          'attachments': [
            _clone(Map<String, dynamic>.from(receipt['output'] as Map)),
          ],
        },
      });
    }
    final saved = (work['saved_results'] as Map)['items'] as List;
    final selected = saved.cast<Map>().firstWhere(
      (row) => row['artifact_id'] == artifactId,
    );
    return _envelope({
      'artifact': {
        'artifact_id': artifactId,
        'sha256': alterSavedHash ? 'c' * 64 : selected['sha256'],
      },
      'document': {
        'version': selected['version'],
        'markdown':
            '## Numeric checks\n\nThe retained report result.\n\n方法：source_bound_business_question_analysis/1\n',
        'draft_digest': selected['draft_digest'],
        'payload': {
          'business_work': {
            'work_id': _workId,
            'revision': selected['business_revision'],
            'question': work['question'],
          },
        },
      },
    });
  }

  @override
  Future<SavedWorkExportFile> exportSourceBriefSavedWork({
    required String domainId,
    required String artifactId,
    required String format,
    String purpose = 'delivery',
  }) async {
    exports.add({
      'domainId': domainId,
      'artifactId': artifactId,
      'format': format,
      'purpose': purpose,
    });
    if (exportError case final error?) throw error;
    if (pendingExport case final pending?) return pending.future;
    return SavedWorkExportFile(
      bytes: Uint8List.fromList(
        emptyExport ? [] : utf8.encode('Exported $artifactId'),
      ),
      filename: '$artifactId.$format',
      mediaType: 'application/octet-stream',
    );
  }

  @override
  Future<Map<String, dynamic>> saveBusinessWork({
    required String domainId,
    required String workId,
    required String revision,
    required String requestId,
    required List<Map<String, dynamic>> citations,
    String? confirmedResource,
    String? previousArtifactId,
    String? expectedDraftDigest,
  }) async {
    saves.add({
      'requestId': requestId,
      'citations': citations,
      'confirmedResource': confirmedResource,
      'previousArtifactId': previousArtifactId,
      'expectedDraftDigest': expectedDraftDigest,
    });
    if (confirmedResource == null) {
      return _envelope({'resource': 'exact-reviewed-resource'});
    }
    committedSaves += 1;
    markSaved();
    return _envelope({
      'saved_work': {
        'artifact': {'artifact_id': _artifact},
        'document': {'version': 1, 'draft_digest': 'b' * 64},
      },
    });
  }

  @override
  Future<Map<String, dynamic>> advanceBusinessWork({
    required String domainId,
    required String workId,
    required String operation,
    required String revision,
    required String submissionId,
    required Map<String, dynamic> payload,
  }) async {
    transitions.add({
      'operation': operation,
      'revision': revision,
      'submissionId': submissionId,
      'payload': payload,
    });
    if (failNextTransition) {
      failNextTransition = false;
      throw const LumenisCoreException('Uncertain acknowledgement');
    }
    if (transitionError case final error?) throw error;
    work['state'] = 'DECIDED';
    if (operation == 'adopt' && payload['decision'] is Map) {
      work['decision'] = _clone(
        Map<String, dynamic>.from(payload['decision'] as Map),
      );
      if (payload['options'] is List) work['options'] = payload['options'];
    }
    work['revision'] = 'app_evidence_records:11';
    return _envelope(_clone(work));
  }
}
