import 'dart:async';

import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_icon.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';

class Acc03RecentWork extends StatefulWidget {
  const Acc03RecentWork({required this.client, this.onOpen, super.key});

  final LumenisCoreClient client;
  final void Function(String kind, String artifactId)? onOpen;

  @override
  State<Acc03RecentWork> createState() => _Acc03RecentWorkState();
}

class _Acc03RecentWorkState extends State<Acc03RecentWork> {
  List<_Work> _items = [];
  String? _cursor;
  bool _busy = false, _failed = false, _incomplete = false;
  int _generation = 0;
  final _usedCursors = <String>{};

  @override
  void initState() {
    super.initState();
    unawaited(_load());
  }

  @override
  void didUpdateWidget(covariant Acc03RecentWork oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!identical(oldWidget.client, widget.client)) unawaited(_load());
  }

  Future<void> _load({bool more = false}) async {
    if (more && (_busy || _cursor == null)) return;
    final generation = ++_generation;
    final cursor = more ? _cursor : null;
    setState(() {
      _busy = true;
      _failed = false;
      if (!more) {
        _items = [];
        _cursor = null;
        _incomplete = false;
        _usedCursors.clear();
      }
    });
    try {
      if (cursor != null && !_usedCursors.add(cursor)) {
        throw const FormatException('Repeated work cursor');
      }
      final response = await widget.client.listLatestSharedWork(cursor: cursor);
      if (!mounted || generation != _generation) return;
      final result = response['result'];
      if (response['ok'] != true ||
          result is! Map ||
          result['items'] is! List ||
          result['verification_complete'] is! bool ||
          result['has_more'] is! bool) {
        throw const FormatException('Invalid recent work');
      }
      final rows = <_Work>[];
      var incomplete = result['verification_complete'] != true;
      for (final raw in result['items'] as List) {
        final work = _Work.parse(raw);
        if (work == null) {
          incomplete = true;
        } else {
          rows.add(work);
        }
      }
      final next = result['next_cursor'];
      if (result['has_more'] == true &&
          (next is! String ||
              next.isEmpty ||
              next.length > 4096 ||
              next == cursor ||
              _usedCursors.contains(next))) {
        throw const FormatException('Invalid work continuation');
      }
      setState(() {
        final items = <String, _Work>{
          if (more)
            for (final item in _items) item.workId: item,
          for (final item in rows) item.workId: item,
        };
        _items = items.values.toList();
        _incomplete = (more && _incomplete) || incomplete;
        _cursor = result['has_more'] == true ? next as String : null;
      });
    } catch (_) {
      if (!mounted || generation != _generation) return;
      setState(() {
        _items = [];
        _cursor = null;
        _failed = true;
      });
    } finally {
      if (mounted && generation == _generation) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = LumenisTheme.of(context);
    return Column(
      key: const ValueKey('acc03-recent-work'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                _copy(context, '继续工作', 'Continue working', '이어서 작업'),
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: palette.foreground,
                ),
              ),
            ),
            IconButton(
              tooltip: _copy(context, '刷新', 'Refresh', '새로고침'),
              onPressed: _busy ? null : () => _load(),
              icon: const LumenisIcon(Icons.refresh_rounded, size: 18),
            ),
          ],
        ),
        if (_busy && _items.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 16),
            child: LinearProgressIndicator(minHeight: 2),
          ),
        if (_failed)
          TextButton.icon(
            onPressed: () => _load(),
            icon: const LumenisIcon(Icons.refresh_rounded, size: 16),
            label: Text(
              _copy(
                context,
                '暂时无法读取，重试',
                'Unable to read. Retry',
                '불러올 수 없습니다. 다시 시도',
              ),
            ),
          ),
        if (!_busy && !_failed && _items.isEmpty && !_incomplete)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Text(
              _copy(context, '还没有已保存的工作', 'No saved work yet', '저장된 작업이 없습니다'),
              style: TextStyle(color: palette.muted),
            ),
          ),
        for (final work in _items)
          Material(
            color: Colors.transparent,
            child: InkWell(
              key: ValueKey('acc03-resume-${work.id}'),
              onTap: widget.onOpen == null
                  ? null
                  : () => widget.onOpen!(work.kind, work.id),
              child: Container(
                padding: const EdgeInsets.symmetric(
                  vertical: 14,
                  horizontal: 4,
                ),
                decoration: BoxDecoration(
                  border: Border(top: BorderSide(color: palette.line)),
                ),
                child: Row(
                  children: [
                    LumenisIcon(
                      work.kind == 'research'
                          ? Icons.auto_stories_outlined
                          : Icons.article_outlined,
                      size: 25,
                      color: palette.muted,
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            work.title,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: palette.foreground,
                              fontSize: 16,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${_kind(context, work.kind)} · ${_copy(context, '版本', 'Version', '버전')} ${work.version}',
                            style: TextStyle(
                              color: palette.muted,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 12),
                    LumenisIcon(
                      Icons.arrow_forward_rounded,
                      size: 18,
                      color: palette.muted,
                    ),
                  ],
                ),
              ),
            ),
          ),
        if (_incomplete)
          Text(
            _copy(
              context,
              '部分工作暂时无法读取',
              'Some work is unavailable',
              '일부 작업을 불러올 수 없습니다',
            ),
            style: TextStyle(color: palette.caution, fontSize: 12),
          ),
        if (_cursor != null)
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton(
              onPressed: _busy ? null : () => _load(more: true),
              child: Text(_copy(context, '更多工作', 'More work', '더 보기')),
            ),
          ),
      ],
    );
  }
}

