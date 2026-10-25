import 'dart:convert';

import 'package:flutter/material.dart';

import '../../core/lumenis_core_client.dart';
import '../../l10n/lumenis_localizations.dart';
import 'ai01_conversations.dart';

class Ai01SourcePicker extends StatefulWidget {
  const Ai01SourcePicker({
    required this.repository,
    required this.conversationId,
    super.key,
  });
  final Ai01ConversationSources repository;
  final String conversationId;

  @override
  State<Ai01SourcePicker> createState() => _Ai01SourcePickerState();
}

class _Ai01SourcePickerState extends State<Ai01SourcePicker> {
  final _query = TextEditingController();
  List<Map<String, dynamic>> _records = [];
  Map<String, dynamic>? _preview;
  TextSelection? _selection;
  String? _snapshot;
  String? _submittedQuery;
  int? _next;
  bool _busy = false;
  String? _error;
  int _request = 0;

  String _text(String zh, String en, String ko) =>
      switch (context.lumenisL10n.locale.languageCode) {
        'en' => en,
        'ko' => ko,
        _ => zh,
      };

  Future<void> _search({bool more = false}) async {
    final query = more ? _submittedQuery : _query.text.trim();
    if (_busy || query == null || query.isEmpty || (more && _next == null)) {
      return;
    }
    final request = ++_request;
    setState(() {
      _busy = true;
      _error = null;
      _preview = null;
      _selection = null;
    });
    try {
      final result = await widget.repository
          .sourceQuery(widget.conversationId, {
            'query': query,
            'limit': '12',
            if (more) 'offset': '$_next',
            if (more && _snapshot != null) 'snapshot': _snapshot!,
          });
      if (!mounted || request != _request) return;
      final search = result['search'];
      if (result['ok'] != true ||
          search is! Map ||
          search['records'] is! List ||
          search['has_more'] is! bool ||
          search['verification_complete'] is! bool) {
        throw const FormatException('Invalid source search.');
      }
      final records = (search['records'] as List)
          .map((raw) => _validate(raw))
          .toList();
      final next = search['next_offset'];
      if (search['has_more'] == true && next is! int) {
        throw const FormatException('Invalid source cursor.');
      }
      final retrieval = search['retrieval'];
      _snapshot = retrieval is Map
          ? retrieval['source_snapshot_sha256'] as String?
          : null;
      _records = more ? [..._records, ...records] : records;
      _next = search['has_more'] == true ? next as int : null;
      _submittedQuery = query;
      if (search['verification_complete'] != true) {
        _error = _text(
          '部分资料暂时无法读取',
          'Some materials could not be read',
          '일부 자료를 읽을 수 없습니다',
        );
      }
    } catch (error) {
      if (!mounted || request != _request) return;
      _failed(error);
    } finally {
      if (mounted && request == _request) setState(() => _busy = false);
    }
  }

  Map<String, dynamic> _validate(dynamic raw) {
    if (raw is! Map || raw['reference'] is! Map || raw['state'] is! String) {
      throw const FormatException('Invalid source.');
    }
    final item = Map<String, dynamic>.from(raw);
    if (item['state'] == 'available' &&
        (item['text'] is! String ||
            item['title'] is! String ||
            item['offset_unit'] != 'unicode_codepoint' ||
            item['character_count'] is! int)) {
      throw const FormatException('Invalid source text.');
    }
    return item;
  }

  void _failed(Object error) {
    if (error is LumenisCoreException &&
        const [401, 403, 404, 410].contains(error.statusCode)) {
      _records = [];
      _preview = null;
      _selection = null;
      _next = null;
      _error = _text(
        '资料已不可访问',
        'Materials are no longer accessible',
        '자료에 더 이상 접근할 수 없습니다',
      );
    } else if (error is LumenisCoreException && error.statusCode == 409) {
      _records = [];
      _next = null;
      _snapshot = null;
      _error = _text(
        '资料已更新，请重新搜索',
        'Materials changed. Search again.',
        '자료가 변경되었습니다. 다시 검색하세요.',
      );
    } else {
      _error = _text(
        '未能读取，请重试',
        'Could not read. Try again.',
        '읽지 못했습니다. 다시 시도하세요.',
      );
    }
  }

  Future<void> _open(Map<String, dynamic> record, {int start = 0}) async {
    if (_busy || record['state'] != 'available') return;
    final request = ++_request;
    setState(() {
      _busy = true;
      _error = null;
      _selection = null;
      _preview = null;
    });
    try {
      final reference = Map<String, dynamic>.from(record['reference'] as Map);
      reference['start'] = start;
      reference['end'] = (start + 64000).clamp(
        start,
        record['character_count'] as int,
      );
      final response = await widget.repository.sourceQuery(
        widget.conversationId,
        {'source_reference': jsonEncode(reference)},
      );
      if (!mounted || request != _request) return;
      if (response['ok'] != true) {
        throw const FormatException('Invalid source preview.');
      }
      _preview = _validate(response['source_preview']);
    } catch (error) {
      if (!mounted || request != _request) return;
      _failed(error);
    } finally {
      if (mounted && request == _request) setState(() => _busy = false);
    }
  }

