import 'dart:async';

import 'package:flutter/widgets.dart';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/ai01/ai01_workspace_draft.dart';

class DraftClient extends LumenisCoreClient {
  DraftClient() : super(baseUrl: 'http://127.0.0.1:1');
  String saved = '';
  int revision = 0;
  bool fail = false;
  Completer<void>? writeBarrier;
  Completer<void>? readBarrier;
  final writes = <String>[];

  Map<String, dynamic> receipt(String scope) => {
    'ok': true,
    'draft': {'scope_key': scope, 'text': saved, 'revision': revision},
  };

  @override
  Future<Map<String, dynamic>> workspaceDraft(String scopeKey) async {
    if (readBarrier case final barrier?) await barrier.future;
    return receipt(scopeKey);
  }

  @override
  Future<Map<String, dynamic>> saveWorkspaceDraft(
    String scopeKey,
    String text,
    int expectedRevision,
  ) async {
    writes.add(text);
    if (writeBarrier case final barrier?) await barrier.future;
    if (fail) throw StateError('offline');
    if (expectedRevision != revision) {
      throw LumenisCoreException('conflict', statusCode: 409);
    }
    saved = text;
    revision++;
    return receipt(scopeKey);
  }
}

Future<void> settled() => Future<void>.delayed(Duration.zero);

void main() {
  test('composition stays local until the input method commits text', () async {
    final client = DraftClient();
    final draft = Ai01WorkspaceDraft(client, 'GLOBAL_ALL::');
    addTearDown(draft.dispose);
    await settled();
    draft.value = const TextEditingValue(
      text: 'huan',
      composing: TextRange(start: 0, end: 4),
    );
    await draft.flush();
    expect(client.writes, isEmpty);
    expect(draft.status.value, 'editing');
    draft.value = const TextEditingValue(
      text: '寰意',
      selection: TextSelection.collapsed(offset: 2),
    );
    await draft.flush();
    expect(client.writes, ['寰意']);
    expect(draft.hasUnsavedChanges, isFalse);
  });
  test(
    'navigation flush waits for pending writes and the edit made during them',
    () async {
      final client = DraftClient();
      final draft = Ai01WorkspaceDraft(client, 'GLOBAL_ALL::');
      addTearDown(draft.dispose);
      await settled();
      client.writeBarrier = Completer<void>();
      draft.text = 'first';
      final first = draft.flush();
      draft.text = 'newer input';
      final navigation = draft.flush();
      expect(identical(first, navigation), isTrue);
      client.writeBarrier!.complete();
      await navigation;
      expect(client.writes, ['first', 'newer input']);
      expect(client.saved, 'newer input');
      expect(draft.hasUnsavedChanges, isFalse);
      final reopened = Ai01WorkspaceDraft(client, 'GLOBAL_ALL::');
      addTearDown(reopened.dispose);
      await settled();
      expect(reopened.text, 'newer input');
    },
  );

  test(
    'typing during read and competing windows require an explicit choice',
    () async {
      final client = DraftClient()
        ..saved = 'other window'
        ..revision = 3;
      client.readBarrier = Completer<void>();
      final draft = Ai01WorkspaceDraft(client, 'GLOBAL_ALL::');
      addTearDown(draft.dispose);
      draft.text = 'my input';
      client.readBarrier!.complete();
      await settled();
      expect(draft.text, 'my input');
      expect(draft.recoveredText, 'other window');
      await draft.flush();
      expect(client.writes, isEmpty);
      await draft.keepCurrent();
      expect(client.saved, 'my input');
      client.saved = 'another revision';
      client.revision++;
      draft.text = 'local unsaved';
      await draft.flush();
      expect(draft.status.value, 'conflict');
      await draft.restore();
      expect(draft.text, 'local unsaved');
      draft.useRecovered();
      expect(draft.text, 'another revision');
      expect(draft.hasUnsavedChanges, isFalse);
    },
  );

  test(
    'failed writes retain input for retry and explicit discard stops a debounce',
    () async {
      final client = DraftClient();
      final draft = Ai01WorkspaceDraft(client, 'GLOBAL_ALL::');
      addTearDown(draft.dispose);
      await settled();
      client.fail = true;
      draft.text = 'must not disappear';
      await draft.flush();
      expect(draft.status.value, 'failed');
      expect(draft.text, 'must not disappear');
      expect(draft.hasUnsavedChanges, isTrue);
      client.fail = false;
      await draft.flush();
      expect(client.saved, 'must not disappear');
      draft.text = 'discard me';
      draft.discardLocalChanges();
      await draft.flush();
      expect(client.saved, 'must not disappear');
      expect(draft.text, client.saved);
    },
  );
}
