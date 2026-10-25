import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/ai01/ai01_conversation_panel.dart';
import 'package:lumenis_app/features/ai01/ai01_conversations.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

void main() {
  late _ConversationRepository repository;
  late Ai01ConversationViewModel model;

  setUp(() {
    repository = _ConversationRepository();
    model = Ai01ConversationViewModel(repository: repository);
  });

  tearDown(() => model.dispose());

  testWidgets(
    'work details save, reopen and exclude messages without requesting AI',
    (tester) async {
      await model.createConversation();
      await repository.append(
        conversationId: model.selectedId!,
        text: 'obsolete budget is 100',
        idempotencyKey: 'original',
        expectedRevision: 1,
      );
      await model.open(model.selectedId!);
      final draft = TextEditingController(text: 'unsent composer stays');
      addTearDown(draft.dispose);
      await tester.pumpWidget(_conversationApp(model, draft));
      await tester.pumpAndSettle();
      await tester.tap(
        find.byKey(const ValueKey('ai01-conversation-context-open')),
      );
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const ValueKey('ai01-conversation-context-goal')),
        'finish the existing manuscript',
      );
      await _showContextField(tester, 'draft');
      await tester.enterText(
        find.byKey(const ValueKey('ai01-conversation-context-draft')),
        'current human writing',
      );
      final exclude = find.byKey(
        ValueKey(
          'ai01-conversation-context-exclude-${repository.userTurns.single.id}',
        ),
      );
      await tester.scrollUntilVisible(
        exclude,
        160,
        scrollable: _contextScroll(),
      );
      await tester.pumpAndSettle();
      await tester.tap(exclude);
      await tester.tap(
        find.byKey(const ValueKey('ai01-conversation-context-save')),
      );
      await tester.pumpAndSettle();
      expect(repository.contextWriteCount, 1);
      expect(
        repository.contexts[model.selectedId!]!.value['draft'],
        'current human writing',
      );
      expect(
        repository.contexts[model.selectedId!]!.value['excluded_turn_ids'],
        [repository.userTurns.single.id],
      );
      expect(repository.respondCalls, isEmpty);
      expect(draft.text, 'unsent composer stays');
      await tester.tap(
        find.byKey(const ValueKey('ai01-conversation-context-close')),
      );
      await tester.pumpAndSettle();
      await tester.tap(
        find.byKey(const ValueKey('ai01-conversation-context-open')),
      );
      await tester.pumpAndSettle();
      expect(
        tester
            .widget<TextField>(
              find.byKey(const ValueKey('ai01-conversation-context-goal')),
            )
            .controller!
            .text,
        'finish the existing manuscript',
      );
      await _showContextField(tester, 'draft');
      expect(
        tester
            .widget<TextField>(
              find.byKey(const ValueKey('ai01-conversation-context-draft')),
            )
            .controller!
            .text,
        'current human writing',
      );
      expect(repository.respondCalls, isEmpty);
    },
  );

  testWidgets(
    'work-detail conflict keeps local writing until an explicit version choice',
    (tester) async {
      await model.createConversation();
      repository.contextConflictOnce = true;
      final draft = TextEditingController();
      addTearDown(draft.dispose);
      await tester.pumpWidget(_conversationApp(model, draft));
      await tester.pumpAndSettle();
      await tester.tap(
        find.byKey(const ValueKey('ai01-conversation-context-open')),
      );
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const ValueKey('ai01-conversation-context-goal')),
        'my unchanged goal',
      );
      await tester.pumpAndSettle();
      await tester.tap(
        find.byKey(const ValueKey('ai01-conversation-context-save')),
      );
      await tester.pumpAndSettle();
      expect(repository.contextWriteCount, 1);
      expect(
        tester
            .widget<TextField>(
              find.byKey(const ValueKey('ai01-conversation-context-goal')),
            )
            .controller!
            .text,
        'my unchanged goal',
      );
      expect(
        repository.contexts[model.selectedId!]!.value['goal'],
        'remote goal',
      );
      final keep = find.byKey(
        const ValueKey('ai01-conversation-context-keep-local'),
      );
      await tester.scrollUntilVisible(keep, -160, scrollable: _contextScroll());
      await tester.tap(keep);
      await tester.pumpAndSettle();
      expect(repository.contextWriteCount, 2);
      expect(
        repository.contexts[model.selectedId!]!.value['goal'],
        'my unchanged goal',
      );
      expect(repository.respondCalls, isEmpty);
    },
  );

  testWidgets(
    'unknown context save checks persisted bytes before any new write',
    (tester) async {
      await model.createConversation();
      repository.contextThrowsAfterPersist = true;
      final draft = TextEditingController();
      addTearDown(draft.dispose);
      await tester.pumpWidget(_conversationApp(model, draft));
      await tester.pumpAndSettle();
      await tester.tap(
        find.byKey(const ValueKey('ai01-conversation-context-open')),
      );
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const ValueKey('ai01-conversation-context-goal')),
        'save without a model',
      );
      await tester.pumpAndSettle();
      await tester.tap(
        find.byKey(const ValueKey('ai01-conversation-context-save')),
      );
      await tester.pumpAndSettle();
      expect(repository.contextWriteCount, 1);
      expect(
        tester
            .widget<FilledButton>(
              find.byKey(const ValueKey('ai01-conversation-context-save')),
            )
            .onPressed,
        isNull,
      );
      await tester.tap(
        find.byKey(const ValueKey('ai01-conversation-context-check')),
      );
      await tester.pumpAndSettle();
      expect(repository.contextWriteCount, 1);
      expect(
        tester
            .widget<TextField>(
              find.byKey(const ValueKey('ai01-conversation-context-goal')),
            )
            .controller!
            .text,
        'save without a model',
      );
      expect(repository.respondCalls, isEmpty);
    },
  );

  for (final status in [401, 403, 404, 410]) {
    testWidgets('context read $status clears writing and cached conversation', (
      tester,
    ) async {
      await model.createConversation();
      final composer = TextEditingController(text: 'unsent independent draft');
      addTearDown(composer.dispose);
      await tester.pumpWidget(_conversationApp(model, composer));
      await tester.pumpAndSettle();
      await tester.tap(
        find.byKey(const ValueKey('ai01-conversation-context-open')),
      );
      await tester.pumpAndSettle();
      final controllers = <TextEditingController>[];
      for (final name in ['goal', 'constraints', 'draft', 'decisions']) {
        await _showContextField(tester, name);
        final field = find.byKey(ValueKey('ai01-conversation-context-$name'));
        await tester.enterText(field, 'restricted $name');
        controllers.add(tester.widget<TextField>(field).controller!);
      }
      repository.contextReadStatus = status;
      await tester.tap(
        find.byKey(const ValueKey('ai01-conversation-context-check')),
      );
      await tester.pumpAndSettle();
      expect(
        controllers.map((controller) => controller.text),
        everyElement(isEmpty),
      );
      expect(model.detail, isNull);
      expect(repository.contextWriteCount, 0);
      expect(composer.text, 'unsent independent draft');
      expect(
        tester
            .widget<FilledButton>(
              find.byKey(const ValueKey('ai01-conversation-context-save')),
            )
            .onPressed,
        isNull,
      );
      expect(repository.respondCalls, isEmpty);
    });
  }

  for (final revokedRead in [false, true]) {
    testWidgets('context write denial rechecks read, revoked=$revokedRead', (
      tester,
    ) async {
      await model.createConversation();
      final composer = TextEditingController();
      addTearDown(composer.dispose);
      await tester.pumpWidget(_conversationApp(model, composer));
      await tester.pumpAndSettle();
      await tester.tap(
        find.byKey(const ValueKey('ai01-conversation-context-open')),
      );
      await tester.pumpAndSettle();
      final field = find.byKey(
        const ValueKey('ai01-conversation-context-goal'),
      );
      await tester.enterText(field, 'keep only while readable');
      await tester.pumpAndSettle();
      repository.contextWriteStatus = 403;
      if (revokedRead) repository.contextReadStatus = 403;
      await tester.tap(
        find.byKey(const ValueKey('ai01-conversation-context-save')),
      );
      await tester.pumpAndSettle();
      expect(repository.contextReadCount, 2);
      expect(repository.contextWriteCount, 1);
      expect(
        tester.widget<TextField>(field).controller!.text,
        revokedRead ? '' : 'keep only while readable',
      );
      expect(model.detail == null, revokedRead);
      expect(repository.respondCalls, isEmpty);
    });
  }

  for (final writeDenied in [false, true]) {
    testWidgets(
      'unknown context read retains local writing, denied write=$writeDenied',
      (tester) async {
        await model.createConversation();
        final composer = TextEditingController();
        addTearDown(composer.dispose);
        await tester.pumpWidget(_conversationApp(model, composer));
        await tester.pumpAndSettle();
        await tester.tap(
          find.byKey(const ValueKey('ai01-conversation-context-open')),
        );
        await tester.pumpAndSettle();
        final field = find.byKey(
          const ValueKey('ai01-conversation-context-goal'),
        );
        await tester.enterText(
          field,
          'local writing survives transport failure',
        );
        await tester.pumpAndSettle();
        repository.contextReadOffline = true;
        if (writeDenied) repository.contextWriteStatus = 403;
        await tester.tap(
          find.byKey(
            ValueKey(
              writeDenied
                  ? 'ai01-conversation-context-save'
                  : 'ai01-conversation-context-check',
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(
          tester.widget<TextField>(field).controller!.text,
          'local writing survives transport failure',
        );
        expect(repository.contextWriteCount, writeDenied ? 1 : 0);
        expect(model.detail, isNotNull);
        expect(repository.respondCalls, isEmpty);
      },
    );
  }

  testWidgets('server-unknown context save keeps draft and requires readback', (
    tester,
  ) async {
    await model.createConversation();
    final composer = TextEditingController();
    addTearDown(composer.dispose);
    await tester.pumpWidget(_conversationApp(model, composer));
    await tester.pumpAndSettle();
    await tester.tap(
      find.byKey(const ValueKey('ai01-conversation-context-open')),
    );
    await tester.pumpAndSettle();
    final field = find.byKey(const ValueKey('ai01-conversation-context-goal'));
    await tester.enterText(field, 'unknown save must not lose this');
    await tester.pumpAndSettle();
    repository.contextWriteStatus = 503;
    await tester.tap(
      find.byKey(const ValueKey('ai01-conversation-context-save')),
    );
    await tester.pumpAndSettle();
    expect(repository.contextWriteCount, 1);
    expect(
      tester.widget<TextField>(field).controller!.text,
      'unknown save must not lose this',
    );
    expect(
      tester
          .widget<FilledButton>(
            find.byKey(const ValueKey('ai01-conversation-context-save')),
          )
          .onPressed,
      isNull,
    );
    expect(repository.contextReadCount, 1);
  });

  testWidgets(
    'keyboard submit waits for IME composition and persists the final text once',
    (tester) async {
      final draft = TextEditingController();
      addTearDown(draft.dispose);
      await tester.pumpWidget(_conversationApp(model, draft, embedded: true));
      await tester.pumpAndSettle();
      final input = find.byKey(const ValueKey('ai01-conversation-input'));
      await tester.enterText(input, '经营分析');
      draft.value = const TextEditingValue(
        text: '经营分析',
        selection: TextSelection.collapsed(offset: 4),
        composing: TextRange(start: 0, end: 4),
      );
      await tester.pump();
      await tester.sendKeyDownEvent(LogicalKeyboardKey.controlLeft);
      await tester.sendKeyEvent(LogicalKeyboardKey.enter);
      await tester.sendKeyUpEvent(LogicalKeyboardKey.controlLeft);
      await tester.pumpAndSettle();
      expect(repository.conversations, isEmpty);
      expect(repository.appendedTexts, isEmpty);
      draft.value = const TextEditingValue(
        text: '经营分析',
        selection: TextSelection.collapsed(offset: 4),
      );
      await tester.pump();
      await tester.sendKeyDownEvent(LogicalKeyboardKey.controlLeft);
      await tester.sendKeyEvent(LogicalKeyboardKey.enter);
      await tester.sendKeyUpEvent(LogicalKeyboardKey.controlLeft);
      await tester.pumpAndSettle();
      expect(repository.appendedTexts, ['经营分析']);
      expect(repository.respondCalls, hasLength(1));
      expect(draft.text, isEmpty);
      expect(tester.takeException(), isNull);
    },
  );

  test(
    'persists the original message, replies once, and reopens saved turns',
    () async {
      await model.refreshList();
      await model.createConversation();
      var cleared = false;

      expect(
        await model.send(
          '  Keep the user\'s spacing.  ',
          onPersisted: () => cleared = true,
        ),
        isTrue,
      );
      expect(cleared, isTrue);
      expect(repository.appendedTexts, ['  Keep the user\'s spacing.  ']);
      expect(repository.respondCalls, hasLength(1));
      expect(model.detail!.turns.map((turn) => turn.text), [
        '  Keep the user\'s spacing.  ',
        'A grounded reply',
      ]);

      final conversationId = model.detail!.id;
      model.showConversationList();
      await model.open(conversationId);
      expect(model.detail!.turns.map((turn) => turn.text), [
        '  Keep the user\'s spacing.  ',
        'A grounded reply',
      ]);
    },
  );

  test(
    'unknown append is not duplicated and safe save retry does not request AI',
    () async {
      await model.createConversation();
      repository.appendThrowsAfterPersist = true;
      var cleared = false;

      expect(
        await model.send('save this once', onPersisted: () => cleared = true),
        isFalse,
      );
      expect(repository.appendCalls, hasLength(1));
      expect(repository.respondCalls, isEmpty);
      expect(model.outcomeUnknown, isTrue);
      expect(model.canSend, isFalse);
      expect(model.pendingAppendText, 'save this once');

      await model.checkOutcome(onAppendPersisted: () => cleared = true);
      expect(cleared, isTrue);
      expect(repository.appendCalls, hasLength(1));
      expect(repository.userTurns, hasLength(1));
      expect(model.pendingAppendText, isNull);
      expect(model.outcomeUnknown, isFalse);
      expect(model.canSend, isTrue);
      expect(repository.respondCalls, isEmpty);

      final userTurn = model.detail!.turns.single;
      await model.respondToTurn(userTurn, confirmed: true);
      expect(repository.respondCalls, hasLength(1));
      expect(repository.respondCalls.single.retryConfirmed, isFalse);
    },
  );

  test(
    'unknown append can be safely retried with the original idempotency key',
    () async {
      await model.createConversation();
      repository.appendThrowsBeforePersist = true;
      await model.send('persist once', onPersisted: () {});
      final originalKey = repository.appendCalls.single.idempotencyKey;
      repository.appendThrowsBeforePersist = false;

      await model.retryPendingAppend(onPersisted: () {});

      expect(repository.appendCalls, hasLength(2));
      expect(repository.appendCalls.last.idempotencyKey, originalKey);
      expect(repository.userTurns, hasLength(1));
      expect(repository.respondCalls, isEmpty);
      expect(model.pendingAppendText, isNull);
    },
  );

  test(
    'unknown conversation creation is never repeated without acknowledgement',
    () async {
      repository.createThrowsAfterPersist = true;

      await model.createConversation();

      expect(model.creatingUnknown, isTrue);
      expect(repository.conversations, hasLength(1));
      await model.createConversation();
      expect(repository.conversations, hasLength(1));

      await model.createConversation(acknowledgeUnresolvedPrevious: true);
      expect(repository.conversations, hasLength(2));
      expect(model.creatingUnknown, isFalse);
    },
  );

  test(
    'unknown model result is read back and never automatically retried',
    () async {
      await model.createConversation();
      repository.respondThrowsAfterReserve = true;

      await model.send('wait for a reply', onPersisted: () {});
      expect(repository.respondCalls, hasLength(1));
      expect(model.outcomeUnknown, isTrue);
      expect(model.canSend, isFalse);

      await model.checkOutcome();
      expect(repository.respondCalls, hasLength(1));
      final reserved = model.detail!.turns.singleWhere(
        (turn) => turn.originKind == 'model_output',
      );
      expect(reserved.state, 'reserved');

      await model.interruptResponse(reserved, confirmed: true);
      expect(repository.interruptCalls, hasLength(1));
      expect(repository.interruptCalls.single.confirmed, isTrue);
      expect(model.outcomeUnknown, isTrue);
      expect(repository.interruptCalls.single.externalCallStopped, isFalse);
    },
  );

  test(
    'a new response attempt requires explicit confirmation after failure',
    () async {
      await model.createConversation();
      repository.respondFailureState = 'failed';
      await model.send('try a reply', onPersisted: () {});
      final userTurn = model.detail!.turns.first;

      await model.retryResponse(userTurn, confirmed: false);
      expect(repository.respondCalls, hasLength(1));
      await model.retryResponse(userTurn, confirmed: true);
      expect(repository.respondCalls, hasLength(2));
      expect(repository.respondCalls.last.retryConfirmed, isTrue);
    },
  );

  test(
    'conversation and turn pages follow server cursors and preserve identity',
    () async {
      for (var index = 0; index < 30; index++) {
        final id = 'conv_${index.toRadixString(16).padLeft(32, '0')}';
        repository.conversations[id] = _summary(
          id,
          title: 'Conversation $index',
        );
        repository.turns[id] = [];
      }
      repository.conversations[_conversationId] = _summary(_conversationId);
      repository.turns[_conversationId] = [
        for (var index = 0; index < 31; index++)
          repository._turn(
            _conversationId,
            role: 'user',
            originKind: 'user_input',
            text: 'turn $index',
          ),
      ];
      await model.refreshList(selectFirstIfEmpty: false);
      expect(model.listHasMore, isTrue);
      expect(model.conversations, hasLength(30));
      await model.loadMoreConversations();
      expect(repository.listOffsets, [0, 30]);
      expect(model.conversations, hasLength(31));

      await model.open(_conversationId);
      expect(model.canLoadMoreTurns, isTrue);
      await model.loadMoreTurns();
      expect(repository.readCursors, [0, 30]);
      expect(model.detail!.turns, hasLength(31));
      expect(model.detail!.turns.last.sequence, 31);
    },
  );

  testWidgets(
    'home uses existing conversation persistence without an extra dialog or empty creation',
    (tester) async {
      final draft = TextEditingController();
      addTearDown(draft.dispose);
      await tester.pumpWidget(_conversationApp(model, draft, embedded: true));
      await tester.pumpAndSettle();
      expect(repository.conversations, isEmpty);
      expect(
        find.byKey(const ValueKey('ai01-conversation-dialog')),
        findsNothing,
      );
      await tester.enterText(
        find.byKey(const ValueKey('ai01-conversation-input')),
        'Keep this original question',
      );
      await tester.pump();
      await tester.tap(find.byKey(const ValueKey('ai01-conversation-send')));
      await tester.pumpAndSettle();
      expect(repository.conversations.length, 1);
      expect(repository.appendedTexts, ['Keep this original question']);
      expect(repository.respondCalls.length, 1);
      expect(draft.text, isEmpty);
      expect(find.text('A grounded reply'), findsOneWidget);
      await tester.tap(
        find.byKey(const ValueKey('ai01-conversation-new-work')),
      );
      await tester.pumpAndSettle();
      expect(repository.conversations.length, 1);
      await tester.tap(find.byKey(const ValueKey('ai01-conversation-history')));
      await tester.pumpAndSettle();
      await tester.tap(
        find.byKey(const ValueKey('ai01-conversation-$_conversationId')),
      );
      await tester.pumpAndSettle();
      expect(find.text('Keep this original question'), findsOneWidget);
      expect(repository.appendedTexts.length, 1);
      expect(repository.respondCalls.length, 1);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('home retains draft and confirmation after uncertain creation', (
    tester,
  ) async {
    repository.createThrowsAfterPersist = true;
    final draft = TextEditingController(text: 'Retain the original question');
    addTearDown(draft.dispose);
    await tester.pumpWidget(_conversationApp(model, draft, embedded: true));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('ai01-conversation-send')));
    await tester.pumpAndSettle();
    expect(model.creatingUnknown, isTrue);
    expect(repository.conversations, hasLength(1));
    expect(repository.respondCalls, isEmpty);
    expect(draft.text, 'Retain the original question');
    expect(
      tester
          .widget<IconButton>(
            find.byKey(const ValueKey('ai01-conversation-send')),
          )
          .onPressed,
      isNull,
    );
    await tester.tap(find.byKey(const ValueKey('ai01-conversation-new-work')));
    await tester.pumpAndSettle();
    expect(
      find.byKey(const ValueKey('ai01-conversation-create-again-confirm')),
      findsOneWidget,
    );
    expect(repository.conversations, hasLength(1));
    await tester.tap(
      find.descendant(
        of: find.byKey(
          const ValueKey('ai01-conversation-create-again-confirm'),
        ),
        matching: find.byType(TextButton),
      ),
    );
    await tester.pumpAndSettle();
    expect(repository.conversations, hasLength(1));
    expect(draft.text, 'Retain the original question');
    expect(tester.takeException(), isNull);
  });

  testWidgets('checking an unknown save does not clear a later draft edit', (
    tester,
  ) async {
    await model.createConversation();
    repository.appendThrowsAfterPersist = true;
    final draft = TextEditingController();
    addTearDown(draft.dispose);
    tester.view.physicalSize = const Size(1000, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(_conversationApp(model, draft));
    await tester.pumpAndSettle();
    final input = find.byKey(const ValueKey('ai01-conversation-input'));
    await tester.enterText(input, 'A');
    await tester.pumpAndSettle();
    expect(model.canSend, isTrue);
    expect(draft.text, 'A');
    expect(tester.widget<TextField>(input).controller!.text, 'A');
    final send = find.byKey(const ValueKey('ai01-conversation-send'));
    expect(tester.widget<IconButton>(send).onPressed, isNotNull);
    await tester.ensureVisible(send);
    await tester.tap(send);
    await tester.pumpAndSettle();
    expect(repository.appendCalls, hasLength(1));
    expect(model.pendingAppendText, 'A');

    draft.text = 'B';
    await tester.tap(
      find.byKey(const ValueKey('ai01-conversation-check-outcome-detail')),
    );
    await tester.pumpAndSettle();

    expect(model.pendingAppendText, isNull);
    expect(draft.text, 'B');
    expect(tester.takeException(), isNull);
  });

  testWidgets('closing the conversation scope removes its open confirmation', (
    tester,
  ) async {
    await model.createConversation();
    repository.respondFailureState = 'failed';
    await model.send('needs a retry', onPersisted: () {});
    final failedTurn = model.detail!.turns.last;
    final draft = TextEditingController();
    addTearDown(draft.dispose);
    tester.view.physicalSize = const Size(1000, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    late NavigatorState navigator;
    DialogRoute<void>? panelRoute;
    await tester.pumpWidget(
      MaterialApp(
        theme: LumenisTheme.dark,
        supportedLocales: LumenisLocalizations.supportedLocales,
        localizationsDelegates: const [
          LumenisLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        home: Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: TextButton(
                key: const ValueKey('open-conversation-panel'),
                onPressed: () {
                  navigator = Navigator.of(context, rootNavigator: true);
                  final route = DialogRoute<void>(
                    context: context,
                    builder: (_) => Ai01ConversationPanel(
                      viewModel: model,
                      draftController: draft,
                      onClose: () => navigator.pop(),
                    ),
                  );
                  panelRoute = route;
                  navigator.push(route);
                },
                child: const Text('Open'),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.byKey(const ValueKey('open-conversation-panel')));
    await tester.pumpAndSettle();
    await tester.tap(
      find.byKey(ValueKey('ai01-conversation-retry-${failedTurn.id}')),
    );
    await tester.pumpAndSettle();
    expect(
      find.byKey(const ValueKey('ai01-conversation-retry-confirm')),
      findsOneWidget,
    );

    navigator.removeRoute(panelRoute!);
    await tester.pumpAndSettle();
    expect(
      find.byKey(const ValueKey('ai01-conversation-retry-confirm')),
      findsNothing,
    );
    expect(
      find.byKey(const ValueKey('ai01-conversation-dialog')),
      findsNothing,
    );
    expect(tester.takeException(), isNull);
  });
}

Widget _conversationApp(
  Ai01ConversationViewModel model,
  TextEditingController draft, {
  bool embedded = false,
}) => MaterialApp(
  theme: LumenisTheme.dark,
  supportedLocales: LumenisLocalizations.supportedLocales,
  localizationsDelegates: const [
    LumenisLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  home: Scaffold(
    body: Ai01ConversationPanel(
      viewModel: model,
      draftController: draft,
      embedded: embedded,
      onClose: () {},
    ),
  ),
);

const _conversationId = 'conv_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';
const _secondConversationId = 'conv_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb';

Finder _contextScroll() => find
    .descendant(
      of: find.byKey(const ValueKey('ai01-conversation-context-editor')),
      matching: find.byType(Scrollable),
    )
    .first;

Future<void> _showContextField(WidgetTester tester, String name) async {
  await tester.scrollUntilVisible(
    find.byKey(ValueKey('ai01-conversation-context-$name')),
    140,
    scrollable: _contextScroll(),
  );
  await tester.pumpAndSettle();
}

class _ConversationRepository implements Ai01ConversationRepository {
  final contexts = <String, Ai01ConversationContext>{};
  int contextWriteCount = 0;
  bool contextConflictOnce = false;
  bool contextThrowsAfterPersist = false;
  int contextReadCount = 0;
  int? contextReadStatus;
  int? contextWriteStatus;
  bool contextReadOffline = false;

  @override
  Future<Ai01ConversationContext> readContext(String conversationId) async {
    contextReadCount++;
    if (contextReadStatus case final int status) {
      throw LumenisCoreException('context read denied', statusCode: status);
    }
    if (contextReadOffline) throw const SocketException('read unavailable');
    return Ai01ConversationContext(
      conversationId: conversationId,
      revision: conversations[conversationId]!.revision,
      value:
          contexts[conversationId]?.value ??
          {
            'goal': '',
            'constraints': <String>[],
            'draft': '',
            'decisions': <String>[],
            'excluded_turn_ids': <String>[],
          },
      turn: contexts[conversationId]?.turn,
    );
  }

  @override
  Future<Ai01ConversationMutation> updateContext({
    required String conversationId,
    required Map<String, dynamic> value,
    required String idempotencyKey,
    required int expectedRevision,
    List<Map<String, dynamic>>? sourceReferences,
  }) async {
    contextWriteCount++;
    if (contextWriteStatus case final int status) {
      throw LumenisCoreException('context write denied', statusCode: status);
    }
    if (contextConflictOnce) {
      contextConflictOnce = false;
      _writeContext(conversationId, {...value, 'goal': 'remote goal'});
    }
    if (expectedRevision != conversations[conversationId]!.revision) {
      throw const LumenisCoreException('stale version', statusCode: 409);
    }
    final result = _writeContext(conversationId, value);
    if (contextThrowsAfterPersist) {
      contextThrowsAfterPersist = false;
      throw const SocketException('context receipt lost');
    }
    return result;
  }

  Ai01ConversationMutation _writeContext(
    String conversationId,
    Map<String, dynamic> value,
  ) {
    final turn = _turn(
      conversationId,
      role: 'user',
      originKind: 'system_status',
      content: {'schema': 'conversation-human-context/v1', 'value': value},
    );
    _append(conversationId, turn);
    final revision = _advance(conversationId);
    contexts[conversationId] = Ai01ConversationContext(
      conversationId: conversationId,
      revision: revision,
      value: value,
      turn: turn,
    );
    return _mutation(turn, revision);
  }

  final conversations = <String, Ai01ConversationSummary>{};
  final turns = <String, List<Ai01ConversationTurn>>{};
  final appendedTexts = <String>[];
  final appendCalls = <({String idempotencyKey, int expectedRevision})>[];
  final respondCalls = <({String turnId, bool retryConfirmed})>[];
  final interruptCalls = <({bool confirmed, bool externalCallStopped})>[];
  final listOffsets = <int>[];
  final readCursors = <int>[];
  bool appendThrowsAfterPersist = false;
  bool appendThrowsBeforePersist = false;
  bool createThrowsAfterPersist = false;
  bool respondThrowsAfterReserve = false;
  String? respondFailureState;
  int _turnSequence = 0;
  int _responseAttempt = 0;
  int _createCount = 0;

  List<Ai01ConversationTurn> get userTurns => turns.values
      .expand((items) => items)
      .where((turn) => turn.originKind == 'user_input')
      .toList(growable: false);

  @override
  Future<Ai01ConversationListPage> list({
    required int limit,
    required int offset,
  }) async {
    listOffsets.add(offset);
    final items = conversations.values.toList()
      ..sort((left, right) => right.updatedAt.compareTo(left.updatedAt));
    final page = items.skip(offset).take(limit).toList(growable: false);
    final hasMore = offset + page.length < items.length;
    return Ai01ConversationListPage(
      items: page,
      hasMore: hasMore,
      nextOffset: hasMore ? offset + limit : null,
    );
  }

  @override
  Future<Ai01ConversationSummary> create({required String title}) async {
    _createCount++;
    final id = _createCount == 1 ? _conversationId : _secondConversationId;
    final summary = _summary(id, title: title, revision: 1);
    conversations[id] = summary;
    turns[id] = [];
    if (createThrowsAfterPersist) {
      createThrowsAfterPersist = false;
      throw const SocketException('creation result lost');
    }
    return summary;
  }

  @override
  Future<Ai01ConversationDetail> read({
    required String conversationId,
    required int afterSequence,
    required int limit,
  }) async {
    readCursors.add(afterSequence);
    if (contextReadStatus case final int status) {
      throw LumenisCoreException(
        'conversation read denied',
        statusCode: status,
      );
    }
    final summary = conversations[conversationId];
    if (summary == null) throw StateError('missing conversation');
    final allTurns = turns[conversationId]!;
    final eligible = allTurns
        .where((turn) => turn.sequence > afterSequence)
        .toList(growable: false);
    final page = eligible.take(limit).toList(growable: false);
    final hasMore = eligible.length > page.length;
    return Ai01ConversationDetail(
      id: summary.id,
      title: summary.title,
      revision: summary.revision,
      state: summary.state,
      updatedAt: summary.updatedAt,
      turns: page,
      hasMore: hasMore,
      nextSequence: hasMore ? page.last.sequence : null,
    );
  }

  @override
  Future<Ai01ConversationMutation> append({
    required String conversationId,
    required String text,
    required String idempotencyKey,
    required int expectedRevision,
  }) async {
    appendCalls.add((
      idempotencyKey: idempotencyKey,
      expectedRevision: expectedRevision,
    ));
    if (appendThrowsBeforePersist) throw const SocketException('unknown write');
    appendedTexts.add(text);
    final turn = _turn(
      conversationId,
      role: 'user',
      originKind: 'user_input',
      text: text,
    );
    _append(conversationId, turn);
    final revision = _advance(conversationId);
    if (appendThrowsAfterPersist) {
      appendThrowsAfterPersist = false;
      throw const SocketException('response lost');
    }
    return _mutation(turn, revision);
  }

  @override
  Future<Ai01ConversationMutation> attachTask({
    required String conversationId,
    required String taskId,
    required String idempotencyKey,
    required int expectedRevision,
  }) async {
    final turn = _turn(
      conversationId,
      role: 'assistant',
      originKind: 'task_projection',
      content: {'task_id': taskId, 'owner': 'AI-01'},
    );
    _append(conversationId, turn);
    return _mutation(turn, _advance(conversationId));
  }

  @override
  Future<Ai01ConversationMutation> respond({
    required String conversationId,
    required String turnId,
    required String idempotencyKey,
    required int expectedRevision,
    required bool retryConfirmed,
  }) async {
    _responseAttempt++;
    respondCalls.add((turnId: turnId, retryConfirmed: retryConfirmed));
    final user = turns[conversationId]!.singleWhere(
      (turn) => turn.id == turnId,
    );
    final state = _responseAttempt > 1
        ? 'completed'
        : (respondFailureState ?? 'completed');
    final turn = _turn(
      conversationId,
      role: 'assistant',
      originKind: 'model_output',
      state: respondThrowsAfterReserve ? 'reserved' : state,
      content: {
        'in_reply_to': turnId,
        if (!respondThrowsAfterReserve && state == 'completed')
          'text': 'A grounded reply',
      },
    );
    _append(conversationId, turn);
    final revision = _advance(conversationId);
    if (respondThrowsAfterReserve) {
      respondThrowsAfterReserve = false;
      throw const SocketException('result unknown');
    }
    if (respondFailureState != null && _responseAttempt > 1) {
      respondFailureState = null;
    }
    expect(user.text, isNotNull);
    return _mutation(turn, revision);
  }

  @override
  Future<Ai01ConversationMutation> interrupt({
    required String conversationId,
    required String turnId,
    required int expectedRevision,
  }) async {
    final items = turns[conversationId]!;
    final index = items.indexWhere((turn) => turn.id == turnId);
    final old = items[index];
    final updated = Ai01ConversationTurn(
      id: old.id,
      conversationId: old.conversationId,
      sequence: old.sequence,
      role: old.role,
      originKind: old.originKind,
      state: 'interrupted',
      revision: old.revision + 1,
      content: old.content,
      recovery: 'RESULT_UNKNOWN_NO_AUTOMATIC_RETRY',
    );
    items[index] = updated;
    final mutation = _mutation(
      updated,
      _advance(conversationId),
      externalCallStopped: false,
      priorResultUnknown: true,
    );
    interruptCalls.add((confirmed: true, externalCallStopped: false));
    return mutation;
  }

  void _append(String conversationId, Ai01ConversationTurn turn) {
    turns[conversationId]!.add(turn);
  }

  int _advance(String conversationId) {
    final old = conversations[conversationId]!;
    final next = _summary(
      conversationId,
      title: old.title,
      revision: old.revision + 1,
    );
    conversations[conversationId] = next;
    return next.revision;
  }

  Ai01ConversationTurn _turn(
    String conversationId, {
    required String role,
    required String originKind,
    String state = 'recorded',
    String? text,
    String? replyTo,
    Map<String, Object?>? content,
  }) {
    _turnSequence++;
    return Ai01ConversationTurn(
      id: 'turn_${_turnSequence.toRadixString(16).padLeft(32, '0')}',
      conversationId: conversationId,
      sequence: _turnSequence,
      role: role,
      originKind: originKind,
      state: state,
      revision: 1,
      content: content ?? {'text': text, 'in_reply_to': ?replyTo},
      recovery: state == 'reserved'
          ? 'RESULT_UNKNOWN_NO_AUTOMATIC_RETRY'
          : null,
    );
  }

  Ai01ConversationMutation _mutation(
    Ai01ConversationTurn turn,
    int revision, {
    bool? externalCallStopped,
    bool? priorResultUnknown,
  }) => Ai01ConversationMutation(
    turn: turn,
    revision: revision,
    idempotentHit: false,
    externalCallStopped: externalCallStopped,
    priorResultUnknown: priorResultUnknown,
  );
}

Ai01ConversationSummary _summary(
  String id, {
  String title = 'Conversation',
  int revision = 1,
}) => Ai01ConversationSummary(
  id: id,
  title: title,
  revision: revision,
  state: 'active',
  updatedAt: '2026-10-22T00:00:00Z',
);
