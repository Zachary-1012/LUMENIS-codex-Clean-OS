import 'package:flutter/material.dart';

import '../../../core/lumenis_botanical.dart';
import '../../../core/lumenis_theme.dart';
import '../../../core/lumenis_core_client.dart';

const creationLanguages = {
  'zh': '中文',
  'en': 'English',
  'ko': '한국어',
  'ja': '日本語',
  'fr': 'Français',
  'de': 'Deutsch',
  'es': 'Español',
  'pt': 'Português',
  'ru': 'Русский',
  'ar': 'العربية',
  'hi': 'हिन्दी',
  'id': 'Bahasa Indonesia',
};

class CreationBriefDialog extends StatefulWidget {
  const CreationBriefDialog({
    super.key,
    required this.initialTitle,
    required this.language,
    required this.sections,
    required this.onCreate,
    this.initial = const {},
    this.client,
  });
  final String initialTitle, language;
  final List<Map<String, String>> sections;
  final Map<String, dynamic> initial;
  final LumenisCoreClient? client;
  final Future<String?> Function(Map<String, dynamic>) onCreate;
  @override
  State<CreationBriefDialog> createState() => _CreationBriefDialogState();
}

class _CreationBriefDialogState extends State<CreationBriefDialog> {
  late final _title = TextEditingController(
    text: widget.initial['title'] as String? ?? widget.initialTitle,
  );
  late final _question = TextEditingController(
    text: widget.initial['question'] as String? ?? '',
  );
  late final _audience = TextEditingController(
    text: widget.initial['audience'] as String? ?? '',
  );
  late final _brand = TextEditingController(
    text: widget.initial['brand'] as String? ?? '',
  );
  late final _tone = TextEditingController(
    text: widget.initial['tone'] as String? ?? '',
  );
  late final _constraints = TextEditingController(
    text: (widget.initial['constraints'] as List? ?? []).join('\n'),
  );
  late String _language = widget.language;
  final _selected = <String>{};
  bool _busy = false;
  String? _error;
  bool _loadingSources = false;
  bool _sourcesLoaded = false;
  String? _sourceCursor;
  final _sources = <Map<String, String>>[];
  final _sourceSelection = <String>{};

