import 'dart:async';
import 'package:flutter/material.dart';
import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_icon.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';

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

class Ai01DraftStatus extends StatelessWidget {
  const Ai01DraftStatus({required this.draft, super.key});
  final Ai01WorkspaceDraft draft;

  String _text(BuildContext context, String zh, String en, String ko) =>
      switch (context.lumenisL10n.locale.languageCode) {
        'en' => en,
        'ko' => ko,
        _ => zh,
      };

  @override
  Widget build(BuildContext context) => ValueListenableBuilder<String>(
    valueListenable: draft.status,
    builder: (context, state, _) {
      final trouble = state == 'failed' || state == 'conflict';
      if (state == 'saved' && draft.text.isEmpty) {
        return const SizedBox.shrink();
      }
      return Semantics(
        liveRegion: trouble,
        child: Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Wrap(
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 8,
            children: [
              LumenisIcon(
                trouble
                    ? Icons.error_outline
                    : state == 'saved'
                    ? Icons.check_rounded
                    : Icons.more_horiz,
                size: 14,
                color: LumenisTheme.of(context).muted,
              ),
              Text(switch (state) {
                'loading' => _text(
                  context,
                  '正在恢复草稿',
                  'Restoring draft',
                  '초안 복원 중',
                ),
                'saving' => _text(context, '正在保存草稿', 'Saving draft', '초안 저장 중'),
                'editing' => _text(
                  context,
                  '未保存修改',
                  'Unsaved changes',
                  '저장하지 않은 변경',
                ),
                'conflict' => _text(
                  context,
                  '另一个窗口修改了草稿',
                  'Draft changed in another window',
                  '다른 창에서 초안이 변경되었습니다',
                ),
                'failed' => _text(
                  context,
                  '草稿尚未保存',
                  'Draft not saved',
                  '초안이 저장되지 않았습니다',
                ),
                _ => _text(context, '草稿已保存', 'Draft saved', '초안 저장됨'),
              }, style: Theme.of(context).textTheme.bodySmall),
              if (trouble && draft.recoveredText == null)
                TextButton(
                  onPressed: draft.restore,
                  child: Text(_text(context, '重新读取', 'Check draft', '초안 확인')),
                ),
              if (draft.recoveredText != null) ...[
                TextButton(
                  onPressed: () => showDialog<void>(
                    context: context,
                    builder: (context) => AlertDialog(
                      title: Text(
                        _text(context, '已保存的草稿', 'Saved draft', '저장된 초안'),
                      ),
                      content: SingleChildScrollView(
                        child: SelectableText(draft.recoveredText!),
                      ),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.pop(context),
                          child: Text(
                            context.lumenisL10n.text('common.cancel'),
                          ),
                        ),
                        TextButton(
                          onPressed: () {
                            draft.useRecovered();
                            Navigator.pop(context);
                          },
                          child: Text(
                            _text(
                              context,
                              '恢复此稿',
                              'Restore this draft',
                              '이 초안 복원',
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  child: Text(
                    _text(context, '查看已保存稿', 'View saved draft', '저장된 초안 보기'),
                  ),
                ),
                TextButton(
                  onPressed: draft.keepCurrent,
                  child: Text(
                    _text(context, '保留当前稿', 'Keep current draft', '현재 초안 유지'),
                  ),
                ),
              ],
            ],
          ),
        ),
      );
    },
  );
}
