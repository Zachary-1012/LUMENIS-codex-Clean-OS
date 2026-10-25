import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import '../../shared/sh04/sh04_export_files.dart';
import 'source_brief_view_model.dart';
import 'business_domain_plan_editor.dart';

Map<String, dynamic> _map(Object? value) =>
    value is Map ? Map<String, dynamic>.from(value) : const {};
List<Map<String, dynamic>> _rows(Object? value) => value is List
    ? value
          .whereType<Map>()
          .map((row) => Map<String, dynamic>.from(row))
          .toList()
    : const [];

class BusinessWorkPanel extends StatefulWidget {
  const BusinessWorkPanel({
    required this.client,
    required this.domainId,
    required this.onReturn,
    this.source,
    this.exportFiles,
    super.key,
  });
  final LumenisCoreClient client;
  final String domainId;
  final SourceBriefResult? source;
  final Sh04ExportFiles? exportFiles;
  final VoidCallback onReturn;

  @override
  State<BusinessWorkPanel> createState() => _BusinessWorkPanelState();
}

class _BusinessWorkPanelState extends State<BusinessWorkPanel> {
  final _question = TextEditingController();
  late final _exportFiles = widget.exportFiles ?? Sh04ExportFiles();
  late final String _scope = jsonEncode(widget.client.currentContextEnvelope);
  Map<String, dynamic>? _work;
  List<Map<String, dynamic>> _recent = [];
  Map<String, dynamic>? _saved;
  bool _busy = false;
  String? _error;
  final Map<String, String> _operationIds = {};
  final Map<String, Map<String, String>> _formDrafts = {};
  String _tab = 'plan';
  bool _questionExpanded = false;

  String _t(String key) => context.lumenisL10n.text('business.work.$key');
  String _local(String zh, String en, String ko) =>
      switch (context.lumenisL10n.locale.languageCode) {
        'en' => en,
        'ko' => ko,
        _ => zh,
      };
  String _rc(String key) {
    const labels = {
      'report': ['报告回答', 'Report answers', '보고서 답변'],
      'numbers': ['数字与统计口径', 'Numbers and statistical basis', '수치와 통계 기준'],
      'source': ['原文依据', 'Original support', '원문 근거'],
      'scope': [
        '报告自述的范围与局限',
        'Scope and limits reported by the source',
        '자료에 명시된 범위와 한계',
      ],
      'diagnostics': ['方法与诊断信息', 'Methods and diagnostics', '방법과 진단 정보'],
      'next': ['下一步', 'Next action', '다음 단계'],
      'otherAnswers': ['其他回答与限制', 'Other answers and limitations', '다른 답변과 한계'],
      'reanalyze': ['重新核对资料', 'Recheck material', '자료 다시 검토'],
      'editDecision': ['修改决定', 'Edit decision', '결정 수정'],
      'sourceExcerpt': ['原文摘录', 'Source excerpt', '원문 발췌'],
      'estimatedCost': ['预计费用', 'Estimated cost', '예상 비용'],
      'options': ['方案比较', 'Compare options', '방안 비교'],
      'showQuestion': ['查看完整问题', 'Read the full question', '전체 질문 보기'],
      'hideQuestion': ['收起问题', 'Collapse question', '질문 접기'],
      'export': ['导出', 'Export', '내보내기'],
      'exportFormat': ['选择导出格式', 'Choose an export format', '내보내기 형식 선택'],
      'delivery': ['交付文件', 'Delivery', '전달 파일'],
      'archive': ['归档副本', 'Archive', '보관 사본'],
      'downloadHandedOff': [
        '文件已交给浏览器下载，请检查下载记录。',
        'The file was handed to the browser. Check Downloads.',
        '브라우저에 파일을 전달했습니다. 다운로드 목록을 확인하세요.',
      ],
      'fileExported': [
        '文件已保存到所选位置。',
        'The file was saved to the selected location.',
        '선택한 위치에 파일을 저장했습니다.',
      ],
      'exportCopied': ['导出文本已复制。', 'Exported text copied.', '내보낸 텍스트를 복사했습니다.'],
      'exportFailed': [
        '导出未完成。请重试。',
        'Export did not complete. Please retry.',
        '내보내기를 완료하지 못했습니다. 다시 시도하세요.',
      ],
      'reported': [
        '以下数字来自报告陈述，不代表已逐条核验原生记录。',
        'These are report statements, not independently verified native records.',
        '아래 수치는 보고서의 진술이며 원본 기록의 개별 검증을 뜻하지 않습니다.',
      ],
      'paragraph': ['原文段落', 'Original paragraph', '원문 문단'],
      'unknown': ['未知', 'Unknown', '알 수 없음'],
      'internalResult': ['内部制作成果', 'Created material', '제작 자료'],
      'internalFresh': [
        '本次已复查制作成果',
        'Created material rechecked now',
        '이번에 제작 자료를 다시 확인했습니다',
      ],
      'internalHistorical': [
        '历史制作记录，尚未重新核验',
        'Historical creation record; not rechecked',
        '이전 제작 기록이며 재확인 전입니다',
      ],
      'internalOnly': [
        '制作完成不代表已执行对外行动或取得经营效果。',
        'Creation does not confirm external action or business results.',
        '제작 완료는 외부 실행이나 사업 성과를 뜻하지 않습니다.',
      ],
      'openInternal': ['打开制作成果', 'Open created material', '제작 자료 열기'],
      'publicDocument': ['公共来源文档', 'Public-source document', '공개 출처 문서'],
      'approvedDocument': [
        '获准研究材料',
        'Permitted research material',
        '허용된 연구 자료',
      ],
      'REPORT_QUANTITIES': [
        '报告数字与口径',
        'Reported quantities and scope',
        '보고 수치와 범위',
      ],
      'SOURCE_REVIEW': ['来源与适用范围', 'Sources and applicability', '출처와 적용 범위'],
      'CALENDAR_REVIEW': ['日期与活动范围', 'Dates and activity scope', '날짜와 행사 범위'],
      'INTERACTION_REVIEW': ['互动数据口径', 'Interaction definitions', '상호작용 지표 기준'],
      'LABEL_REVIEW': ['反馈与标注', 'Feedback and annotations', '피드백과 분류'],
      'BUSINESS_COMPARISON': ['比较边界', 'Comparison limits', '비교의 한계'],
      'BUSINESS_RESULT': ['经营结果', 'Business outcomes', '경영 결과'],
      'VENUE_OPERATOR_DISCLOSURE': [
        '运营方披露',
        'Operator disclosures',
        '운영자 공개 자료',
      ],
      'CONSUMER_FEEDBACK': ['消费者反馈', 'Consumer feedback', '소비자 피드백'],
      'OFFICIAL_BRAND_SELF_DESCRIPTION': [
        '品牌官方资料',
        'Official brand materials',
        '브랜드 공식 자료',
      ],
      'MARKET_DISCLOSURE': [
        '市场与竞品资料',
        'Market and competitor materials',
        '시장과 경쟁 자료',
      ],
      'CREATOR_CONTENT': ['创作者内容', 'Creator materials', '크리에이터 자료'],
      'ENTITY_PROFILE_RESEARCH_COMPILATION': [
        '主体研究汇编',
        'Subject research',
        '주체 리서치',
      ],
    };
    final index = switch (context.lumenisL10n.locale.languageCode) {
      'en' => 1,
      'ko' => 2,
      _ => 0,
    };
    return labels[key]?[index] ?? _rc('report');
  }

  String _businessProse(String value) {
    for (final role in const [
      'VENUE_OPERATOR_DISCLOSURE',
      'CONSUMER_FEEDBACK',
      'OFFICIAL_BRAND_SELF_DESCRIPTION',
      'MARKET_DISCLOSURE',
      'CREATOR_CONTENT',
      'ENTITY_PROFILE_RESEARCH_COMPILATION',
    ]) {
      value = value.replaceAll(role, _rc(role));
    }
    for (final item in _citations) {
      if (item['source_id'] is String) {
        value = value.replaceAll(
          item['source_id'] as String,
          item['title'] as String? ?? _rc('source'),
        );
      }
    }
    return value
        .replaceAll(RegExp(r'(?:DOC|SRC)-[A-Za-z0-9_-]+'), _rc('source'))
        .replaceAll('public_document', _rc('publicDocument'))
        .replaceAll('approved_research_document', _rc('approvedDocument'))
        .replaceAll(RegExp(r'\bUNKNOWN\b'), _rc('unknown'));
  }

  bool get _sameScope =>
      _scope == jsonEncode(widget.client.currentContextEnvelope);
  bool get _editable =>
      !_busy && _sameScope && _work?['is_current_revision'] == true;
  String get _state => _work?['state'] as String? ?? '';
  List<Map<String, dynamic>> get _citations =>
      _rows(_map(_work?['citation_candidates'])['items']);
  String _id(String key) => _operationIds.putIfAbsent(
    key,
    () =>
        'business_${DateTime.now().microsecondsSinceEpoch}_${_operationIds.length}',
  );

  @override
  void initState() {
    super.initState();
    _question.text = widget.source?.businessQuestion ?? '';
    unawaited(_load());
  }

  @override
  void dispose() {
    _question.dispose();
    super.dispose();
  }

  Map<String, dynamic> _result(Map<String, dynamic> response) {
    if (response['ok'] != true || response['result'] is! Map) {
      throw const FormatException('Invalid business response');
    }
    return _map(response['result']);
  }

