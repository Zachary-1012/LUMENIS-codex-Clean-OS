import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'shared_research_repository.dart';

String _copy(BuildContext context, String zh, String en, String ko) =>
    switch (context.lumenisL10n.locale.languageCode) {
      'en' => en,
      'ko' => ko,
      _ => zh,
    };

Future<void> openSharedResearch(
  BuildContext context, {
  required SharedResearchRepository repository,
  required Map<String, String> sources,
}) => Navigator.of(context).push<void>(
  MaterialPageRoute(
    builder: (_) =>
        SharedResearchWorkspace(repository: repository, sources: sources),
  ),
);

class SharedResearchWorkspace extends StatefulWidget {
  const SharedResearchWorkspace({
    super.key,
    required this.repository,
    required this.sources,
  });
  final SharedResearchRepository repository;
  final Map<String, String> sources;
  @override
  State<SharedResearchWorkspace> createState() =>
      _SharedResearchWorkspaceState();
}

class _SharedResearchWorkspaceState extends State<SharedResearchWorkspace> {
  final _question = TextEditingController();
  final _title = TextEditingController();
  final _body = TextEditingController();
  final _selected = <String>{};
  List<SharedResearchDocument> _history = [];
  List<SharedResearchTask> _tasks = [];
  String? _historyCursor, _taskCursor;
  SharedResearchDocument? _opened;
  SharedResearchTask? _task;
  bool _busy = false, _loading = true, _incomplete = false, _allowPop = false;
  bool _editing = false;
  String? _notice;
  Future<void> Function()? _pending;
  Timer? _poll;
  int _generation = 0;
  bool get _dirty =>
      _opened != null &&
      (_title.text != _opened!.title || _body.text != _opened!.markdown);
  String _requestId() =>
      'research_${DateTime.now().microsecondsSinceEpoch}_${Random.secure().nextInt(1 << 30)}';

  @override
  void initState() {
    super.initState();
    _selected.addAll(widget.sources.keys.take(100));
    unawaited(_load());
  }

  @override
  void dispose() {
    _poll?.cancel();
    _question.dispose();
    _title.dispose();
    _body.dispose();
    super.dispose();
  }

