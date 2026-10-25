import 'dart:convert';
import 'dart:math';

import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import 'collector_request_panel.dart';

class CollectedCommentsPanel extends StatefulWidget {
  const CollectedCommentsPanel({
    super.key,
    required this.client,
    required this.domainId,
    required this.sourceId,
    required this.title,
  });
  final LumenisCoreClient client;
  final String domainId, sourceId, title;
  @override
  State<CollectedCommentsPanel> createState() => _CollectedCommentsPanelState();
}

class _CollectedCommentsPanelState extends State<CollectedCommentsPanel> {
  final _requestId =
      'comments_${DateTime.now().microsecondsSinceEpoch}_${Random.secure().nextInt(1 << 30)}';
  late final _scope = jsonEncode(widget.client.currentContextEnvelope);
  final _comments = <Map<String, dynamic>>[];
  bool _busy = false, _replies = false, _attempted = false;
  String? _next, _status, _pageRef, _sourceVersion;
  Map<String, dynamic>? _continuation;
  String _t(String zh, String en, String ko) =>
      switch (Localizations.localeOf(context).languageCode) {
        'en' => en,
        'ko' => ko,
        _ => zh,
      };
  @override
  void initState() {
    super.initState();
    _read();
  }

  bool get _sameScope =>
      _scope == jsonEncode(widget.client.currentContextEnvelope);
  void _apply(Map<String, dynamic> value, {bool append = false}) {
    if (!_sameScope) {
      throw const LumenisCoreException('Scope changed.', statusCode: 403);
    }
    final comments = value['comments'];
    if (comments is! List ||
        comments.any((row) => row is! Map || row['content'] is! String)) {
      throw const FormatException();
    }
    setState(() {
      if (!append) _comments.clear();
      _comments.addAll(
        comments.map((row) => Map<String, dynamic>.from(row as Map)),
      );
      _next = value['next_cursor'] as String?;
      _pageRef = value['page_ref'] as String? ?? _pageRef;
      _sourceVersion = value['source_version_state'] as String?;
      _status = value['status'] as String?;
      _continuation = value['continuation'] is Map
          ? Map<String, dynamic>.from(value['continuation'] as Map)
          : null;
    });
  }

  void _failed(Object error) {
    setState(() {
      final denied =
          error is LumenisCoreException &&
          const {401, 403, 404, 410}.contains(error.statusCode);
      if (denied || !_sameScope) {
        _comments.clear();
        _continuation = null;
        _next = null;
      }
      _status = denied || !_sameScope ? 'SCOPE_UNAUTHORIZED' : 'UNCONFIRMED';
    });
  }