  Future<void> _run(
    Future<void> Function() action, {
    String fallbackError = 'retryMessage',
  }) async {
    if (_busy) return;
    if (!_sameScope) {
      setState(() => _error = 'contextChanged');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
      if (mounted && !_sameScope) {
        _work = null;
        _recent = [];
        _saved = null;
        _error = 'contextChanged';
      }
    } on LumenisCoreException catch (error) {
      if (error.statusCode == 403 || error.statusCode == 401) {
        _work = null;
        _saved = null;
        _recent = [];
        _formDrafts.clear();
      }
      final code = error.errorCode ?? '';
      _error = error.statusCode == 409
          ? 'conflict'
          : error.statusCode == 403
          ? 'accessChanged'
          : code.contains('SOURCE') || code.contains('CITATION')
          ? 'sourceUnavailable'
          : fallbackError;
    } catch (_) {
      _error = fallbackError;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _load() => _run(() async {
    final value = _result(
      await widget.client.listBusinessWork(widget.domainId),
    );
    if (mounted && _sameScope) _recent = _rows(value['items']);
  });

  Future<void> _open(String id, {String? revision}) => _run(() async {
    final value = _result(
      await widget.client.readBusinessWork(
        domainId: widget.domainId,
        workId: id,
        revision: revision,
      ),
    );
    if (mounted && _sameScope) {
      if (_work?['work_id'] != value['work_id'] ||
          _work?['question'] != value['question']) {
        _questionExpanded = false;
      }
      _work = value;
      _question.text = value['question'] as String? ?? '';
      _saved = null;
    }
  });

  Future<void> _prepare() => _run(() async {
    final source = widget.source;
    if (source == null ||
        source.scope.globalScope ||
        _question.text.trim().isEmpty) {
      return;
    }
    final key = jsonEncode(['prepare', source.jobId, _question.text.trim()]);
    final value = _result(
      await widget.client.prepareBusinessWork(
        domainId: widget.domainId,
        jobId: source.jobId,
        question: _question.text.trim(),
        submissionId: _id(key),
      ),
    );
    if (mounted && _sameScope) {
      _work = value;
    }
  });

  Future<void> _advance(String operation, Map<String, dynamic> payload) =>
      _run(() async {
        final work = _work!;
        final key = jsonEncode([
          work['work_id'],
          work['revision'],
          operation,
          payload,
        ]);
        final value = _result(
          await widget.client.advanceBusinessWork(
            domainId: widget.domainId,
            workId: work['work_id'] as String,
            operation: operation,
            revision: work['revision'] as String,
            submissionId: _id(key),
            payload: payload,
          ),
        );
        if (mounted && _sameScope) {
          _work = value;
          if (value['revision'] != work['revision']) _saved = null;
        }
      });

  DateTime? _formDate(String value) {
    final text = value.trim();
    final match = RegExp(
      r'^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d{1,6})?)?(Z|[+-]\d{2}:\d{2})$',
    ).firstMatch(text);
    if (match == null) return null;
    final year = int.parse(match[1]!);
    final month = int.parse(match[2]!);
    final day = int.parse(match[3]!);
    final zone = match[7]!;
    if (year < 1 ||
        month < 1 ||
        month > 12 ||
        day < 1 ||
        day > DateTime.utc(year, month + 1, 0).day ||
        int.parse(match[4]!) > 23 ||
        int.parse(match[5]!) > 59 ||
        int.parse(match[6] ?? '0') > 59 ||
        zone != 'Z' &&
            (int.parse(zone.substring(1, 3)) > 23 ||
                int.parse(zone.substring(4, 6)) > 59)) {
      return null;
    }
    return DateTime.tryParse(text);
  }

  Future<Map<String, String>?> _form(
    String title,
    Map<String, String> fields, {
    Set<String> optional = const {},
    Map<String, String> initial = const {},
  }) async {
    final formKey = jsonEncode([_work?['work_id'], _work?['revision'], title]);
    final values = _formDrafts[formKey] ?? initial;
    final controllers = {
      for (final key in fields.keys)
        key: TextEditingController(text: values[key] ?? ''),
    };
    final dateFields = <String>{
      for (final key in const [
        'start',
        'end',
        'performed_at',
        'observed_at',
        'occurred_at',
        'review_at',
      ])
        if (fields.containsKey(key)) key,
    };
    bool invalidDate(String key) =>
        dateFields.contains(key) &&
        (!optional.contains(key) || controllers[key]!.text.trim().isNotEmpty) &&
        _formDate(controllers[key]!.text) == null;
    String fieldValue(String key) {
      final text = controllers[key]!.text.trim();
      return dateFields.contains(key)
          ? _formDate(text)?.toUtc().toIso8601String() ?? text
          : text;
    }

    final route = DialogRoute<Map<String, String>>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, update) => AlertDialog(
          title: Text(title),
          content: SizedBox(
            width: 560,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  for (final entry in fields.entries)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 14),
                      child: TextField(
                        controller: controllers[entry.key],
                        onChanged: (_) => update(() {}),
                        minLines:
                            const {
                              'reason',
                              'revision_reason',
                              'proposal',
                              'rationale',
                              'limits',
                              'quote',
                              'definition',
                              'question',
                            }.contains(entry.key)
                            ? 2
                            : 1,
                        maxLines: 5,
                        decoration: InputDecoration(
                          labelText: entry.value,
                          errorText: invalidDate(entry.key)
                              ? _t('dateInvalid')
                              : null,
                          suffixIcon: !dateFields.contains(entry.key)
                              ? null
                              : IconButton(
                                  tooltip: MaterialLocalizations.of(
                                    dialogContext,
                                  ).datePickerHelpText,
                                  icon: const Icon(
                                    Icons.calendar_today_outlined,
                                  ),
                                  onPressed: () async {
                                    var value =
                                        _formDate(
                                          controllers[entry.key]!.text,
                                        )?.toLocal() ??
                                        DateTime.now();
                                    if (value.isBefore(DateTime(1900)) ||
                                        value.isAfter(DateTime(2200))) {
                                      value = DateTime.now();
                                    }
                                    final day = await showDatePicker(
                                      context: dialogContext,
                                      initialDate: value,
                                      firstDate: DateTime(1900),
                                      lastDate: DateTime(2200),
                                    );
                                    if (day == null || !dialogContext.mounted) {
                                      return;
                                    }
                                    final time = await showTimePicker(
                                      context: dialogContext,
                                      initialTime: TimeOfDay.fromDateTime(
                                        value,
                                      ),
                                    );
                                    if (time == null ||
                                        !dialogContext.mounted) {
                                      return;
                                    }
                                    update(() {
                                      final selected = DateTime(
                                        day.year,
                                        day.month,
                                        day.day,
                                        time.hour,
                                        time.minute,
                                      );
                                      controllers[entry.key]!.text = selected
                                          .toUtc()
                                          .toIso8601String();
                                    });
                                  },
                                ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: Text(_t('cancel')),
            ),
            FilledButton(
              onPressed:
                  !_sameScope ||
                      dateFields.any(invalidDate) ||
                      controllers.entries.any(
                        (e) =>
                            !optional.contains(e.key) &&
                            e.value.text.trim().isEmpty,
                      )
                  ? null
                  : () => Navigator.pop(dialogContext, {
                      for (final e in controllers.entries)
                        e.key: fieldValue(e.key),
                    }),
              child: Text(_t('confirm')),
            ),
          ],
        ),
      ),
    );
    try {
      final result = await Navigator.of(
        context,
        rootNavigator: true,
      ).push(route);
      await route.completed;
      return result;
    } finally {
      if (_sameScope) {
        _formDrafts[formKey] = {
          for (final e in controllers.entries) e.key: fieldValue(e.key),
        };
      }
      for (final controller in controllers.values) {
        controller.dispose();
      }
    }
  }

  Future<void> _choose(Map<String, dynamic> option) async {
    final answer = await _form(
      _t('decide'),
      {
        'reason': _t('reason'),
        'owner': _t('owner'),
        'review_at': _t('reviewAt'),
      },
      initial: {
        'review_at': DateTime.now()
            .add(const Duration(days: 7))
            .toUtc()
            .toIso8601String(),
      },
    );
    if (answer == null || !mounted || !_sameScope) return;
    if (DateTime.tryParse(answer['review_at']!) == null ||
        !RegExp(r'(Z|[+-]\d{2}:\d{2})$').hasMatch(answer['review_at']!)) {
      setState(() => _error = 'dateInvalid');
      return;
    }
    await _advance('choose', {'option_id': option['option_id'], ...answer});
  }

  Future<void> _revise(Map<String, dynamic> option) async {
    final answer = await _form(
      _t('revise'),
      {
        'proposal': _t('proposal'),
        'rationale': _t('rationale'),
        'check': _t('check'),
        'reason': _t('revisionReason'),
      },
      initial: {
        'proposal': '${option['proposal']}',
        'rationale': '${option['rationale']}',
        'check': '${option['check']}',
      },
    );
    if (answer == null || !mounted || !_sameScope) return;
    final options = _rows(_work!['options'])
        .map(
          (item) => <String, dynamic>{
            for (final key in [
              'option_id',
              'proposal',
              'rationale',
              'source_ids',
              'assumptions',
              'unknowns',
              'check',
            ])
              key: item[key],
            if (item['option_id'] == option['option_id']) ...{
              'proposal': answer['proposal'],
              'rationale': answer['rationale'],
              'check': answer['check'],
            },
          },
        )
        .toList();
    await _advance('adopt', {
      'reason': answer['reason'],
      'question': _work!['question'],
      'source_job_id': _map(_work!['source_report'])['job_id'],
      'options': options,
      'decision': _decisionInput(_map(_work!['decision'])),
    });
  }

  Map<String, dynamic> _decisionInput(Map<String, dynamic> value) => {
    for (final key in const ['option_id', 'reason', 'owner', 'review_at'])
      key: value[key],
    if (value['resource_constraints'] is Map)
      'resource_constraints': {
        for (final key in const [
          'budget_amount',
          'estimated_cost_amount',
          'currency',
          'as_of',
          'limits',
        ])
          key: _map(value['resource_constraints'])[key],
      },
  };

  List<Map<String, dynamic>> _optionInputs(Map<String, dynamic> work) => [
    for (final option in _rows(work['options']))
      {
        for (final key in const [
          'option_id',
          'proposal',
          'rationale',
          'source_ids',
          'assumptions',
          'unknowns',
          'check',
        ])
          key: option[key],
      },
  ];

