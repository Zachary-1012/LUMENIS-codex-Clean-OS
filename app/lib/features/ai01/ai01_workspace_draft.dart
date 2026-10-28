import 'dart:async';

import 'package:flutter/widgets.dart';

import '../../core/lumenis_core_client.dart';

class Ai01WorkspaceDraft extends TextEditingController {
  Ai01WorkspaceDraft(this.client, this.scopeKey) {
    addListener(_edited);
    unawaited(restore());
  }

  final LumenisCoreClient client;
  final String scopeKey;
  final status = ValueNotifier<String>('loading');
  Timer? _timer;
  bool _closed = false, _applying = false, _restoring = false;
  Future<void>? _pendingFlush;
  int? _revision;
  String _persisted = '';
  String? recoveredText;
  bool get hasUnsavedChanges => text != _persisted || recoveredText != null;

  void _edited() {
    if (_applying || _closed) return;
    _timer?.cancel();
    if (value.composing.isValid && !value.composing.isCollapsed) {
      status.value = 'editing';
      return;
    }
    if (_revision == null || recoveredText != null) return;
    status.value = text == _persisted ? 'saved' : 'saving';
    _timer = Timer(const Duration(milliseconds: 450), flush);
  }

  Map<String, dynamic> _read(Map<String, dynamic> response) {
    final draft = response['draft'];
    if (response['ok'] != true ||
        draft is! Map<String, dynamic> ||
        draft['scope_key'] != scopeKey ||
        draft['text'] is! String ||
        draft['revision'] is! int ||
        (draft['revision'] as int) < 0) {
      throw const FormatException('Invalid draft receipt');
    }
    return draft;
  }

  Future<void> restore() async {
    if (_closed || _pendingFlush != null || _restoring) return;
    _restoring = true;
    final before = value;
    status.value = 'loading';
    try {
      final row = _read(await client.workspaceDraft(scopeKey));
      if (_closed) return;
      _revision = row['revision'] as int;
      final remote = row['text'] as String;
      if (text.isNotEmpty && text != remote && _revision != 0) {
        recoveredText = remote;
        status.value = 'conflict';
        return;
      }
      _persisted = remote;
      if (value == before && text.isEmpty) {
        _applying = true;
        value = TextEditingValue(
          text: remote,
          selection: TextSelection.collapsed(offset: remote.length),
        );
        _applying = false;
      }
      status.value = 'saved';
      _edited();
    } catch (_) {
      if (!_closed) status.value = 'failed';
    } finally {
      _restoring = false;
    }
  }

  Future<void> flush() {
    if (_pendingFlush case final pending?) return pending;
    _timer?.cancel();
    late final Future<void> pending;
    pending = _flushChanges().whenComplete(() {
      if (identical(_pendingFlush, pending)) _pendingFlush = null;
    });
    _pendingFlush = pending;
    return pending;
  }

  Future<void> _flushChanges() async {
    while (!_closed &&
        !_restoring &&
        _revision != null &&
        recoveredText == null &&
        !(value.composing.isValid && !value.composing.isCollapsed) &&
        text != _persisted) {
      final sent = text;
      status.value = 'saving';
      try {
        final row = _read(
          await client.saveWorkspaceDraft(scopeKey, sent, _revision!),
        );
        if (_closed) return;
        if (row['text'] != sent) {
          throw const FormatException('Draft write mismatch');
        }
        _revision = row['revision'] as int;
        _persisted = sent;
        status.value = text == sent ? 'saved' : 'saving';
      } on LumenisCoreException catch (error) {
        if (!_closed) {
          status.value = error.statusCode == 409 ? 'conflict' : 'failed';
          if (error.statusCode == 409) _revision = null;
        }
        return;
      } catch (_) {
        if (!_closed) status.value = 'failed';
        return;
      }
    }
  }

  void discardLocalChanges() {
    _timer?.cancel();
    _applying = true;
    text = recoveredText ?? _persisted;
    _persisted = text;
    recoveredText = null;
    _applying = false;
    status.value = 'saved';
  }

  void useRecovered() {
    final remote = recoveredText;
    if (remote == null) return;
    recoveredText = null;
    _persisted = remote;
    _applying = true;
    value = TextEditingValue(
      text: remote,
      selection: TextSelection.collapsed(offset: remote.length),
    );
    _applying = false;
    status.value = 'saved';
  }

  Future<void> keepCurrent() async {
    if (recoveredText == null || _revision == null) return;
    _persisted = recoveredText!;
    recoveredText = null;
    await flush();
  }

  @override
  void dispose() {
    _closed = true;
    _timer?.cancel();
    removeListener(_edited);
    status.dispose();
    super.dispose();
  }
}