  void _adopt() {
    final preview = _preview;
    if (_busy || preview == null || preview['state'] != 'available') return;
    final reference = Map<String, dynamic>.from(preview['reference'] as Map);
    final selected = _selection;
    if (selected != null && selected.isValid && !selected.isCollapsed) {
      final text = preview['text'] as String;
      final offset = reference['start'] as int;
      reference['start'] =
          offset + text.substring(0, selected.start).runes.length;
      reference['end'] = offset + text.substring(0, selected.end).runes.length;
    }
    Navigator.of(
      context,
    ).pop(<String, dynamic>{...preview, 'reference': reference});
  }

  @override
  void dispose() {
    _request++;
    _query.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final preview = _preview;
    final selected = _selection != null && !_selection!.isCollapsed;
    return AlertDialog(
      title: Text(_text('参考资料', 'Reference materials', '참고 자료')),
      content: SizedBox(
        width: 720,
        height: MediaQuery.sizeOf(context).height * .62,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _query,
                    enabled: !_busy,
                    onSubmitted: (_) => _search(),
                    decoration: InputDecoration(
                      labelText: _text('搜索资料', 'Search materials', '자료 검색'),
                    ),
                  ),
                ),
                IconButton(
                  onPressed: _busy ? null : () => _search(),
                  tooltip: _text('搜索', 'Search', '검색'),
                  icon: const Icon(Icons.search),
                ),
              ],
            ),
            if (_busy) const LinearProgressIndicator(),
            if (_error != null)
              Semantics(
                liveRegion: true,
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: Text(_error!),
                ),
              ),
            if (preview != null) ...[
              Row(
                children: [
                  IconButton(
                    onPressed: () => setState(() {
                      _preview = null;
                      _selection = null;
                    }),
                    tooltip: _text('返回', 'Back', '뒤로'),
                    icon: const Icon(Icons.arrow_back),
                  ),
                  Expanded(
                    child: Text(
                      preview['state'] == 'available'
                          ? preview['title'] as String
                          : _text('资料不可用', 'Material unavailable', '자료 사용 불가'),
                      maxLines: 2,
                    ),
                  ),
                ],
              ),
              Expanded(
                child: SingleChildScrollView(
                  child: SelectableText(
                    preview['state'] == 'available'
                        ? preview['text'] as String
                        : '',
                    onSelectionChanged: (selection, _) =>
                        setState(() => _selection = selection),
                  ),
                ),
              ),
              if (preview['state'] == 'available' &&
                  (preview['reference'] as Map)['end'] <
                      preview['character_count'])
                TextButton(
                  onPressed: _busy
                      ? null
                      : () => _open(
                          preview,
                          start: (preview['reference'] as Map)['end'] as int,
                        ),
                  child: Text(_text('继续阅读', 'Read next section', '다음 부분 읽기')),
                ),
            ] else
              Expanded(
                child: ListView(
                  children: [
                    for (final record in _records)
                      ListTile(
                        title: Text(
                          record['state'] == 'available'
                              ? record['title'] as String
                              : _text(
                                  '资料不可用',
                                  'Material unavailable',
                                  '자료 사용 불가',
                                ),
                        ),
                        subtitle: record['state'] == 'available'
                            ? Text(
                                record['text'] as String,
                                maxLines: 3,
                                overflow: TextOverflow.ellipsis,
                              )
                            : null,
                        onTap: record['state'] == 'available' && !_busy
                            ? () => _open(record)
                            : null,
                        trailing: const Icon(Icons.chevron_right),
                      ),
                    if (_submittedQuery != null &&
                        _records.isEmpty &&
                        !_busy &&
                        _error == null)
                      Padding(
                        padding: const EdgeInsets.all(24),
                        child: Text(
                          _text(
                            '没有匹配的资料',
                            'No matching materials',
                            '일치하는 자료가 없습니다',
                          ),
                        ),
                      ),
                    if (_next != null)
                      TextButton(
                        onPressed: _busy ? null : () => _search(more: true),
                        child: Text(_text('加载更多', 'Load more', '더 보기')),
                      ),
                  ],
                ),
              ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(context.lumenisL10n.text('common.cancel')),
        ),
        FilledButton(
          onPressed: preview?['state'] == 'available' && !_busy ? _adopt : null,
          child: Text(
            selected
                ? _text('采用选中文字', 'Use selected text', '선택한 텍스트 사용')
                : _text('采用这部分', 'Use this section', '이 부분 사용'),
          ),
        ),
      ],
    );
  }
}