final class _Work {
  const _Work(this.id, this.workId, this.title, this.kind, this.version);
  final String id, workId, title, kind;
  final int version;

  static _Work? parse(Object? raw) {
    if (raw is! Map) return null;
    final artifact = raw['artifact'],
        doc = raw['document'],
        resume = raw['resume'];
    if (artifact is! Map || doc is! Map || resume is! Map) return null;
    final id = artifact['artifact_id'],
        workId = doc['work_id'],
        title = doc['title'],
        version = doc['version'],
        sha256 = artifact['sha256'],
        draftDigest = doc['draft_digest'];
    final context = doc['context'];
    if (id is! String ||
        !RegExp(r'^ART-[0-9a-f]{16}$').hasMatch(id) ||
        workId is! String ||
        !RegExp(r'^WORK-[0-9a-f]{24}$').hasMatch(workId) ||
        title is! String ||
        title.trim().isEmpty ||
        title.length > 300 ||
        version is! int ||
        version < 1 ||
        context is! Map ||
        context['scope_kind'] != 'shared_workspace' ||
        context['version'] != 1 ||
        context.keys.any(
          (key) => const {
            'domain_id',
            'product_id',
            'subject_id',
            'brand_focus_id',
            'global_scope',
          }.contains(key),
        ) ||
        doc['schema'] != 'lumenis.saved-work/v1' ||
        sha256 is! String ||
        !RegExp(r'^[0-9a-f]{64}$').hasMatch(sha256) ||
        draftDigest is! String ||
        !RegExp(r'^[0-9a-f]{64}$').hasMatch(draftDigest) ||
        resume['expected_draft_digest'] != draftDigest ||
        resume['artifact_id'] != id ||
        resume['work_id'] != workId ||
        resume['version'] != version ||
        resume['expected_sha256'] != artifact['sha256'] ||
        resume['state'] != 'ready_to_reopen' ||
        resume['execution'] != 'not_started') {
      return null;
    }
    final contract = doc['contract'];
    final payload = doc['payload'];
    final material = payload is Map ? payload['source_material'] : null;
    final kind = doc['kind'] == 'research'
        ? material is Map && material['origin'] == 'user-upload'
              ? 'material'
              : payload is Map && payload['source_brief_reference'] is Map
              ? 'research'
              : null
        : doc['kind'] == 'report' &&
              contract is Map &&
              contract['id'] == 'lumenis.internal-pitch' &&
              contract['version'] == '4'
        ? 'manuscript'
        : doc['kind'] == 'report'
        ? 'report'
        : null;
    return kind == null ? null : _Work(id, workId, title, kind, version);
  }
}

String _kind(BuildContext context, String kind) => switch (kind) {
  'manuscript' => _copy(context, '文稿', 'Manuscript', '원고'),
  'research' => _copy(context, '研究', 'Research', '리서치'),
  'material' => _copy(context, '资料', 'Material', '자료'),
  _ => _copy(context, '报告', 'Report', '보고서'),
};

String _copy(BuildContext context, String zh, String en, String ko) =>
    switch (context.lumenisL10n.locale.languageCode) {
      'en' => en,
      'ko' => ko,
      _ => zh,
    };
