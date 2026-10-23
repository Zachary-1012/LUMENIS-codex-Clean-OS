import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';

class Sys06PageContext extends StatefulWidget {
  const Sys06PageContext({
    required this.read,
    this.embedded = false,
    this.pageIdentity,
    this.onClose,
    super.key,
  });

  final bool embedded;
  final String? pageIdentity;
  final VoidCallback? onClose;

  final Future<Map<String, dynamic>> Function(String question) read;

  @override
  State<Sys06PageContext> createState() => _Sys06PageContextState();
}

class _Sys06PageContextState extends State<Sys06PageContext> {
  final _question = TextEditingController();
  Map<String, dynamic>? _result;
  String? _failure;
  bool _busy = false;
  bool _showAll = false;
  int _generation = 0;

  String _text(String zh, String en, String ko) =>
      switch (Localizations.localeOf(context).languageCode) {
        'zh' => zh,
        'ko' => ko,
        _ => en,
      };

  @override
  void didUpdateWidget(covariant Sys06PageContext oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.pageIdentity != oldWidget.pageIdentity) {
      _generation++;
      _result = null;
      _failure = null;
      _busy = false;
      _showAll = false;
    }
  }

  @override
  void dispose() {
    _question.dispose();
    super.dispose();
  }

  Future<void> _read() async {
    if (_busy || _question.text.trim().isEmpty) return;
    final question = _question.text.trim();
    final generation = ++_generation;
    setState(() {
      _showAll = false;
      _busy = true;
      _failure = null;
      _result = null;
    });
    try {
      final result = await widget.read(question);
      final page = result['page_context'];
      final metadata = result['metadata'];
      final formats = result['formats'];
      final body = formats is Map ? formats['text'] : null;
      if (result['ok'] != true ||
          page is! Map ||
          page['question'] != question ||
          page['excerpt'] is! String ||
          page['answer_state'] != 'NOT_GENERATED' ||
          page['content_kind'] != 'SOURCE_EXCERPT' ||
          metadata is! Map ||
          metadata['url'] is! String ||
          metadata['title'] is! String ||
          DateTime.tryParse('${metadata['captured_at']}') == null ||
          body is! Map ||
          body['success'] != true ||
          body['data'] is! String) {
        throw const FormatException('Page context is unavailable.');
      }
      if (mounted && generation == _generation) {
        setState(() => _result = result);
      }
    } catch (error) {
      if (!mounted || generation != _generation) return;
      final code = error is LumenisCoreException ? error.errorCode : null;
      setState(
        () => _failure = switch (code) {
          'BROWSER_CONTEXT_PAGE_REQUIRED' => _text(
            '先打开你要阅读的网页。',
            'Open the page you want to read first.',
            '먼저 읽을 페이지를 열어 주세요.',
          ),
          'BROWSER_EXTRACTION_PAGE_CHANGED' => _text(
            '页面已变化，请返回网页后重新读取。',
            'The page changed. Return to it and read again.',
            '페이지가 변경되었습니다. 돌아가서 다시 읽어 주세요.',
          ),
          'BROWSER_EXTRACTION_HUMAN_REQUIRED' => _text(
            '这个页面需要先完成登录或验证。',
            'Complete sign-in or verification on this page first.',
            '먼저 이 페이지에서 로그인 또는 인증을 완료해 주세요.',
          ),
          _ => _text(
            '暂时无法读取这个页面。你的问题已保留。',
            'This page could not be read. Your question is retained.',
            '페이지를 읽을 수 없습니다. 질문은 유지됩니다.',
          ),
        },
      );
    } finally {
      if (mounted && generation == _generation) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = LumenisTheme.of(context);
    final result = _result;
    final page = result?['page_context'] as Map?;
    final metadata = result?['metadata'] as Map?;
    final selection = page?['selection'] as Map?;
    final body = result?['formats']?['text']?['data'] as String?;
    final content = Padding(
      padding: const EdgeInsets.fromLTRB(22, 14, 22, 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  _text('这个网页', 'This page', '이 페이지'),
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              IconButton(
                onPressed: widget.onClose ?? () => Navigator.of(context).pop(),
                tooltip: _text('关闭', 'Close', '닫기'),
                icon: const Icon(Icons.close),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (result == null && !_busy && _failure == null) ...[
                    const SizedBox(height: 48),
                    Text(
                      _text('从当前网页开始', 'Start with this page', '현재 페이지에서 시작하기'),
                      textAlign: TextAlign.center,
                      style: TextStyle(color: theme.muted, fontSize: 14),
                    ),
                  ],
                  if (_busy) LinearProgressIndicator(color: theme.accent),
                  if (_failure != null)
                    Semantics(liveRegion: true, child: Text(_failure!)),
                  if (metadata != null) ...[
                    SelectableText(
                      page!['question'] as String,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 20),
                    SelectableText(
                      '${metadata['title']}',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 10),
                    SelectableText(
                      '${metadata['url']}',
                      style: TextStyle(color: theme.muted),
                    ),
                    Text(
                      DateTime.parse(
                        metadata['captured_at'] as String,
                      ).toLocal().toString(),
                      style: TextStyle(color: theme.muted),
                    ),
                    const SizedBox(height: 24),
                    Text(
                      _text('原文摘录', 'From the page', '페이지 원문'),
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 12),
                    if (selection?['matched_query_terms'] == 0)
                      Text(
                        _text(
                          '未找到与问题匹配的文字，以下为页面开头。',
                          'No matching words were found; this is the beginning of the page.',
                          '질문과 일치하는 단어가 없어 페이지 시작 부분을 표시합니다.',
                        ),
                      ),
                    SelectableText(
                      _showAll ? body! : page['excerpt'] as String,
                      style: const TextStyle(fontSize: 16, height: 1.65),
                    ),
                    if (body!.length > (page['excerpt'] as String).length)
                      TextButton(
                        onPressed: () => setState(() => _showAll = !_showAll),
                        child: Text(
                          _showAll
                              ? _text('收起', 'Show less', '접기')
                              : _text(
                                  '展开已读取内容',
                                  'Show captured text',
                                  '읽은 내용 펼치기',
                                ),
                        ),
                      ),
                    const SizedBox(height: 16),
                    Text(
                      _text(
                        '以上是网页原文，尚未生成分析或回答。',
                        'This is page text. An analysis or answer has not been generated.',
                        '위 내용은 페이지 원문입니다. 분석이나 답변은 아직 생성되지 않았습니다.',
                      ),
                      style: TextStyle(color: theme.muted),
                    ),
                    Text(
                      result!['truncated'] == true
                          ? _text(
                              '页面内容未读取完整。',
                              'Some page content was not captured.',
                              '페이지 내용의 일부를 읽지 못했습니다.',
                            )
                          : _text(
                              '仅包含当前已加载的正文；未读取嵌入页面或未加载内容。',
                              'Only loaded page text is included; embedded and unloaded content is excluded.',
                              '현재 로드된 본문만 포함하며 삽입된 페이지와 미로드 내용은 제외됩니다.',
                            ),
                      style: TextStyle(color: theme.muted),
                    ),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            key: const ValueKey('sys06-context-question'),
            controller: _question,
            minLines: 1,
            maxLines: 3,
            maxLength: 2000,
            onChanged: (_) => setState(() {}),
            decoration: InputDecoration(
              hintText: _text(
                '你想了解这个页面的什么？',
                'What do you want to find on this page?',
                '이 페이지에서 무엇을 알고 싶나요?',
              ),
              counterText: '',
              filled: true,
              fillColor: theme.surfaceRaised.withValues(alpha: 1),
              contentPadding: const EdgeInsets.fromLTRB(16, 16, 12, 16),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: BorderSide(color: theme.line),
              ),
              suffixIcon: IconButton(
                key: const ValueKey('sys06-context-read'),
                tooltip: _text('读取页面', 'Read page', '페이지 읽기'),
                onPressed: _busy || _question.text.trim().isEmpty
                    ? null
                    : _read,
                icon: const Icon(Icons.arrow_upward),
              ),
            ),
          ),
        ],
      ),
    );
    if (widget.embedded) return content;
    return Dialog(
      insetPadding: const EdgeInsets.all(20),
      child: SizedBox(
        width: 780,
        height: MediaQuery.sizeOf(context).height * .86,
        child: content,
      ),
    );
  }
}