  Future<void> _read({bool more = false, bool exactPage = false}) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final value = await widget.client.sourceComments(
        domainId: widget.domainId,
        sourceId: widget.sourceId,
        before: more ? _next : null,
        pageRef: exactPage ? _pageRef : null,
      );
      if (mounted) _apply(value, append: more);
    } catch (error) {
      if (mounted) _failed(error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _collect({bool more = false}) async {
    if (_busy || !_sameScope) return;
    setState(() {
      _busy = true;
      _attempted = true;
    });
    try {
      final result = await widget.client.collectSourceComments(
        domainId: widget.domainId,
        sourceId: widget.sourceId,
        requestId: _requestId,
        includeReplies: _replies,
        continuation: more ? _continuation : null,
      );
      if (!mounted) return;
      if (result['comments'] is List) {
        _apply(result, append: more);
      } else {
        setState(() => _status = result['status'] as String? ?? 'UNAVAILABLE');
      }
    } catch (error) {
      if (mounted) _failed(error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => PopScope(
    canPop: !_busy,
    child: Dialog(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 820, maxHeight: 760),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      widget.title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  IconButton(
                    onPressed: _busy ? null : () => Navigator.pop(context),
                    tooltip: _t('关闭', 'Close', '닫기'),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 12,
                runSpacing: 8,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  FilledButton.icon(
                    onPressed: _busy || !_sameScope ? null : _collect,
                    icon: const Icon(Icons.refresh),
                    label: Text(_t('获取评论', 'Collect comments', '댓글 가져오기')),
                  ),
                  FilterChip(
                    selected: _replies,
                    label: Text(_t('包含回复', 'Include replies', '답글 포함')),
                    onSelected: _busy || _attempted
                        ? null
                        : (v) => setState(() => _replies = v),
                  ),
                  TextButton(
                    onPressed: _busy ? null : _read,
                    child: Text(
                      _t('查看已存评论', 'Read saved comments', '저장된 댓글 읽기'),
                    ),
                  ),
                  if (_pageRef != null)
                    TextButton(
                      onPressed: _busy ? null : () => _read(exactPage: true),
                      child: Text(
                        _t('重开本次记录', 'Reopen this capture', '이번 기록 다시 열기'),
                      ),
                    ),
                ],
              ),
              if (_busy)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: LinearProgressIndicator(),
                ),
              if (_status != null)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  child: Semantics(
                    liveRegion: true,
                    child: Text(collectionStatusText(context, _status)),
                  ),
                ),
              if (_sourceVersion == 'RECORDED_SOURCE_VERSION')
                Text(
                  _t(
                    '原帖后来有更新，正在查看当时的评论记录。',
                    'The post has changed. These comments belong to the recorded version.',
                    '원문이 변경되었습니다. 당시 버전의 댓글 기록입니다.',
                  ),
                ),
              Flexible(
                child: _comments.isEmpty
                    ? Padding(
                        padding: const EdgeInsets.symmetric(vertical: 42),
                        child: Text(
                          _t('尚无已存评论', 'No saved comments', '저장된 댓글 없음'),
                          textAlign: TextAlign.center,
                        ),
                      )
                    : ListView.separated(
                        shrinkWrap: true,
                        itemCount: _comments.length,
                        separatorBuilder: (_, index) =>
                            const Divider(height: 32),
                        itemBuilder: (context, index) {
                          final row = _comments[index];
                          final reply =
                              row['parent_comment_id'] != null ||
                              row['reply_to_comment_id'] != null;
                          return Padding(
                            padding: EdgeInsets.only(left: reply ? 24 : 0),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Wrap(
                                  spacing: 14,
                                  runSpacing: 6,
                                  children: [
                                    Text(
                                      row['author_nickname'] as String? ??
                                          _t(
                                            '作者未提供',
                                            'Author not provided',
                                            '작성자 미제공',
                                          ),
                                      style: const TextStyle(
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                    if (reply)
                                      Text(
                                        _t('回复', 'Reply', '답글'),
                                        style: TextStyle(
                                          color: LumenisTheme.of(context).muted,
                                        ),
                                      ),
                                    Text(
                                      row['publish_datetime'] as String? ?? '—',
                                      style: TextStyle(
                                        color: LumenisTheme.of(context).muted,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 8),
                                SelectableText(row['content'] as String),
                                const SizedBox(height: 10),
                                Row(
                                  children: [
                                    const Icon(Icons.favorite_border, size: 16),
                                    const SizedBox(width: 6),
                                    Text(
                                      row['likes'] is num
                                          ? '${row['likes']}'
                                          : '—',
                                    ),
                                    if (row['state'] ==
                                        'LEGACY_COMMENT_NOT_VERIFIED') ...[
                                      const SizedBox(width: 18),
                                      Text(
                                        _t(
                                          '历史记录，来源待核',
                                          'Historical record; source unverified',
                                          '출처 미확인 과거 기록',
                                        ),
                                      ),
                                    ],
                                  ],
                                ),
                              ],
                            ),
                          );
                        },
                      ),
              ),
              if (_next != null || _continuation != null)
                Padding(
                  padding: const EdgeInsets.only(top: 16),
                  child: Wrap(
                    spacing: 12,
                    children: [
                      if (_next != null)
                        TextButton(
                          onPressed: _busy ? null : () => _read(more: true),
                          child: Text(
                            _t('更多已存评论', 'More saved comments', '저장된 댓글 더 보기'),
                          ),
                        ),
                      if (_continuation != null)
                        FilledButton.tonal(
                          onPressed: _busy ? null : () => _collect(more: true),
                          child: Text(
                            _t('继续获取', 'Continue collection', '계속 수집'),
                          ),
                        ),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    ),
  );
}
