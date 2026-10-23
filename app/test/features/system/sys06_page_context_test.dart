import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/features/system/sys06/sys06_page_context.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';

void main() {
  testWidgets('page text is shown as a source excerpt, never as an answer', (
    tester,
  ) async {
    String? received;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Sys06PageContext(
            read: (question) async {
              received = question;
              return {
                'ok': true,
                'page_context': {
                  'question': question,
                  'excerpt': 'Open from 10 AM.',
                  'answer_state': 'NOT_GENERATED',
                  'content_kind': 'SOURCE_EXCERPT',
                  'selection': {'matched_query_terms': 1},
                },
                'metadata': {
                  'title': 'Visitor information',
                  'url': 'https://example.com/visit',
                  'captured_at': '2026-10-23T02:00:00Z',
                },
                'formats': {
                  'text': {'success': true, 'data': 'Open from 10 AM.'},
                },
                'truncated': true,
              };
            },
          ),
        ),
      ),
    );
    await tester.enterText(
      find.byKey(const ValueKey('sys06-context-question')),
      'Opening hours',
    );
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('sys06-context-read')));
    await tester.pumpAndSettle();
    expect(received, 'Opening hours');
    expect(find.text('Open from 10 AM.'), findsOneWidget);
    expect(
      find.text(
        'This is page text. An analysis or answer has not been generated.',
      ),
      findsOneWidget,
    );
    expect(find.text('Some page content was not captured.'), findsOneWidget);
  });

  testWidgets('changed page retains question without showing a stale answer', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Sys06PageContext(
            read: (_) async => throw const LumenisCoreException(
              'changed',
              errorCode: 'BROWSER_EXTRACTION_PAGE_CHANGED',
            ),
          ),
        ),
      ),
    );
    await tester.enterText(
      find.byKey(const ValueKey('sys06-context-question')),
      'My question',
    );
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('sys06-context-read')));
    await tester.pumpAndSettle();
    expect(
      find.text('The page changed. Return to it and read again.'),
      findsOneWidget,
    );
    expect(find.text('My question'), findsOneWidget);
    expect(find.text('From the page'), findsNothing);
  });
}