  Future<void> _editDecision() async {
    if (!_editable || const {'CANCELLED', 'INTERRUPTED'}.contains(_state)) {
      return;
    }
    final work = _work!;
    final decision = _decisionInput(_map(work['decision']));
    if (decision['option_id'] == null) return;
    final answer = await _form(
      _rc('editDecision'),
      {
        'reason': _t('reason'),
        'owner': _t('owner'),
        'review_at': _t('reviewAt'),
        'revision_reason': _t('revisionReason'),
      },
      initial: {
        for (final key in const ['reason', 'owner', 'review_at'])
          key: decision[key] as String? ?? '',
      },
    );
    if (answer == null || !mounted || !_sameScope) return;
    if (!_editable ||
        _work?['work_id'] != work['work_id'] ||
        _work?['revision'] != work['revision']) {
      setState(() => _error = 'conflict');
      return;
    }
    await _advance('adopt', {
      'source_job_id': _map(work['source_report'])['job_id'],
      'question': work['question'],
      'options': _optionInputs(work),
      'decision': {
        ...decision,
        for (final key in const ['reason', 'owner', 'review_at'])
          key: answer[key],
      },
      'reason': answer['revision_reason'],
    });
  }

  Future<void> _editDomainPlan() async {
    if (!_editable || _busy) return;
    final work = _work!;
    final analysis = _map(work['domain_analysis']);
    final planning = _map(
      _map(analysis['question_result'])['planning_constraints'],
    );
    await showDialog<Map<String, dynamic>>(
      context: context,
      barrierDismissible: false,
      builder: (context) => BusinessDomainPlanEditor(
        domain: widget.domainId,
        sources: _citations,
        initial: _map(planning['domain_plan']),
        objective: work['question'] as String,
        onSubmit: (plan) async {
          if (!mounted ||
              !_sameScope ||
              _work?['revision'] != work['revision'] ||
              _work?['work_id'] != work['work_id']) {
            if (mounted) setState(() => _error = 'conflict');
            return false;
          }
          await _advance('adopt', {
            'reason': _local('更新行动计划', 'Update action plan', '실행 계획 수정'),
            'question': work['question'],
            'source_job_id': _map(work['source_report'])['job_id'],
            'options': _optionInputs(work),
            if (_map(work['decision']).isNotEmpty)
              'decision': _decisionInput(_map(work['decision'])),
            'planning_constraints': {...planning, 'domain_plan': plan},
          });
          return mounted &&
              _sameScope &&
              _error == null &&
              _work?['revision'] != work['revision'];
        },
      ),
    );
  }

  Future<void> _openSourceExcerpt(Map<String, dynamic> source) =>
      _run(() async {
        final work = _work!;
        final refreshed = _result(
          await widget.client.readBusinessWork(
            domainId: widget.domainId,
            workId: work['work_id'] as String,
            revision: work['revision'] as String,
          ),
        );
        if (!mounted || !_sameScope) return;
        final matches = _rows(_map(refreshed['citation_candidates'])['items'])
            .where(
              (item) =>
                  item['source_id'] == source['source_id'] &&
                  item['source_job_id'] == source['source_job_id'],
            )
            .toList();
        final expected = _map(source['citation']);
        final citation = matches.length == 1
            ? _map(matches.single['citation'])
            : const <String, dynamic>{};
        if (refreshed['work_id'] != work['work_id'] ||
            refreshed['revision'] != work['revision'] ||
            matches.length != 1 ||
            citation['quote'] is! String ||
            const [
              'evidence_id',
              'start',
              'end',
              'quote',
            ].any((key) => citation[key] != expected[key])) {
          _error = 'sourceUnavailable';
          return;
        }
        setState(() => _busy = false);
        await showDialog<void>(
          context: context,
          builder: (dialogContext) => AlertDialog(
            title: Text(
              matches.single['title'] as String? ?? _rc('sourceExcerpt'),
            ),
            content: SizedBox(
              width: 660,
              child: SingleChildScrollView(
                child: SelectableText(
                  citation['quote'] as String,
                  key: const ValueKey('business-source-excerpt'),
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext),
                child: Text(_t('close')),
              ),
            ],
          ),
        );
      });

  Future<void> _reasonAction(String operation) async {
    final answer = await _form(_t(operation), {'reason': _t('reason')});
    if (answer != null && mounted && _sameScope) {
      await _advance(operation, answer);
    }
  }

  Future<void> _reanalyze() async {
    final work = _work!;
    final answer = await _form(_rc('reanalyze'), {
      'reason': _t('revisionReason'),
    });
    if (answer == null || !mounted || !_sameScope) return;
    await _advance('adopt', {
      'source_job_id': _map(work['source_report'])['job_id'],
      'question': work['question'],
      'options': null,
      'decision': null,
      'reason': answer['reason'],
    });
  }