  Future<void> _load({bool moreHistory = false, bool moreTasks = false}) async {
    if (_busy) return;
    final generation = _generation;
    setState(() {
      _loading = true;
      _notice = null;
    });
    try {
      final history = await widget.repository.history(
        cursor: moreHistory ? _historyCursor : null,
      );
      final tasks = await widget.repository.tasks(
        cursor: moreTasks ? _taskCursor : null,
      );
      if (!mounted || generation != _generation) return;
      setState(() {
        _history = moreHistory
            ? [..._history, ...history.items]
            : history.items;
        _tasks = moreTasks ? [..._tasks, ...tasks.items] : tasks.items;
        _historyCursor = history.cursor;
        _taskCursor = tasks.cursor;
        _incomplete = history.incomplete;
      });
    } catch (error) {
      if (mounted) _error(error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _error(Object error) {
    _poll?.cancel();
    final restricted =
        error is LumenisCoreException &&
        const {401, 403, 404, 409, 410}.contains(error.statusCode);
    setState(() {
      if (restricted) {
        _generation++;
        _opened = null;
        _task = null;
        _title.clear();
        _body.clear();
        _pending = null;
        _history = [];
        _tasks = [];
      }
      _notice = restricted
          ? _copy(
              context,
              '资料或版本已变化，请重新读取。',
              'The source or version changed. Read it again.',
              '자료 또는 버전이 변경되었습니다. 다시 읽어 주세요.',
            )
          : _copy(
              context,
              '暂时无法确认结果。请重试读取或核对本次保存。',
              'The result could not be confirmed. Read again or check this save.',
              '결과를 확인하지 못했습니다. 다시 읽거나 저장 결과를 확인해 주세요.',
            );
    });
  }

  Future<bool> _leaveDraft() async {
    if (!_dirty && _pending == null) return true;
    return await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: Text(
              _copy(context, '离开当前编辑？', 'Leave this edit?', '편집을 나갈까요?'),
            ),
            content: Text(
              _copy(
                context,
                '未保存的编辑将丢失。已提交的工作可从记录重新打开。',
                'Unsaved edits will be lost. Submitted work can be reopened from history.',
                '저장하지 않은 편집은 사라집니다. 제출한 작업은 기록에서 다시 열 수 있습니다.',
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: Text(_copy(context, '继续编辑', 'Keep editing', '계속 편집')),
              ),
              TextButton(
                onPressed: () => Navigator.pop(context, true),
                child: Text(_copy(context, '离开', 'Leave', '나가기')),
              ),
            ],
          ),
        ) ??
        false;
  }

  Future<void> _close() async {
    if (_busy || !await _leaveDraft() || !mounted) return;
    setState(() => _allowPop = true);
    Navigator.of(context).pop();
  }

  void _showDocument(SharedResearchDocument item) {
    _opened = item;
    _editing = false;
    _task = null;
    _title.text = item.title;
    _body.text = item.markdown;
    _notice = null;
    _poll?.cancel();
  }

  Future<void> _open(SharedResearchDocument item) async {
    if (_busy || !await _leaveDraft() || !mounted) return;
    final generation = ++_generation;
    _poll?.cancel();
    setState(() {
      _busy = true;
      _opened = null;
      _task = null;
      _body.clear();
      _title.clear();
      _pending = null;
    });
    try {
      final current = await widget.repository.open(item.id);
      if (!mounted || generation != _generation) return;
      setState(() => _showDocument(current));
    } catch (error) {
      if (mounted && generation == _generation) _error(error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _showTask(SharedResearchTask task) {
    _task = task;
    _editing = false;
    _tasks = [task, ..._tasks.where((item) => item.id != task.id)];
    _opened = null;
    _title.text = task.question;
    _body.text = task.markdown ?? '';
    _notice = null;
    _poll?.cancel();
    if (task.state == 'pending' || task.state == 'running') {
      _poll = Timer(
        const Duration(seconds: 2),
        () => unawaited(_readTask(task.id)),
      );
    }
  }

  Future<void> _readTask(
    String id, {
    bool resume = false,
    bool select = false,
  }) async {
    if (_busy || (select && !await _leaveDraft()) || !mounted) return;
    final generation = ++_generation;
    setState(() {
      _busy = true;
      if (select) _pending = null;
    });
    try {
      final task = await widget.repository.task(id, resume: resume);
      if (!mounted || generation != _generation) return;
      setState(() => _showTask(task));
    } catch (error) {
      if (mounted && generation == _generation) _error(error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _runPending() async {
    final operation = _pending;
    if (_busy || operation == null) return;
    setState(() {
      _busy = true;
      _notice = null;
    });
    try {
      await operation();
      if (mounted) setState(() => _pending = null);
    } catch (error) {
      if (mounted) _error(error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
    if (mounted && _pending == null) await _load();
  }

  Future<void> _start() async {
    final question = _question.text.trim();
    if (_busy || _pending != null || question.length < 4 || _selected.isEmpty) {
      return;
    }
    if (!await _leaveDraft() || !mounted) return;
    final requestId = _requestId(), sources = _selected.toList(growable: false);
    _poll?.cancel();
    ++_generation;
    _pending = () async {
      final task = await widget.repository.start(question, sources, requestId);
      if (mounted) setState(() => _showTask(task));
    };
    await _runPending();
  }

  Future<void> _save() async {
    if (_busy || _pending != null) return;
    final parent = _opened,
        task = _task,
        title = _title.text.trim(),
        body = _body.text;
    final requestId = _requestId();
    if (parent != null && (!_dirty || title.isEmpty || body.trim().isEmpty)) {
      return;
    }
    _pending = () async {
      final item = parent != null
          ? await widget.repository.revise(parent, title, body, requestId)
          : await widget.repository.save(task!, requestId);
      if (mounted) setState(() => _showDocument(item));
    };
    await _runPending();
  }

  @override
  Widget build(BuildContext context) {
    final theme = LumenisTheme.of(context);
    return PopScope(
      canPop: _allowPop,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) unawaited(_close());
      },
      child: Scaffold(
        backgroundColor: theme.canvas,
        appBar: AppBar(
          backgroundColor: theme.canvas,
          leading: IconButton(
            tooltip: _copy(context, '返回资料库', 'Back to library', '자료실로 돌아가기'),
            onPressed: _busy ? null : _close,
            icon: const Icon(Icons.arrow_back_rounded),
          ),
          title: Text(_copy(context, '研究', 'Research', '연구')),
          actions: [
            IconButton(
              tooltip: _copy(context, '刷新记录', 'Refresh history', '기록 새로고침'),
              onPressed: _loading || _busy ? null : () => _load(),
              icon: const Icon(Icons.refresh_rounded),
            ),
          ],
        ),
        body: SafeArea(
          child: LayoutBuilder(
            builder: (context, box) {
              final side = _sidebar(context);
              final paper = _paper(context);
              return box.maxWidth >= 980
                  ? Row(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        SizedBox(width: 300, child: side),
                        VerticalDivider(width: 1, color: theme.line),
                        Expanded(child: paper),
                      ],
                    )
                  : DefaultTabController(
                      length: 2,
                      child: Column(
                        children: [
                          TabBar(
                            tabs: [
                              Tab(
                                text: _copy(
                                  context,
                                  '资料与记录',
                                  'Sources & history',
                                  '자료와 기록',
                                ),
                              ),
                              Tab(
                                text: _copy(
                                  context,
                                  '当前工作',
                                  'Current work',
                                  '현재 작업',
                                ),
                              ),
                            ],
                          ),
                          Expanded(child: TabBarView(children: [side, paper])),
                        ],
                      ),
                    );
            },
          ),
        ),
      ),
    );
  }

  Widget _sidebar(BuildContext context) => ListView(
    padding: const EdgeInsets.all(20),
    children: [
      Text(
        _copy(context, '选择资料', 'Choose sources', '자료 선택'),
        style: Theme.of(context).textTheme.titleMedium,
      ),
      for (final entry in widget.sources.entries)
        CheckboxListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          controlAffinity: ListTileControlAffinity.leading,
          value: _selected.contains(entry.key),
          title: Text(
            entry.value,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          onChanged: _busy || _pending != null
              ? null
              : (value) => setState(() {
                  value == true
                      ? _selected.add(entry.key)
                      : _selected.remove(entry.key);
                }),
        ),
      if (widget.sources.isEmpty)
        Text(
          _copy(
            context,
            '先在资料库导入文件。',
            'Import a file in the library first.',
            '자료실에서 파일을 먼저 가져오세요.',
          ),
        ),
      const SizedBox(height: 18),
      TextField(
        controller: _question,
        maxLength: 1500,
        minLines: 2,
        maxLines: 5,
        enabled: !_busy && _pending == null,
        decoration: InputDecoration(
          labelText: _copy(
            context,
            '想了解什么？',
            'What would you like to know?',
            '무엇을 알아볼까요?',
          ),
        ),
        onChanged: (_) => setState(() {}),
      ),
      FilledButton.icon(
        onPressed:
            _busy ||
                _pending != null ||
                _selected.isEmpty ||
                _question.text.trim().length < 4
            ? null
            : _start,
        icon: const Icon(Icons.arrow_forward_rounded),
        label: Text(_copy(context, '开始研究', 'Start research', '연구 시작')),
      ),
      const SizedBox(height: 28),
      Text(
        _copy(context, '工作记录', 'Work history', '작업 기록'),
        style: Theme.of(context).textTheme.titleMedium,
      ),
      if (_loading) const LinearProgressIndicator(minHeight: 2),
      for (final task in _tasks)
        ListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(
            task.question,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          subtitle: Text(_taskState(context, task.state)),
          leading: const Icon(Icons.notes_rounded, size: 18),
          onTap: _busy ? null : () => _readTask(task.id, select: true),
        ),
      if (_taskCursor != null)
        TextButton(
          onPressed: _loading || _busy ? null : () => _load(moreTasks: true),
          child: Text(_copy(context, '更多工作', 'More work', '더 많은 작업')),
        ),
      const SizedBox(height: 22),
      Text(
        _copy(context, '已保存版本', 'Saved versions', '저장된 버전'),
        style: Theme.of(context).textTheme.titleMedium,
      ),
      for (final item in _history)
        ListTile(
          contentPadding: EdgeInsets.zero,
          selected: _opened?.id == item.id,
          title: Text(item.title, maxLines: 2, overflow: TextOverflow.ellipsis),
          subtitle: Text(
            '${_copy(context, '版本', 'Version', '버전')} ${item.version} · ${_date(item.createdAt)}',
          ),
          onTap: _busy ? null : () => _open(item),
        ),
      if (_historyCursor != null)
        TextButton(
          onPressed: _loading || _busy ? null : () => _load(moreHistory: true),
          child: Text(_copy(context, '更多版本', 'More versions', '더 많은 버전')),
        ),
      if (_incomplete)
        Text(
          _copy(
            context,
            '部分版本暂时无法读取。',
            'Some versions cannot be read right now.',
            '일부 버전을 지금 읽을 수 없습니다.',
          ),
        ),
    ],
  );

  Widget _paper(BuildContext context) {
    final task = _task;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (_busy) const LinearProgressIndicator(minHeight: 2),
        if (_notice != null)
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
            child: Semantics(liveRegion: true, child: Text(_notice!)),
          ),
        if (_pending != null && !_busy)
          Align(
            alignment: Alignment.centerLeft,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: OutlinedButton(
                onPressed: _runPending,
                child: Text(
                  _copy(context, '核对本次操作', 'Check this operation', '이번 작업 확인'),
                ),
              ),
            ),
          ),
        if (task != null)
          Padding(
            padding: const EdgeInsets.fromLTRB(28, 20, 28, 0),
            child: Wrap(
              spacing: 16,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Text(_taskState(context, task.state)),
                if (task.state != 'succeeded')
                  TextButton(
                    onPressed: _busy ? null : () => _readTask(task.id),
                    child: Text(_copy(context, '刷新', 'Refresh', '새로고침')),
                  ),
                if (task.canResume)
                  OutlinedButton(
                    onPressed: _busy
                        ? null
                        : () => _readTask(task.id, resume: true),
                    child: Text(_copy(context, '继续', 'Resume', '계속')),
                  ),
              ],
            ),
          ),
        Expanded(
          child: _opened == null && task?.markdown == null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(32),
                    child: Text(
                      _copy(
                        context,
                        '选择资料提出问题，或打开一份已有成果。',
                        'Choose sources and ask a question, or open saved work.',
                        '자료와 질문을 선택하거나 저장된 결과를 열어 보세요.',
                      ),
                    ),
                  ),
                )
              : ListView(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 28,
                    vertical: 24,
                  ),
                  children: [
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 880),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          TextField(
                            controller: _title,
                            maxLength: 300,
                            readOnly:
                                !_editing ||
                                _opened == null ||
                                _pending != null,
                            style: Theme.of(context).textTheme.headlineSmall,
                            decoration: InputDecoration(
                              labelText: _copy(context, '标题', 'Title', '제목'),
                              counterText: '',
                            ),
                            onChanged: (_) => setState(() {}),
                          ),
                          const SizedBox(height: 24),
                          if (!_editing)
                            _ResearchReading(
                              markdown: _body.text,
                              title: _title.text,
                            )
                          else
                            TextField(
                              controller: _body,
                              minLines: 12,
                              maxLines: null,
                              readOnly:
                                  !_editing ||
                                  _opened == null ||
                                  _pending != null,
                              style: const TextStyle(fontSize: 16, height: 1.7),
                              decoration: InputDecoration(
                                border: InputBorder.none,
                                labelText: _copy(
                                  context,
                                  '正文',
                                  'Content',
                                  '본문',
                                ),
                              ),
                              onChanged: (_) => setState(() {}),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
        ),
        if (_opened != null || task?.markdown != null)
          Padding(
            padding: const EdgeInsets.all(20),
            child: Row(
              children: [
                if (_opened != null)
                  Expanded(
                    child: Text(
                      '${_copy(context, '版本', 'Version', '버전')} ${_opened!.version}${_dirty ? ' · ${_copy(context, '未保存', 'Unsaved', '저장 안 됨')}' : ''}',
                    ),
                  )
                else
                  const Spacer(),
                if (_opened != null)
                  TextButton.icon(
                    onPressed: _busy || _pending != null
                        ? null
                        : () => setState(() => _editing = !_editing),
                    icon: Icon(
                      _editing
                          ? Icons.visibility_outlined
                          : Icons.edit_outlined,
                    ),
                    label: Text(
                      _editing
                          ? _copy(context, '预览', 'Preview', '미리 보기')
                          : _copy(context, '编辑', 'Edit', '편집'),
                    ),
                  ),
                FilledButton(
                  onPressed:
                      _busy || _pending != null || (_opened != null && !_dirty)
                      ? null
                      : _save,
                  child: Text(
                    _opened == null
                        ? _copy(context, '保存成果', 'Save result', '결과 저장')
                        : _copy(
                            context,
                            '保存新版本',
                            'Save new version',
                            '새 버전 저장',
                          ),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

String _date(String value) =>
    DateTime.tryParse(value)?.toLocal().toString().split('.').first ?? value;
String _taskState(BuildContext context, String state) => switch (state) {
  'succeeded' => _copy(context, '已整理，待核阅', 'Ready for review', '검토 준비됨'),
  'running' => _copy(context, '处理中', 'In progress', '처리 중'),
  'pending' => _copy(context, '等待处理', 'Waiting', '처리 대기'),
  'failed' => _copy(context, '未完成', 'Not completed', '완료되지 않음'),
  'interrupted' => _copy(context, '已中断', 'Interrupted', '중단됨'),
  'cancelled' => _copy(context, '已取消', 'Cancelled', '취소됨'),
  'paused' => _copy(context, '已暂停', 'Paused', '일시 중지됨'),
  _ => _copy(context, '状态待确认', 'Status unconfirmed', '상태 미확인'),
};

class _ResearchReading extends StatelessWidget {
  const _ResearchReading({required this.markdown, required this.title});
  final String markdown, title;
  String _text(String value) => value
      .replaceAll('**', '')
      .replaceAllMapped(RegExp(r'\\([\\_*\[\]()`#<>.!+{}-])'), (m) => m[1]!);
  @override
  Widget build(BuildContext context) {
    final lines = markdown.split('\n');
    final children = <Widget>[];
    final typography = Theme.of(context).textTheme;
    for (var i = 0; i < lines.length; i++) {
      final line = lines[i];
      if (line.trim().isEmpty ||
          (i == 0 &&
              line.startsWith('# ') &&
              _text(line.substring(2)) == title)) {
        continue;
      }
      if (line.startsWith('| ') &&
          i + 1 < lines.length &&
          lines[i + 1].startsWith('| ---')) {
        final table = <List<String>>[];
        while (i < lines.length &&
            lines[i].startsWith('|') &&
            lines[i].endsWith('|')) {
          if (!RegExp(r'^\|[ :|\-]+$').hasMatch(lines[i])) {
            table.add(lines[i].split('|').skip(1).toList()..removeLast());
          }
          i++;
        }
        i--;
        final width = table.fold<int>(0, (n, row) => max(n, row.length));
        for (final row in table) {
          while (row.length < width) {
            row.add('');
          }
        }
        children.add(
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 14),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Table(
                defaultColumnWidth: const IntrinsicColumnWidth(),
                border: TableBorder(
                  horizontalInside: BorderSide(
                    color: LumenisTheme.of(context).line,
                  ),
                ),
                children: [
                  for (var row = 0; row < table.length; row++)
                    TableRow(
                      children: [
                        for (final cell in table[row])
                          Padding(
                            padding: const EdgeInsets.fromLTRB(0, 10, 22, 10),
                            child: ConstrainedBox(
                              constraints: const BoxConstraints(maxWidth: 280),
                              child: Text(
                                _text(cell.trim()),
                                style: row == 0
                                    ? typography.labelLarge
                                    : typography.bodyMedium,
                              ),
                            ),
                          ),
                      ],
                    ),
                ],
              ),
            ),
          ),
        );
        continue;
      }
      final heading = RegExp(r'^(#{1,3}) (.*)$').firstMatch(line);
      children.add(
        Padding(
          padding: EdgeInsets.only(top: heading == null ? 6 : 22, bottom: 6),
          child: Text(
            _text(heading?[2] ?? line.replaceFirst(RegExp(r'^- '), '• ')),
            style: heading == null
                ? typography.bodyLarge?.copyWith(height: 1.7)
                : heading[1]!.length == 1
                ? typography.titleLarge
                : typography.titleMedium,
          ),
        ),
      );
    }
    return SelectionArea(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: children,
      ),
    );
  }
}