  Future<void> _loadSources({bool more = false}) async {
    if (_loadingSources || widget.client == null) return;
    setState(() => _loadingSources = true);
    try {
      final response = await widget.client!.listSharedDocumentImports(
        cursor: more ? _sourceCursor : null,
      );
      final data = response['result'];
      if (response['ok'] != true || data is! Map) throw const FormatException();
      final items = data['items'];
      if (items is! List) throw const FormatException();
      final sources = <Map<String, String>>[];
      for (final item in items) {
        if (item is! Map) throw const FormatException();
        final artifact = item['artifact'];
        final document = item['document'];
        if (artifact is! Map ||
            document is! Map ||
            artifact['artifact_id'] is! String ||
            artifact['sha256'] is! String ||
            document['title'] is! String) {
          throw const FormatException();
        }
        if (!RegExp(
              r'^ART-[a-f0-9]{16}$',
            ).hasMatch(artifact['artifact_id'] as String) ||
            !RegExp(r'^[a-f0-9]{64}$').hasMatch(artifact['sha256'] as String)) {
          throw const FormatException();
        }
        sources.add({
          'artifact_id': artifact['artifact_id'] as String,
          'sha256': artifact['sha256'] as String,
          'title': document['title'] as String,
        });
      }
      if (!mounted) return;
      setState(() {
        if (!more) {
          _sources.clear();
          _sourceSelection.clear();
        }
        _sources.addAll(
          sources.where(
            (s) =>
                !_sources.any((old) => old['artifact_id'] == s['artifact_id']),
          ),
        );
        _sourceCursor = data['has_more'] == true
            ? data['next_cursor'] as String?
            : null;
        _sourcesLoaded = true;
        _error = null;
      });
    } catch (_) {
      if (mounted) {
        setState(
          () => _error = _t(
            '资料读取失败，已选择的内容保持不变。',
            'Could not read the library. Your selection is unchanged.',
            '자료를 읽지 못했습니다. 선택 내용은 유지됩니다.',
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _loadingSources = false);
    }
  }

  String _t(String zh, String en, String ko) =>
      switch (Localizations.localeOf(context).languageCode) {
        'en' => en,
        'ko' => ko,
        _ => zh,
      };
  @override
  void dispose() {
    for (final c in [
      _title,
      _question,
      _audience,
      _brand,
      _tone,
      _constraints,
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _create() async {
    if (_busy) return;
    final constraints = _constraints.text
        .split('\n')
        .map((s) => s.trim())
        .where((s) => s.isNotEmpty)
        .toList();
    if (_title.text.trim().isEmpty ||
        _question.text.trim().isEmpty ||
        _title.text.runes.length > 300 ||
        _question.text.runes.length > 12000 ||
        [_audience, _brand, _tone].any((c) => c.text.runes.length > 300) ||
        constraints.length > 64 ||
        (widget.sections.isNotEmpty && _selected.isEmpty)) {
      setState(
        () => _error = _t(
          '请填写标题和创作要求，并选择需要修改的段落。',
          'Enter a title and brief, and select sections when revising.',
          '제목과 요청을 입력하고 수정할 문단을 선택하세요.',
        ),
      );
      return;
    }
    final brief = <String, dynamic>{
      'title': _title.text.trim(),
      'question': _question.text.trim(),
      'language': _language,
      if (_audience.text.trim().isNotEmpty) 'audience': _audience.text.trim(),
      if (_brand.text.trim().isNotEmpty) 'brand': _brand.text.trim(),
      if (_tone.text.trim().isNotEmpty) 'tone': _tone.text.trim(),
      if (constraints.isNotEmpty) 'constraints': constraints,
    };
    setState(() {
      _busy = true;
      _error = null;
    });
    String? error;
    try {
      error = await widget.onCreate({
        'brief': brief,
        if (_selected.isNotEmpty) 'selected_section_ids': _selected.toList(),
        if (_sourceSelection.isNotEmpty)
          'source_artifacts': [
            for (final row in _sources)
              if (_sourceSelection.contains(row['artifact_id']))
                {'artifact_id': row['artifact_id'], 'sha256': row['sha256']},
          ],
      });
    } catch (_) {
      error = _t(
        '操作未完成，要求已保留。',
        'Could not finish. Your brief is retained.',
        '완료하지 못했습니다. 요청은 유지됩니다.',
      );
    }
    if (!mounted) return;
    if (error == null) {
      Navigator.pop(context, brief);
    } else {
      setState(() {
        _busy = false;
        _error = error;
      });
    }
  }

  @override
  Widget build(BuildContext context) => PopScope(
    canPop: !_busy,
    child: Dialog(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 720, maxHeight: 820),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  const LumenisBotanical(plant: LumenisPlant.jasmine, size: 38),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Text(
                      widget.sections.isEmpty
                          ? _t('开始创作', 'Create a draft', '초안 만들기')
                          : _t(
                              '修改选定段落',
                              'Revise selected sections',
                              '선택한 문단 수정',
                            ),
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
              const SizedBox(height: 18),
              Flexible(
                child: SingleChildScrollView(
                  child: AbsorbPointer(
                    absorbing: _busy,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        TextField(
                          controller: _title,
                          decoration: InputDecoration(
                            labelText: _t('标题', 'Title', '제목'),
                          ),
                        ),
                        const SizedBox(height: 16),
                        TextField(
                          controller: _question,
                          minLines: 5,
                          maxLines: 10,
                          decoration: InputDecoration(
                            labelText: _t(
                              '要写什么，给谁看，需要达成什么',
                              'What to create, who it is for, and what it should achieve',
                              '무엇을, 누구를 위해, 어떤 목적으로 만들까요',
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                        DropdownButtonFormField<String>(
                          initialValue: _language,
                          decoration: InputDecoration(
                            labelText: _t('作品语言', 'Content language', '콘텐츠 언어'),
                          ),
                          items: [
                            for (final item in creationLanguages.entries)
                              DropdownMenuItem(
                                value: item.key,
                                child: Text(item.value),
                              ),
                          ],
                          onChanged: (value) {
                            if (value != null) {
                              setState(() => _language = value);
                            }
                          },
                        ),
                        ExpansionTile(
                          title: Text(
                            _t(
                              '受众、品牌与要求',
                              'Audience, brand and constraints',
                              '독자, 브랜드와 조건',
                            ),
                          ),
                          children: [
                            for (final field in [
                              (_audience, _t('受众', 'Audience', '독자')),
                              (_brand, _t('品牌', 'Brand', '브랜드')),
                              (_tone, _t('语气', 'Tone', '어조')),
                              (
                                _constraints,
                                _t(
                                  '必须遵守的要求，每行一条',
                                  'Constraints, one per line',
                                  '준수할 조건, 한 줄에 하나',
                                ),
                              ),
                            ])
                              Padding(
                                padding: const EdgeInsets.only(bottom: 12),
                                child: TextField(
                                  controller: field.$1,
                                  minLines: 1,
                                  maxLines: field.$1 == _constraints ? 5 : 1,
                                  decoration: InputDecoration(
                                    labelText: field.$2,
                                  ),
                                ),
                              ),
                          ],
                        ),
                        if (widget.client != null)
                          ExpansionTile(
                            title: Text(
                              _t('参考资料', 'Reference materials', '참고 자료'),
                            ),
                            onExpansionChanged: (open) {
                              if (open && !_sourcesLoaded) _loadSources();
                            },
                            children: [
                              if (_loadingSources)
                                const LinearProgressIndicator(),
                              if (_sourcesLoaded && _sources.isEmpty)
                                Padding(
                                  padding: const EdgeInsets.all(12),
                                  child: Text(
                                    _t(
                                      '资料库还没有文件',
                                      'No files in your library yet',
                                      '자료실에 파일이 없습니다',
                                    ),
                                  ),
                                ),
                              for (final row in _sources)
                                CheckboxListTile(
                                  contentPadding: EdgeInsets.zero,
                                  title: Text(row['title']!),
                                  value: _sourceSelection.contains(
                                    row['artifact_id'],
                                  ),
                                  onChanged:
                                      _busy ||
                                          (_sourceSelection.length >= 16 &&
                                              !_sourceSelection.contains(
                                                row['artifact_id'],
                                              ))
                                      ? null
                                      : (value) => setState(() {
                                          if (value == true) {
                                            _sourceSelection.add(
                                              row['artifact_id']!,
                                            );
                                          } else {
                                            _sourceSelection.remove(
                                              row['artifact_id'],
                                            );
                                          }
                                        }),
                                ),
                              if (_sourceCursor != null)
                                TextButton(
                                  onPressed: _loadingSources || _busy
                                      ? null
                                      : () => _loadSources(more: true),
                                  child: Text(
                                    _t('更多资料', 'More materials', '자료 더 보기'),
                                  ),
                                ),
                              if (!_sourcesLoaded && !_loadingSources)
                                TextButton(
                                  onPressed: _loadSources,
                                  child: Text(
                                    _t('重新读取', 'Read again', '다시 읽기'),
                                  ),
                                ),
                            ],
                          ),
                        if (widget.sections.isNotEmpty) ...[
                          const Divider(height: 24),
                          for (final section in widget.sections)
                            CheckboxListTile(
                              contentPadding: EdgeInsets.zero,
                              title: Text(section['heading']!),
                              subtitle: Text(
                                section['body']!,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                              ),
                              value: _selected.contains(section['section_id']),
                              onChanged: (value) => setState(() {
                                if (value == true) {
                                  _selected.add(section['section_id']!);
                                } else {
                                  _selected.remove(section['section_id']);
                                }
                              }),
                            ),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Semantics(
                    liveRegion: true,
                    child: Text(
                      _error!,
                      style: TextStyle(color: LumenisTheme.of(context).danger),
                    ),
                  ),
                ),
              const SizedBox(height: 18),
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton.icon(
                  onPressed: _busy ? null : _create,
                  icon: Icon(
                    widget.sections.isEmpty
                        ? Icons.auto_awesome_outlined
                        : Icons.edit_note,
                  ),
                  label: Text(
                    _busy
                        ? _t('正在处理…', 'Working…', '처리 중…')
                        : _t('开始', 'Start', '시작'),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}