  Future<Map<String, dynamic>?> _selectSource() async {
    final sources = [..._citations];
    String? cursor;
    bool more = true;
    bool loading = false;
    bool failed = false;
    return showDialog<Map<String, dynamic>>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, update) => AlertDialog(
          title: Text(_t('source')),
          content: SizedBox(
            width: 600,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  for (final item in sources)
                    ListTile(
                      title: Text(item['title'] as String? ?? _t('source')),
                      subtitle: Text(
                        _map(item['citation'])['quote'] as String? ?? '',
                        maxLines: 4,
                        overflow: TextOverflow.ellipsis,
                      ),
                      onTap: !_sameScope
                          ? null
                          : () => Navigator.pop(dialogContext, item),
                    ),
                  if (loading) const LinearProgressIndicator(minHeight: 2),
                  if (failed) Text(_t('sourceUnavailable')),
                  if (more)
                    TextButton(
                      onPressed: loading
                          ? null
                          : () async {
                              update(() {
                                loading = true;
                                failed = false;
                              });
                              try {
                                final page = _result(
                                  await widget.client.businessWorkSources(
                                    widget.domainId,
                                    cursor: cursor,
                                  ),
                                );
                                if (!dialogContext.mounted || !_sameScope) {
                                  return;
                                }
                                update(() {
                                  for (final report in _rows(page['items'])) {
                                    for (final item in _rows(
                                      _map(
                                        report['citation_candidates'],
                                      )['items'],
                                    )) {
                                      if (!sources.any(
                                        (old) =>
                                            old['source_job_id'] ==
                                                item['source_job_id'] &&
                                            old['source_id'] ==
                                                item['source_id'],
                                      )) {
                                        sources.add(item);
                                      }
                                    }
                                  }
                                  cursor = page['next_cursor'] as String?;
                                  more =
                                      page['has_more'] == true &&
                                      cursor != null;
                                });
                              } catch (_) {
                                if (dialogContext.mounted) {
                                  update(() => failed = true);
                                }
                              } finally {
                                if (dialogContext.mounted) {
                                  update(() => loading = false);
                                }
                              }
                            },
                      child: Text(_t('moreSources')),
                    ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: Text(_t('cancel')),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _recordCost({
    Map<String, dynamic>? action,
    Map<String, dynamic>? correction,
  }) async {
    final kind =
        correction?['kind'] as String? ??
        await showDialog<String>(
          context: context,
          builder: (dialogContext) => SimpleDialog(
            title: Text(_t('recordCost')),
            children: [
              for (final value in ['ESTIMATE', 'COMMITTED', 'ACTUAL', 'REFUND'])
                SimpleDialogOption(
                  onPressed: () => Navigator.pop(dialogContext, value),
                  child: Text(_t(value)),
                ),
            ],
          ),
        );
    if (kind == null || !mounted || !_sameScope) return;
    Map<String, dynamic>? parent;
    final observation = _map(_work!['observation']);
    final ledger = _rows(observation['cost_ledger']);
    final superseded =
        (_map(observation['action_cost_review'])['superseded_entry_ids']
                    as List? ??
                [])
            .toSet();
    if (kind == 'REFUND' && correction != null) {
      parent = ledger
          .where((row) => row['entry_id'] == correction['related_entry_id'])
          .firstOrNull;
      if (parent == null) return;
    } else if (kind == 'REFUND') {
      final rows = _rows(observation['cost_ledger'])
          .where(
            (row) =>
                row['kind'] == 'ACTUAL' &&
                !superseded.contains(row['entry_id']),
          )
          .toList();
      parent = await showDialog<Map<String, dynamic>>(
        context: context,
        builder: (dialogContext) => SimpleDialog(
          title: Text(_t('refundFor')),
          children: [
            if (rows.isEmpty)
              Padding(
                padding: const EdgeInsets.all(20),
                child: Text(_t('noActualCost')),
              ),
            for (final row in rows)
              SimpleDialogOption(
                onPressed: () => Navigator.pop(dialogContext, row),
                child: Text('${row['amount'] ?? '—'} ${row['currency']}'),
              ),
          ],
        ),
      );
      if (parent == null || !mounted || !_sameScope) return;
    }
    if (kind != 'REFUND' && correction == null && action == null) {
      final actions = _rows(_map(_work!['domain_plan'])['actions']);
      if (actions.isNotEmpty) {
        final choice = await showDialog<Map<String, dynamic>>(
          context: context,
          builder: (dialogContext) => SimpleDialog(
            title: Text(_local('对应行动', 'Related action', '관련 실행')),
            children: [
              SimpleDialogOption(
                onPressed: () =>
                    Navigator.pop(dialogContext, <String, dynamic>{}),
                child: Text(_local('整个项目', 'Whole project', '전체 프로젝트')),
              ),
              for (final item in actions)
                SimpleDialogOption(
                  onPressed: () => Navigator.pop(dialogContext, item),
                  child: Text('${item['target']}'),
                ),
            ],
          ),
        );
        if (choice == null || !mounted || !_sameScope) return;
        action = choice.isEmpty ? null : choice;
      }
    }
    final source = await _selectSource();
    if (source == null || !mounted || !_sameScope) return;
    final now = DateTime.now().toUtc();
    final answer = await _form(
      correction == null
          ? _t(kind)
          : _local('更正${_t(kind)}', 'Correct ${_t(kind)}', '${_t(kind)} 정정'),
      {
        'amount': _t('amount'),
        'currency': _t('currency'),
        'start': _t('windowStart'),
        'end': _t('windowEnd'),
        'observed_at': _t('observedAt'),
        'occurred_at': _local('费用发生时间', 'Cost date', '비용 발생 일시'),
        'quote': _t('quote'),
        'limits': _t('limits'),
        if (correction != null)
          'correction_reason': _local('更正原因', 'Reason for correction', '정정 사유'),
      },
      optional: const {'amount'},
      initial: {
        'amount': correction?['amount'] as String? ?? '',
        'currency':
            correction?['currency'] as String? ??
            parent?['currency'] as String? ??
            _map(action?['cost_estimate'])['currency'] as String? ??
            '',
        'start':
            _map(observation['window'])['start'] as String? ??
            now.subtract(const Duration(days: 1)).toIso8601String(),
        'end':
            _map(observation['window'])['end'] as String? ??
            now.toIso8601String(),
        'observed_at': now.toIso8601String(),
        'occurred_at':
            correction?['occurred_at'] as String? ?? now.toIso8601String(),
        'quote': _map(source['citation'])['quote'] as String,
      },
    );
    if (answer == null || !mounted || !_sameScope) return;
    final key = jsonEncode([
      'cost',
      _work!['revision'],
      kind,
      answer,
      parent?['entry_id'],
      action?['action_id'],
      correction?['entry_id'],
    ]);
    final entryId = _id(key);
    await _advance('observation', {
      'source_job_id': source['source_job_id'],
      'source_id': source['source_id'],
      'quote': answer['quote'],
      'limits': answer['limits'],
      'observed_at': answer['observed_at'],
      'window': {'start': answer['start'], 'end': answer['end']},
      'metrics': <Object>[],
      'costs': [
        {
          'entry_id': entryId,
          'kind': kind,
          'amount': answer['amount']!.trim().isEmpty ? null : answer['amount'],
          'currency': answer['currency']!.toUpperCase(),
          'related_entry_id': parent?['entry_id'],
          'occurred_at': answer['occurred_at'],
          if (action != null && kind != 'REFUND' && correction == null)
            'plan_action_id': action['action_id'],
          if (correction != null) ...{
            'supersedes_entry_id': correction['entry_id'],
            'correction_reason': answer['correction_reason'],
          },
        },
      ],
    });
  }

  Future<void> _record(
    bool observation, {
    Map<String, dynamic>? plannedAction,
  }) async {
    final source = await _selectSource();
    if (source == null || !mounted || !_sameScope) return;
    final quote = _map(source['citation'])['quote'] as String? ?? '';
    final now = DateTime.now().toUtc();
    final answer = await _form(
      _t(observation ? 'recordObservation' : 'recordAction'),
      observation
          ? {
              'start': _t('windowStart'),
              'end': _t('windowEnd'),
              'observed_at': _t('observedAt'),
              'name': _t('metric'),
              'definition': _t('definition'),
              'value': _t('value'),
              'unit': _t('unit'),
              'numerator': _t('numerator'),
              'denominator': _t('denominator'),
              'quote': _t('quote'),
              'limits': _t('limits'),
            }
          : {
              'performer': _t('owner'),
              'exact_target': _t('actionTarget'),
              'performed_at': _t('performedAt'),
              'quote': _t('quote'),
              'limits': _t('limits'),
            },
      optional: const {'value', 'numerator', 'denominator'},
      initial: {
        if (plannedAction != null) ...{
          'performer': plannedAction['responsible'] as String,
          'exact_target': plannedAction['target'] as String,
        },
        'quote': quote,
        'performed_at': now.toIso8601String(),
        'observed_at': now.toIso8601String(),
        'start': now.subtract(const Duration(days: 1)).toIso8601String(),
        'end': now.toIso8601String(),
      },
    );
    if (answer == null || !mounted || !_sameScope) return;
    final claim = <String, dynamic>{
      'source_job_id': source['source_job_id'],
      'source_id': source['source_id'],
      'quote': answer['quote'],
      'limits': answer['limits'],
    };
    if (observation) {
      await _advance('observation', {
        ...claim,
        'observed_at': answer['observed_at'],
        'window': {'start': answer['start'], 'end': answer['end']},
        'metrics': [
          {
            for (final key in [
              'name',
              'definition',
              'value',
              'unit',
              'numerator',
              'denominator',
            ])
              key: answer[key]!.isEmpty ? null : answer[key],
          },
        ],
        'costs': <Object>[],
      });
    } else {
      await _advance('manual_action', {
        ...claim,
        if (plannedAction != null) 'plan_action_id': plannedAction['action_id'],
        'option_id': _map(_work!['decision'])['option_id'],
        for (final key in ['performer', 'exact_target', 'performed_at'])
          key: answer[key],
      });
    }
  }

  Future<void> _save() => _run(() async {
    final work = _work!;
    if (_map(_map(work['saved_results'])['latest'])['business_revision'] ==
        work['revision']) {
      _saved = null;
      final expected = _map(_map(work['saved_results'])['latest']);
      final refreshed = _result(
        await widget.client.readBusinessWork(
          domainId: widget.domainId,
          workId: work['work_id'] as String,
        ),
      );
      if (!mounted || !_sameScope) return;
      final latest = _map(_map(refreshed['saved_results'])['latest']);
      if (refreshed['work_id'] != work['work_id'] ||
          refreshed['revision'] != work['revision'] ||
          latest['business_revision'] != work['revision'] ||
          latest['artifact_id'] != expected['artifact_id'] ||
          latest['sha256'] != expected['sha256'] ||
          latest['draft_digest'] != expected['draft_digest']) {
        _work = refreshed;
        _error = 'conflict';
        return;
      }
      final verified = _result(
        await widget.client.reopenSourceBriefSavedWork(
          domainId: widget.domainId,
          artifactId: latest['artifact_id'] as String,
        ),
      );
      if (!mounted || !_sameScope) return;
      final artifact = _map(verified['artifact']);
      final document = _map(verified['document']);
      final business = _map(_map(document['payload'])['business_work']);
      if (artifact['artifact_id'] != latest['artifact_id'] ||
          artifact['sha256'] != latest['sha256'] ||
          document['draft_digest'] != latest['draft_digest'] ||
          document['version'] != latest['version'] ||
          business['work_id'] != work['work_id'] ||
          business['revision'] != work['revision']) {
        throw const FormatException('Saved business version changed.');
      }
      _work = refreshed;
      _saved = verified;
      return;
    }
    final candidates = _citations;
    if (candidates.isEmpty ||
        _map(work['citation_candidates'])['save_limit_state'] ==
            'SHARED_CITATION_LIMIT_EXCEEDED') {
      throw const FormatException('Source citations unavailable');
    }
    final citations = candidates.map((item) => _map(item['citation'])).toList();
    final requestId = _id(
      jsonEncode(['save', work['work_id'], work['revision'], citations]),
    );
    final savedResults = _map(work['saved_results']);
    if (savedResults['next_parent_state'] == 'UNAVAILABLE') {
      throw const FormatException('Saved parent unavailable');
    }
    final previous = savedResults['latest'] is Map
        ? _map(savedResults['latest'])
        : null;
    final prepared = _result(
      await widget.client.saveBusinessWork(
        domainId: widget.domainId,
        workId: work['work_id'] as String,
        revision: work['revision'] as String,
        requestId: requestId,
        citations: citations,
        previousArtifactId: previous?['artifact_id'] as String?,
        expectedDraftDigest: previous?['draft_digest'] as String?,
      ),
    );
    if (!mounted || !_sameScope) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(_t('saveResult')),
        content: SizedBox(
          width: 640,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(work['question'] as String),
                const SizedBox(height: 20),
                Text(_t('saveQuotes')),
                const SizedBox(height: 12),
                for (final item in candidates)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          item['title'] as String? ?? _t('source'),
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 6),
                        SelectableText(
                          _map(item['citation'])['quote'] as String,
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: Text(_t('cancel')),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: Text(_t('saveResult')),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted || !_sameScope) return;
    final result = _result(
      await widget.client.saveBusinessWork(
        domainId: widget.domainId,
        workId: work['work_id'] as String,
        revision: work['revision'] as String,
        requestId: requestId,
        citations: citations,
        confirmedResource: prepared['resource'] as String,
        previousArtifactId: previous?['artifact_id'] as String?,
        expectedDraftDigest: previous?['draft_digest'] as String?,
      ),
    );
    if (mounted && _sameScope) {
      _saved = _map(result['saved_work']);
      _work = _result(
        await widget.client.readBusinessWork(
          domainId: widget.domainId,
          workId: work['work_id'] as String,
        ),
      );
    }
  });

  Widget _button(String key, VoidCallback? action, {IconData? icon}) =>
      icon == null
      ? TextButton(onPressed: action, child: Text(_t(key)))
      : OutlinedButton.icon(
          onPressed: action,
          icon: Icon(icon, size: 18),
          label: Text(_t(key)),
        );

  String _status(String value) => switch (value) {
    'PREPARED' => _t('prepared'),
    'DECIDED' => _t('decided'),
    'ACTION_RECORDED' => _t('actionRecorded'),
    'OUTCOME_RECORDED' => _t('observationRecorded'),
    'INTERRUPTED' => _t('interrupted'),
    'CANCELLED' => _t('cancelled'),
    'NOT_READY' => _t('needsMaterials'),
    _ => _t('inProgress'),
  };

  @override
  Widget build(BuildContext context) {
    final palette = LumenisTheme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 16, 24, 12),
          child: Wrap(
            spacing: 14,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              _button('back', widget.onReturn, icon: Icons.arrow_back),
              Text(
                _t(widget.domainId == 'CTH' ? 'cthTitle' : 'bmpTitle'),
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              _button(
                'recent',
                _busy
                    ? null
                    : () {
                        setState(() {
                          _work = null;
                          _saved = null;
                        });
                        unawaited(_load());
                      },
              ),
              if (_work != null)
                _button(
                  'refresh',
                  _busy ? null : () => _open(_work!['work_id'] as String),
                ),
            ],
          ),
        ),
        if (_busy) const LinearProgressIndicator(minHeight: 2),
        if (_error != null || !_sameScope)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
            child: Semantics(
              liveRegion: true,
              child: Text(
                !_sameScope
                    ? _t('contextChanged')
                    : _error == 'exportFailed'
                    ? _rc('exportFailed')
                    : _t(_error!),
                style: TextStyle(color: palette.danger),
              ),
            ),
          ),
        Expanded(
          child: _sameScope
              ? _work == null
                    ? _start()
                    : _workspace()
              : const SizedBox.shrink(),
        ),
      ],
    );
  }

  Widget _start() => ListView(
    padding: const EdgeInsets.all(28),
    children: [
      if (widget.source != null && !widget.source!.scope.globalScope) ...[
        TextField(
          controller: _question,
          minLines: 2,
          maxLines: 5,
          decoration: InputDecoration(labelText: _t('question')),
        ),
        const SizedBox(height: 12),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton(
            onPressed: _busy ? null : _prepare,
            child: Text(_t('prepare')),
          ),
        ),
        const SizedBox(height: 30),
      ],
      if (_recent.isEmpty && !_busy) Text(_t('noWork')),
      for (final row in _recent)
        ListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(row['question'] as String? ?? _t('unavailableWork')),
          subtitle: Text(
            row['availability'] == 'AVAILABLE'
                ? _status('${row['state']}')
                : _t('sourceUnavailable'),
          ),
          trailing: const Icon(Icons.arrow_forward),
          onTap: _busy || row['availability'] != 'AVAILABLE'
              ? null
              : () => _open(row['work_id'] as String),
        ),
    ],
  );

  Widget _workspace() {
    final work = _work!;
    return LayoutBuilder(
      builder: (context, workspaceBox) {
        final inlineActions =
            workspaceBox.maxHeight < 480 ||
            MediaQuery.textScalerOf(context).scale(16) > 24;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 28),
              child: Wrap(
                spacing: 16,
                children: [
                  for (final tab in ['plan', 'execution', 'versions'])
                    Semantics(
                      selected: _tab == tab,
                      child: TextButton(
                        onPressed: () => setState(() => _tab = tab),
                        child: Text(
                          _t(tab),
                          style: TextStyle(
                            fontWeight: _tab == tab
                                ? FontWeight.w700
                                : FontWeight.w400,
                          ),
                        ),
                      ),
                    ),
                  if (work['is_current_revision'] != true)
                    Text(_t('historical')),
                  if (_tab == 'plan' &&
                      _editable &&
                      !const {'CANCELLED', 'INTERRUPTED'}.contains(_state))
                    IconButton(
                      key: const ValueKey('business-recheck-material'),
                      tooltip: _rc('reanalyze'),
                      onPressed: _reanalyze,
                      icon: const Icon(Icons.fact_check_outlined, size: 20),
                    ),
                ],
              ),
            ),
            Expanded(
              child: LayoutBuilder(
                builder: (context, box) {
                  final readingScale =
                      (MediaQuery.textScalerOf(context).scale(16) / 16).clamp(
                        1.0,
                        double.infinity,
                      );
                  // At normal size, reserve 220 / 380 / 276 for the three panes,
                  // plus 36 between panes and 48 around them. Use the panel's
                  // available width after the workspace navigation has been laid out.
                  final wide =
                      readingScale <= 1.5 && box.maxWidth >= 960 * readingScale;
                  final paper = DecoratedBox(
                    key: const ValueKey('business/comparison-paper'),
                    decoration: LumenisTheme.paper(
                      LumenisTheme.of(context),
                      radius: 8,
                    ),
                    child: Material(
                      type: MaterialType.transparency,
                      child: SelectionArea(
                        child: ListView(
                          primary: false,
                          key: const ValueKey('business/main-scroll'),
                          padding: EdgeInsets.fromLTRB(
                            wide ? 28 : 22,
                            24,
                            wide ? 28 : 22,
                            30,
                          ),
                          children: [
                            _questionHeading(work['question'] as String),
                            const SizedBox(height: 20),
                            if (!wide) ...[
                              ..._decisionSummary(),
                              if (_tab == 'plan')
                                ExpansionTile(
                                  key: const ValueKey('business/source-fold'),
                                  tilePadding: EdgeInsets.zero,
                                  title: Text(_rc('source')),
                                  children: _sourceEntries(),
                                ),
                              const Divider(height: 32),
                            ],
                            if (_tab == 'plan') ..._plan(),
                            if (_tab == 'execution')
                              ..._execution(includeActions: !wide),
                            if (_tab == 'versions') ..._versions(),
                            if (inlineActions) _workspaceActions(),
                          ],
                        ),
                      ),
                    ),
                  );
                  return Padding(
                    padding: EdgeInsets.symmetric(horizontal: wide ? 24 : 16),
                    child: wide
                        ? Row(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              SizedBox(
                                width: (box.maxWidth * .19).clamp(220, 280),
                                child: DecoratedBox(
                                  key: const ValueKey('business/source-rail'),
                                  decoration: LumenisTheme.panel(
                                    LumenisTheme.of(context),
                                    recessed: true,
                                    radius: 8,
                                  ),
                                  child: Material(
                                    type: MaterialType.transparency,
                                    child: ListView(
                                      primary: false,
                                      padding: const EdgeInsets.fromLTRB(
                                        18,
                                        24,
                                        18,
                                        24,
                                      ),
                                      children: [
                                        Text(
                                          _rc('source'),
                                          style: Theme.of(
                                            context,
                                          ).textTheme.titleMedium,
                                        ),
                                        const SizedBox(height: 14),
                                        ..._sourceEntries(),
                                      ],
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 18),
                              Expanded(child: paper),
                              const SizedBox(width: 18),
                              SizedBox(
                                width: (box.maxWidth * .23).clamp(276, 340),
                                child: DecoratedBox(
                                  key: const ValueKey('business/decision-rail'),
                                  decoration: LumenisTheme.panel(
                                    LumenisTheme.of(context),
                                    recessed: true,
                                    radius: 8,
                                  ),
                                  child: Material(
                                    type: MaterialType.transparency,
                                    child: ListView(
                                      primary: false,
                                      padding: const EdgeInsets.fromLTRB(
                                        22,
                                        24,
                                        22,
                                        24,
                                      ),
                                      children: [
                                        ..._decisionSummary(),
                                        const Divider(height: 36),
                                        _executionControls(),
                                      ],
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          )
                        : paper,
                  );
                },
              ),
            ),
            if (!inlineActions) _workspaceActions(),
          ],
        );
      },
    );
  }

  Widget _workspaceActions() => Padding(
    key: const ValueKey('business/workspace-actions'),
    padding: const EdgeInsets.fromLTRB(24, 12, 24, 16),
    child: Wrap(
      spacing: 12,
      runSpacing: 8,
      children: [
        if (const {
          'DECIDED',
          'ACTION_RECORDED',
          'OUTCOME_RECORDED',
        }.contains(_state))
          FilledButton.icon(
            onPressed: _editable ? _save : null,
            icon: const Icon(Icons.save_outlined),
            label: Text(_t('saveResult')),
          ),
        if (_state == 'INTERRUPTED')
          _button('resume', _editable ? () => _advance('resume', {}) : null),
        if (_state == 'CANCELLED')
          _button('restore', _editable ? () => _reasonAction('restore') : null),
        if (const {
          'PREPARED',
          'DECIDED',
          'ACTION_RECORDED',
          'NOT_READY',
        }.contains(_state)) ...[
          _button(
            'interrupt',
            _editable ? () => _reasonAction('interrupt') : null,
          ),
          _button(
            'cancelWork',
            _editable ? () => _reasonAction('cancel') : null,
          ),
        ],
        if (_saved != null)
          Semantics(liveRegion: true, child: Text(_t('saved'))),
      ],
    ),
  );

  Widget _questionHeading(String question) => LayoutBuilder(
    builder: (context, box) {
      final style = Theme.of(context).textTheme.bodyLarge!;
      final measure = TextPainter(
        text: TextSpan(text: question, style: style),
        textDirection: Directionality.of(context),
        textScaler: MediaQuery.textScalerOf(context),
        maxLines: 2,
      )..layout(maxWidth: (box.maxWidth - 52).clamp(1, double.infinity));
      final overflow = measure.didExceedMaxLines;
      measure.dispose();
      return Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: _questionExpanded || !overflow
                ? SelectableText(
                    question,
                    key: const ValueKey('business/full-question'),
                    style: style,
                  )
                : Text(
                    question,
                    key: const ValueKey('business/question-summary'),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: style,
                  ),
          ),
          if (overflow)
            Semantics(
              toggled: _questionExpanded,
              child: IconButton(
                key: const ValueKey('business/question-toggle'),
                tooltip: _rc(
                  _questionExpanded ? 'hideQuestion' : 'showQuestion',
                ),
                onPressed: () =>
                    setState(() => _questionExpanded = !_questionExpanded),
                icon: Icon(
                  _questionExpanded
                      ? Icons.unfold_less_rounded
                      : Icons.unfold_more_rounded,
                ),
              ),
            ),
        ],
      );
    },
  );

  List<Widget> _plan() {
    final work = _work!;
    final decision = _map(work['decision']);
    final analysis = _map(work['domain_analysis']);
    final judgment = _map(analysis['judgment']);
    final business = _map(_map(analysis['question_result'])['business_report']);
    return [
      if (_editable)
        Align(
          alignment: AlignmentDirectional.centerEnd,
          child: OutlinedButton.icon(
            onPressed: _busy ? null : _editDomainPlan,
            icon: const Icon(Icons.playlist_add_check),
            label: Text(_local('行动计划', 'Action plan', '실행 계획')),
          ),
        ),
      ..._domainPlanEntries(),
      if (_rows(work['options']).isNotEmpty)
        Semantics(
          header: true,
          child: Text(
            _rc('options'),
            key: const ValueKey('business/options'),
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: LumenisTheme.of(context).muted,
            ),
          ),
        ),
      for (final option in _rows(work['options'])) ...[
        const SizedBox(height: 12),
        Text(
          _businessProse('${option['proposal']}'),
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
            height: 1.4,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 14),
        SelectableText(
          _businessProse('${option['rationale']}'),
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(height: 1.75),
        ),
        const SizedBox(height: 16),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.only(top: 3, right: 10),
              child: Icon(
                Icons.rule_rounded,
                size: 17,
                color: LumenisTheme.of(context).accent,
              ),
            ),
            Expanded(
              child: Text(
                _businessProse('${option['check']}'),
                style: Theme.of(
                  context,
                ).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w500),
              ),
            ),
          ],
        ),
        for (final value in option['assumptions'] as List? ?? const [])
          Padding(
            padding: const EdgeInsets.only(top: 10),
            child: Text(
              _businessProse('$value'),
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
        if (option.containsKey('cost_estimate'))
          Text(
            '${_rc('estimatedCost')}: ${option['cost_estimate'] is num || option['cost_estimate'] is String ? option['cost_estimate'] : '—'}',
          ),
        if (option['unknowns'] is List)
          for (final value in option['unknowns'] as List)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: Text(
                _businessProse('$value'),
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
        Wrap(
          spacing: 12,
          children: [
            if (_state == 'PREPARED')
              _button('decide', _editable ? () => _choose(option) : null),
            if (decision['option_id'] == option['option_id'])
              Text(_t('selected')),
            if (_editable &&
                !const {'CANCELLED', 'INTERRUPTED'}.contains(_state) &&
                decision.isNotEmpty)
              _button('revise', () => _revise(option)),
          ],
        ),
        const Divider(height: 38),
      ],
      if (business['answers'] is List) ..._reportAnswers(business),
      if (business['answers'] is! List && judgment['conclusion'] is String) ...[
        SelectableText(_businessProse(judgment['conclusion'] as String)),
        const SizedBox(height: 20),
      ],
    ];
  }

  List<Widget> _domainPlanEntries() {
    final execution = _map(_work?['domain_execution']);
    final plan = _map(
      _map(
        _map(
          _map(_work?['domain_analysis'])['question_result'],
        )['planning_constraints'],
      )['domain_plan'],
    );
    final planned = {
      for (final action in _rows(plan['actions'])) action['action_id']: action,
    };
    final actions = [
      for (final action in _rows(execution['actions']))
        {
          ...action,
          'cost_estimate': planned[action['action_id']]?['cost_estimate'],
          'success_measure': planned[action['action_id']]?['success_measure'],
        },
    ];
    if (actions.isEmpty) return const [];
    return [
      if (execution['objective'] is String)
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 18),
          child: Text(
            execution['objective'] as String,
            style: Theme.of(context).textTheme.titleLarge,
          ),
        ),
      for (final action in actions)
        Padding(
          padding: const EdgeInsets.only(bottom: 16),
          child: DecoratedBox(
            decoration: BoxDecoration(
              border: Border(
                left: BorderSide(
                  color: LumenisTheme.of(context).accent,
                  width: 3,
                ),
              ),
            ),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 4, 8, 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${action['target']}',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  Text('${action['responsible']}'),
                  SelectableText('${action['deliverable']}'),
                  if (action['due_at'] is String) Text('${action['due_at']}'),
                  if (_map(action['cost_estimate']).isNotEmpty)
                    Text(
                      '${_local('预计', 'Estimate', '예상')}: ${_map(action['cost_estimate'])['amount'] ?? '—'} ${_map(action['cost_estimate'])['currency']}',
                    ),
                  if (_map(action['success_measure']).isNotEmpty) ...[
                    Text(
                      '${_map(action['success_measure'])['name']} · '
                      '${_local('目标', 'Target', '목표')}: ${_map(action['success_measure'])['target_value'] ?? '—'} '
                      '${_map(action['success_measure'])['unit']}',
                    ),
                    Text('${_map(action['success_measure'])['definition']}'),
                    Text(
                      '${_local('基线', 'Baseline', '기준값')}: ${_map(action['success_measure'])['baseline_value'] ?? '—'}',
                    ),
                  ],
                  Text(
                    action['state'] == 'REPORTED_PERFORMED'
                        ? _local('已记录执行', 'Execution recorded', '실행 기록됨')
                        : (_rows(action['waiting_for']).isNotEmpty ||
                              (action['waiting_for'] is List &&
                                  (action['waiting_for'] as List).isNotEmpty))
                        ? _local(
                            '等待前置行动',
                            'Waiting for prerequisites',
                            '선행 작업 대기',
                          )
                        : action['state'] == 'DECISION_REQUIRED'
                        ? _local('等待决定', 'Decision needed', '결정 대기')
                        : _local('待执行', 'Planned', '실행 예정'),
                  ),
                  if (_editable && action['execution_record'] == null)
                    TextButton.icon(
                      onPressed:
                          _busy || action['state'] != 'READY_FOR_OPERATOR'
                          ? null
                          : () => _record(false, plannedAction: action),
                      icon: const Icon(Icons.check),
                      label: Text(_t('recordAction')),
                    ),
                  if (_map(action['cost_review']).isNotEmpty) ...[
                    for (final currency in _map(
                      _map(action['cost_review'])['reported_costs'],
                    ).entries)
                      Text(
                        '${_local('实际净支出', 'Net actual cost', '실제 순지출')}: ${_map(currency.value)['net_actual'] ?? '—'} ${currency.key}',
                      ),
                    Text(
                      '${_local('预计剩余', 'Remaining estimate', '예상 잔액')}: ${_map(action['cost_review'])['remaining_against_declared_estimate'] ?? '—'}',
                    ),
                  ],
                  if (_editable)
                    TextButton.icon(
                      onPressed: _busy
                          ? null
                          : () => _recordCost(action: action),
                      icon: const Icon(Icons.receipt_long_outlined),
                      label: Text(_t('recordCost')),
                    ),
                ],
              ),
            ),
          ),
        ),
    ];
  }

  List<Widget> _sourceEntries() => [
    for (final source in _citations)
      ListTile(
        key: ValueKey('business/source/${source['source_id']}'),
        contentPadding: EdgeInsets.zero,
        title: Text(source['title'] as String? ?? _rc('sourceExcerpt')),
        subtitle: Text(
          _map(source['citation'])['quote'] as String? ?? '',
          maxLines: 4,
          overflow: TextOverflow.ellipsis,
        ),
        trailing: const Icon(Icons.chevron_right_rounded, size: 18),
        onTap: _busy || !_sameScope ? null : () => _openSourceExcerpt(source),
      ),
    if (_citations.isEmpty) Text(_t('sourceUnavailable')),
  ];

  List<Widget> _decisionSummary() {
    final decision = _map(_work!['decision']);
    final resources = _map(decision['resource_constraints']);
    final date = _formDate(decision['review_at'] as String? ?? '')?.toLocal();
    final review = date == null
        ? decision['review_at'] as String? ?? '—'
        : '${MaterialLocalizations.of(context).formatMediumDate(date)} · ${TimeOfDay.fromDateTime(date).format(context)}';
    return [
      Text(
        _status(_state),
        style: TextStyle(color: LumenisTheme.of(context).muted),
      ),
      if (decision.isNotEmpty) ...[
        const SizedBox(height: 18),
        Semantics(
          header: true,
          child: Text(
            _t('decision'),
            style: Theme.of(context).textTheme.titleLarge,
          ),
        ),
        const SizedBox(height: 14),
        SelectableText('${decision['reason']}'),
        const SizedBox(height: 18),
        Text(_t('owner'), style: Theme.of(context).textTheme.labelMedium),
        SelectableText('${decision['owner']}'),
        const SizedBox(height: 14),
        Text(_t('reviewAt'), style: Theme.of(context).textTheme.labelMedium),
        SelectableText(review, key: const ValueKey('business/review-time')),
        const SizedBox(height: 12),
        Align(
          alignment: AlignmentDirectional.centerStart,
          child: OutlinedButton.icon(
            key: const ValueKey('business/edit-decision'),
            onPressed:
                _editable &&
                    !const {'CANCELLED', 'INTERRUPTED'}.contains(_state)
                ? _editDecision
                : null,
            icon: const Icon(Icons.edit_outlined, size: 18),
            label: Text(_rc('editDecision')),
          ),
        ),
        if (resources.isNotEmpty) ...[
          const Divider(height: 30),
          Text(_t('budget'), style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),
          Text(
            '${_t('budgetAmount')}: ${resources['budget_amount'] ?? '—'} ${resources['currency'] ?? ''}',
          ),
          Text(
            '${_rc('estimatedCost')}: ${resources['estimated_cost_amount'] ?? '—'} ${resources['currency'] ?? ''}',
          ),
          if (resources['limits'] is String)
            Text(resources['limits'] as String),
        ],
      ],
    ];
  }

  Widget _executionControls() {
    final enabled =
        _editable &&
        const {
          'DECIDED',
          'ACTION_RECORDED',
          'OUTCOME_RECORDED',
        }.contains(_state);
    return Wrap(
      spacing: 12,
      runSpacing: 8,
      children: [
        _button(
          'recordAction',
          enabled ? () => _record(false) : null,
          icon: Icons.assignment_turned_in_outlined,
        ),
        _button(
          'recordObservation',
          enabled ? () => _record(true) : null,
          icon: Icons.insights_outlined,
        ),
        _button(
          'recordCost',
          enabled ? _recordCost : null,
          icon: Icons.receipt_long_outlined,
        ),
      ],
    );
  }

  List<Widget> _answerCopy(Map<String, dynamic> answer) => [
    Text(
      _rc(answer['goal'] as String? ?? ''),
      style: Theme.of(context).textTheme.titleMedium,
    ),
    const SizedBox(height: 6),
    Text(_businessProse('${answer['summary']}')),
    Text('${_rc('next')}: ${_businessProse('${answer['next_action']}')}'),
    for (final limit in answer['limitations'] as List? ?? const [])
      Text(_businessProse('$limit')),
    const SizedBox(height: 18),
  ];

  List<Widget> _reportAnswers(Map<String, dynamic> business) {
    final answers = _rows(business['answers']);
    final quantityFirst = answers.any(
      (answer) => answer['goal'] == 'REPORT_QUANTITIES',
    );
    return [
      Semantics(
        header: true,
        child: Text(
          _rc('report'),
          style: Theme.of(context).textTheme.titleLarge,
        ),
      ),
      const SizedBox(height: 12),
      for (final answer in answers.where(
        (answer) => !quantityFirst || answer['goal'] == 'REPORT_QUANTITIES',
      ))
        ..._answerCopy(answer),
      for (final review in _rows(business['document_reviews']))
        if (_rows(review['declared_counts']).isNotEmpty ||
            _rows(review['checks']).isNotEmpty) ...[
          Semantics(
            header: true,
            child: Text(
              _rc('numbers'),
              style: Theme.of(context).textTheme.titleLarge,
            ),
          ),
          Text('${review['title']}'),
          Text(_rc('reported')),
          const SizedBox(height: 12),
          Wrap(
            spacing: 24,
            runSpacing: 12,
            children: [
              for (final count in _rows(review['declared_counts']))
                Text(
                  '${count['value']} ${count['unit']}',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
            ],
          ),
          for (final check in _rows(review['checks'])) ...[
            const SizedBox(height: 20),
            Text(
              '${check['title']}',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            Text('${check['summary']}'),
            Text('${check['limitation']}'),
            Text('${_rc('next')}: ${check['next_action']}'),
            _reportReferences([
              _map(check['reference']),
              for (final member in _rows(check['members']))
                _map(member['reference']),
            ]),
          ],
          if (_rows(review['scope_notes']).isNotEmpty)
            ExpansionTile(
              tilePadding: EdgeInsets.zero,
              title: Text(_rc('scope')),
              children: [
                for (final note in _rows(review['scope_notes']))
                  Align(
                    alignment: Alignment.centerLeft,
                    child: SelectableText('${note['statement']}'),
                  ),
              ],
            ),
          const SizedBox(height: 20),
        ],
      if (quantityFirst && answers.length > 1)
        ExpansionTile(
          tilePadding: EdgeInsets.zero,
          title: Text(_rc('otherAnswers')),
          children: [
            for (final answer in answers.where(
              (answer) => answer['goal'] != 'REPORT_QUANTITIES',
            ))
              ..._answerCopy(answer),
          ],
        ),
      ExpansionTile(
        tilePadding: EdgeInsets.zero,
        title: Text(_rc('diagnostics')),
        children: [
          SelectableText(
            const JsonEncoder.withIndent('  ').convert({
              'canonical_inputs': business['canonical_inputs'],
              'cohorts': business['cohorts'],
              'methods': [
                for (final review in _rows(business['document_reviews']))
                  review['method'],
              ],
            }),
          ),
        ],
      ),
      const Divider(),
    ];
  }

  Widget _reportReferences(List<Map<String, dynamic>> references) {
    final unique = <String, Map<String, dynamic>>{};
    for (final reference in references) {
      if (reference['statement'] is String) {
        unique[jsonEncode([
              reference['source_id'],
              reference['start'],
              reference['end'],
            ])] =
            reference;
      }
    }
    return ExpansionTile(
      tilePadding: EdgeInsets.zero,
      title: Text(_rc('source')),
      children: [
        for (final reference in unique.values) ...[
          if (_rows(reference['locators']).isNotEmpty)
            Align(
              alignment: Alignment.centerLeft,
              child: Text(
                '${_rc('paragraph')} ${_rows(reference['locators']).first['index'] ?? ''}',
              ),
            ),
          Align(
            alignment: Alignment.centerLeft,
            child: SelectableText(reference['statement'] as String),
          ),
          ExpansionTile(
            title: Text(_rc('diagnostics')),
            children: [
              SelectableText(
                jsonEncode({
                  for (final key in [
                    'source_id',
                    'evidence_ref',
                    'start',
                    'end',
                    'body_sha256',
                  ])
                    key: reference[key],
                }),
              ),
            ],
          ),
        ],
      ],
    );
  }

  Widget _savedReportReader(Map<String, dynamic> document) {
    final business = _map(_map(document['payload'])['business_work']);
    final question = business['question'] as String?;
    final raw = document['markdown'] as String? ?? _t('unavailableWork');
    final paragraphs = <Widget>[];
    for (final rawLine in raw.split('\n')) {
      final line = rawLine
          .trim()
          .replaceAllMapped(
            RegExp(r'\\([\\`*_{}\[\]()#+.!>\-])'),
            (match) => match[1]!,
          )
          .replaceAll('&lt;', '<')
          .replaceAll('&gt;', '>')
          .replaceAll('&amp;', '&');
      if (line.isEmpty ||
          line == question ||
          RegExp(
            r'^(方法：|分析状态：|完整业务判断：|可核对来源：|来源报告：|证据：|Evidence )',
          ).hasMatch(line) ||
          (!line.startsWith('>') &&
              RegExp(
                r'app_evidence_records:|\b(?:NOT_ESTABLISHED|ANALYZED_WITH_LIMITATIONS|RESEARCH_ACTIONS_PROPOSED)\b',
              ).hasMatch(line))) {
        continue;
      }
      final heading = RegExp(r'^(#{1,6})\s+(.+)$').firstMatch(line);
      final formatted = (heading?.group(2) ?? line)
          .replaceFirst(RegExp(r'^[-*]\s+'), '• ')
          .replaceAllMapped(RegExp(r'\*\*(.+?)\*\*'), (match) => match[1]!);
      final display = line.startsWith('>')
          ? formatted.replaceFirst(RegExp(r'^>\s*'), '')
          : _businessProse(formatted);
      paragraphs.add(
        Padding(
          padding: const EdgeInsets.only(bottom: 10, top: 3),
          child: heading != null
              ? Semantics(
                  header: true,
                  child: Text(
                    display,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                )
              : Text(display),
        ),
      );
    }
    return SelectionArea(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (question != null) ...[
            Text(_t('question'), style: Theme.of(context).textTheme.labelLarge),
            Text(question, style: Theme.of(context).textTheme.bodyLarge),
            const SizedBox(height: 18),
          ],
          ...paragraphs,
          ExpansionTile(
            title: Text(_rc('diagnostics')),
            children: [SelectableText(raw)],
          ),
        ],
      ),
    );
  }

  bool _internalReceiptReady(Map<String, dynamic> receipt) =>
      receipt['owner'] == 'Shared ContentCreation/TaskEngine/SavedWork' &&
      const {
        'INTERNAL_TEXT_CREATION',
        'INTERNAL_TEXT_REVISION',
      }.contains(receipt['action_kind']) &&
      receipt['execution_state'] == 'ARTIFACT_COMMITTED' &&
      receipt['external_effect'] == 'NOT_PERFORMED' &&
      receipt['business_outcome'] == 'NOT_OBSERVED' &&
      receipt['artifact_id'] is String &&
      (receipt['artifact_id'] as String).isNotEmpty &&
      receipt['task_id'] is String &&
      (receipt['task_id'] as String).isNotEmpty &&
      receipt['work_id'] is String &&
      (receipt['work_id'] as String).isNotEmpty &&
      receipt['version'] is int &&
      (receipt['version'] as int) > 0 &&
      receipt['sha256'] is String &&
      RegExp(r'^[0-9a-f]{64}$').hasMatch(receipt['sha256'] as String);

  Future<void> _openInternalResult(Map<String, dynamic> expected) =>
      _run(() async {
        final work = _work!;
        final refreshed = _result(
          await widget.client.readBusinessWork(
            domainId: widget.domainId,
            workId: work['work_id'] as String,
            revision: work['revision'] as String,
          ),
        );
        if (!mounted || !_sameScope) return;
        final receipt = _map(_map(refreshed['action'])['receipt']);
        const identity = [
          'artifact_id',
          'sha256',
          'work_id',
          'task_id',
          'version',
          'parent_artifact_id',
          'parent_sha256',
        ];
        if (refreshed['work_id'] != work['work_id'] ||
            refreshed['revision'] != work['revision'] ||
            !_internalReceiptReady(receipt) ||
            identity.any((key) => receipt[key] != expected[key])) {
          _work = refreshed;
          _error = 'conflict';
          return;
        }
        final value = _result(
          await widget.client.reopenSourceBriefSavedWork(
            domainId: widget.domainId,
            artifactId: receipt['artifact_id'] as String,
          ),
        );
        if (!mounted || !_sameScope) return;
        final artifact = _map(value['artifact']);
        final document = _map(value['document']);
        final attachments = _rows(document['attachments']);
        final output = _map(receipt['output']);
        if (artifact['artifact_id'] != receipt['artifact_id'] ||
            artifact['sha256'] != receipt['sha256'] ||
            document['work_id'] != receipt['work_id'] ||
            document['task_id'] != receipt['task_id'] ||
            document['version'] != receipt['version'] ||
            document['parent_artifact_id'] != receipt['parent_artifact_id'] ||
            document['parent_sha256'] != receipt['parent_sha256'] ||
            attachments.length != 1 ||
            const [
              'artifact_id',
              'sha256',
              'name',
              'media_type',
              'size_bytes',
            ].any(
              (key) =>
                  output[key] == null || attachments.single[key] != output[key],
            ) ||
            document['markdown'] is! String ||
            (document['markdown'] as String).trim().isEmpty) {
          throw const FormatException('Created material identity changed.');
        }
        _work = refreshed;
        setState(() => _busy = false);
        await showDialog<void>(
          context: context,
          builder: (dialogContext) => AlertDialog(
            title: Text('${_rc('internalResult')} · v${receipt['version']}'),
            content: SizedBox(
              width: 800,
              child: SingleChildScrollView(child: _savedReportReader(document)),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext),
                child: Text(_t('close')),
              ),
            ],
          ),
        );
      });

  List<Widget> _execution({bool includeActions = true}) {
    final work = _work!;
    final action = _map(work['action']);
    final receipt = _map(action['receipt']);
    final readable = _internalReceiptReady(receipt);
    final fresh =
        readable &&
        _map(work['action_read'])['state'] == 'FRESH_OWNER_VERIFIED';
    final observation = _map(work['observation']);
    return [
      if (includeActions) _executionControls(),
      ..._domainPlanEntries(),
      const SizedBox(height: 24),
      if (action.isNotEmpty) ...[
        Text(
          '${_rc('internalResult')}${readable ? ' · v${receipt['version']}' : ''}',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        Text(_rc(fresh ? 'internalFresh' : 'internalHistorical')),
        Text(_rc('internalOnly')),
        Align(
          alignment: AlignmentDirectional.centerStart,
          child: TextButton.icon(
            onPressed: !_busy && _sameScope && readable
                ? () => _openInternalResult(receipt)
                : null,
            icon: const Icon(Icons.description_outlined),
            label: Text(_rc('openInternal')),
          ),
        ),
        const Divider(),
      ],
      for (final record in _rows(work['execution_records'])) ...[
        Text(
          '${record['exact_target']}',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        Text('${record['performer']} · ${record['performed_at']}'),
        Text('${record['limits']}'),
        Text(_t('reportedExecution')),
        const Divider(),
      ],
      if (observation.isNotEmpty) ...[
        Text(_t('observation'), style: Theme.of(context).textTheme.titleLarge),
        if (observation['adoption_lineage'] is Map) ...[
          Text('${_t('historical')} · ${_t('observation')}'),
          Text(_t('noncausal')),
        ],
        Text(
          '${_map(observation['window'])['start']} — ${_map(observation['window'])['end']}',
        ),
        for (final metric in _rows(observation['metrics']))
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(
              '${metric['name']} · ${metric['value'] ?? '—'} ${metric['unit']}',
            ),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${metric['definition']}'),
                if (metric['window'] is Map)
                  Text(
                    '${_map(metric['window'])['start']} — ${_map(metric['window'])['end']}',
                  ),
                if (_map(metric['source_claim'])['quote'] is String)
                  SelectableText(
                    _map(metric['source_claim'])['quote'] as String,
                  ),
                if (metric['limits'] is String)
                  Text(metric['limits'] as String),
              ],
            ),
          ),
        Text('${observation['limits']}'),
        Text(_t('reportedObservation')),
        for (final entry in _rows(observation['cost_ledger']))
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(
              '${_t(entry['kind'] as String)} · ${entry['amount'] ?? '—'} ${entry['currency']}',
            ),
            subtitle: Text(
              [
                if (_map(entry['planned_action'])['target'] is String)
                  _map(entry['planned_action'])['target'],
                if (entry['occurred_at'] is String) entry['occurred_at'],
                if (entry['correction_reason'] is String)
                  entry['correction_reason'],
                if ((_map(
                              observation['action_cost_review'],
                            )['superseded_entry_ids']
                            as List? ??
                        [])
                    .contains(entry['entry_id']))
                  _local(
                    '已更正，原记录保留',
                    'Corrected; original retained',
                    '정정됨 · 원본 보존',
                  ),
              ].join(' · '),
            ),
            trailing:
                _editable &&
                    !(_map(
                                  observation['action_cost_review'],
                                )['superseded_entry_ids']
                                as List? ??
                            [])
                        .contains(entry['entry_id'])
                ? TextButton(
                    onPressed: _busy
                        ? null
                        : () => _recordCost(correction: entry),
                    child: Text(_local('更正', 'Correct', '정정')),
                  )
                : null,
          ),
        for (final currency in _map(observation['cost_totals']).entries) ...[
          const SizedBox(height: 20),
          Text(
            '${_t('costs')} · ${currency.key}',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 28,
            runSpacing: 16,
            children: [
              for (final key in const [
                'ESTIMATE',
                'COMMITTED',
                'ACTUAL',
                'REFUND',
                'net_actual',
              ])
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(_t(key)),
                    Text(
                      '${_map(currency.value)[key] ?? '—'}',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ],
                ),
            ],
          ),
        ],
        if (_map(observation['resource_result']).isNotEmpty) ...[
          const SizedBox(height: 24),
          Text(_t('budget'), style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 10),
          Text(
            '${_t('budgetAmount')}: ${_map(observation['resource_result'])['budget_amount'] ?? '—'} ${_map(observation['resource_result'])['currency'] ?? ''}',
          ),
          Text(
            '${_t('budgetRemaining')}: ${_map(observation['resource_result'])['remaining_budget_amount'] ?? '—'}',
          ),
          if (_map(observation['resource_result'])['state'] ==
              'PARTIAL_CURRENCY_CONVERSION_REQUIRED')
            Text(_t('currencyUnconverted')),
        ],
        for (final row in _rows(_map(observation['comparison'])['items'])) ...[
          const SizedBox(height: 20),
          Text('${row['name']} · ${_t('comparison')}'),
          Text(
            '${row['baseline_value'] ?? '—'} → ${row['current_value'] ?? '—'} ${row['unit']}',
          ),
          Text('${_t('difference')}: ${row['difference'] ?? '—'}'),
          if (row['state'] == 'INPUTS_NOT_COMPARABLE') Text(_t('incomparable')),
          Text(_t('noncausal')),
        ],
      ],
      if (action.isEmpty &&
          _rows(work['execution_records']).isEmpty &&
          observation.isEmpty)
        Text(_t('noExecution')),
    ];
  }

  bool _savedVersionContextCurrent(Map<String, dynamic> work) =>
      mounted &&
      _sameScope &&
      _work?['work_id'] == work['work_id'] &&
      _work?['revision'] == work['revision'];

  Future<Map<String, dynamic>> _readSavedVersion(
    Map<String, dynamic> work,
    Map<String, dynamic> row,
  ) async {
    if (!_savedVersionContextCurrent(work)) {
      throw const LumenisCoreException(
        'The report context changed.',
        statusCode: 409,
      );
    }
    final value = _result(
      await widget.client.reopenSourceBriefSavedWork(
        domainId: widget.domainId,
        artifactId: row['artifact_id'] as String,
      ),
    );
    if (!_savedVersionContextCurrent(work)) {
      throw const LumenisCoreException(
        'The report context changed.',
        statusCode: 409,
      );
    }
    final artifact = _map(value['artifact']);
    final document = _map(value['document']);
    final business = _map(_map(document['payload'])['business_work']);
    if (artifact['artifact_id'] != row['artifact_id'] ||
        artifact['sha256'] != row['sha256'] ||
        document['version'] != row['version'] ||
        document['draft_digest'] != row['draft_digest'] ||
        business['work_id'] != work['work_id'] ||
        business['revision'] != row['business_revision']) {
      throw const FormatException('The selected saved report changed.');
    }
    return document;
  }

  Future<void> _openSavedVersion(
    Map<String, dynamic> work,
    Map<String, dynamic> row,
  ) => _run(() async {
    final document = await _readSavedVersion(work, row);
    if (!mounted || !_savedVersionContextCurrent(work)) return;
    setState(() => _busy = false);
    final export = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(
          '${_t(widget.domainId == 'CTH' ? 'cthTitle' : 'bmpTitle')} · v${row['version']}',
        ),
        content: SizedBox(
          width: 800,
          child: SingleChildScrollView(child: _savedReportReader(document)),
        ),
        actions: [
          TextButton.icon(
            key: const ValueKey('business/export-saved-version'),
            onPressed: () => Navigator.pop(dialogContext, true),
            icon: const Icon(Icons.file_download_outlined, size: 18),
            label: Text(_rc('export')),
          ),
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: Text(_t('close')),
          ),
        ],
      ),
    );
    if (export == true && _savedVersionContextCurrent(work)) {
      await _exportSavedVersion(work, row);
    }
  });

  Future<void> _exportSavedVersion(
    Map<String, dynamic> work,
    Map<String, dynamic> row,
  ) async {
    var purpose = 'delivery';
    final formats = _exportFiles.canSaveFile
        ? const ['docx', 'pdf', 'md', 'txt', 'xlsx', 'pptx']
        : const ['md', 'txt'];
    final choice = await showDialog<({String format, String purpose})>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, update) => AlertDialog(
          title: Text(_rc('exportFormat')),
          content: SizedBox(
            width: 340,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final value in ['delivery', 'audit_snapshot'])
                        ChoiceChip(
                          key: ValueKey('business/export-purpose/$value'),
                          label: Text(
                            _rc(value == 'delivery' ? 'delivery' : 'archive'),
                          ),
                          selected: purpose == value,
                          onSelected: (_) => update(() => purpose = value),
                        ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  for (final format in formats)
                    ListTile(
                      key: ValueKey('business/export-format/$format'),
                      title: Text(format.toUpperCase()),
                      onTap: () => Navigator.pop(dialogContext, (
                        format: format,
                        purpose: purpose,
                      )),
                    ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: Text(_t('cancel')),
            ),
          ],
        ),
      ),
    );
    if (choice == null || !_savedVersionContextCurrent(work)) return;
    await _run(() async {
      await _readSavedVersion(work, row);
      final file = await widget.client.exportSourceBriefSavedWork(
        domainId: widget.domainId,
        artifactId: row['artifact_id'] as String,
        format: choice.format,
        purpose: choice.purpose,
      );
      if (!_savedVersionContextCurrent(work)) return;
      if (file.bytes.isEmpty) {
        throw const FormatException('The exported report is empty.');
      }
      if (_exportFiles.canSaveFile) {
        final saved = await _exportFiles.save(
          file,
          suggestedName:
              'oevira-${widget.domainId == 'CTH' ? 'operations' : 'brand-market'}-v${row['version']}.${choice.format}',
        );
        if (!saved || !_savedVersionContextCurrent(work)) return;
      } else {
        await Clipboard.setData(ClipboardData(text: utf8.decode(file.bytes)));
        if (!_savedVersionContextCurrent(work)) return;
      }
      if (!mounted || !_savedVersionContextCurrent(work)) return;
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(
        SnackBar(
          content: Text(
            _rc(
              !_exportFiles.canSaveFile
                  ? 'exportCopied'
                  : kIsWeb
                  ? 'downloadHandedOff'
                  : 'fileExported',
            ),
          ),
        ),
      );
    }, fallbackError: 'exportFailed');
  }

  List<Widget> _versions() {
    final work = _work!;
    final history = _rows(work['timeline']);
    final saved = _rows(_map(work['saved_results'])['items']);
    return [
      for (var index = history.length - 1; index >= 0; index--)
        ListTile(
          contentPadding: EdgeInsets.zero,
          title: Text('${_t('revision')} ${index + 1}'),
          trailing: _button(
            'open',
            _busy
                ? null
                : () => _open(
                    work['work_id'] as String,
                    revision: history[index]['evidence_ref'] as String,
                  ),
          ),
        ),
      if (saved.isNotEmpty) ...[const Divider(), Text(_t('savedResults'))],
      for (final row in saved)
        ListTile(
          key: ValueKey('business/saved-version/${row['artifact_id']}'),
          contentPadding: EdgeInsets.zero,
          title: Text(
            '${_t(widget.domainId == 'CTH' ? 'cthTitle' : 'bmpTitle')} · v${row['version']}',
          ),
          trailing: _button(
            'open',
            _busy ? null : () => _openSavedVersion(work, row),
          ),
        ),
    ];
  }
}
