import 'dart:convert';

import 'package:flutter/material.dart';

import '../../../l10n/lumenis_localizations.dart';

class BusinessDomainPlanEditor extends StatefulWidget {
  const BusinessDomainPlanEditor({
    required this.domain,
    required this.sources,
    required this.initial,
    required this.objective,
    this.onSubmit,
    super.key,
  });
  final String domain, objective;
  final Map<String, dynamic> initial;
  final List<Map<String, dynamic>> sources;
  final Future<bool> Function(Map<String, dynamic>)? onSubmit;
  @override
  State<BusinessDomainPlanEditor> createState() =>
      _BusinessDomainPlanEditorState();
}

class _BusinessDomainPlanEditorState extends State<BusinessDomainPlanEditor> {
  late final _objective = TextEditingController(
    text: widget.initial['objective'] as String? ?? widget.objective,
  );
  final _target = TextEditingController(),
      _person = TextEditingController(),
      _output = TextEditingController(),
      _cost = TextEditingController(),
      _measure = TextEditingController(),
      _definition = TextEditingController(),
      _unit = TextEditingController(),
      _baseline = TextEditingController(),
      _targetValue = TextEditingController();
  late String _workflow =
      widget.initial['workflow'] as String? ??
      (widget.domain == 'CTH' ? 'venue_operations' : 'brand_market');
  late final List<Map<String, dynamic>> _actions = [
    for (final item in widget.initial['actions'] as List? ?? [])
      Map<String, dynamic>.from(jsonDecode(jsonEncode(item)) as Map),
  ];
  final _sources = <String>{}, _dependencies = <String>{};
  String _currency = 'CNY';
  DateTime? _due;
  String? _editing;
  bool _invalid = false;
  bool _measuring = false, _saving = false, _saveFailed = false;
  DateTime? _windowStart, _windowEnd;

  String _t(String zh, String en, String ko) =>
      switch (context.lumenisL10n.locale.languageCode) {
        'en' => en,
        'ko' => ko,
        _ => zh,
      };
  @override
  void dispose() {
    for (final controller in [
      _objective,
      _target,
      _person,
      _output,
      _cost,
      _measure,
      _definition,
      _unit,
      _baseline,
      _targetValue,
    ]) {
      controller.dispose();
    }
    super.dispose();
  }

  void _edit(Map<String, dynamic> action) => setState(() {
    _editing = action['action_id'] as String;
    _target.text = action['target'] as String;
    _person.text = action['responsible'] as String;
    _output.text = action['deliverable'] as String;
    _due = DateTime.tryParse(action['due_at'] as String? ?? '')?.toLocal();
    final cost = action['cost_estimate'] as Map?;
    _cost.text = cost?['amount'] as String? ?? '';
    _currency = cost?['currency'] as String? ?? 'CNY';
    final measure = action['success_measure'] as Map?;
    _measuring = measure != null;
    _measure.text = measure?['name'] as String? ?? '';
    _definition.text = measure?['definition'] as String? ?? '';
    _unit.text = measure?['unit'] as String? ?? '';
    _baseline.text = measure?['baseline_value'] as String? ?? '';
    _targetValue.text = measure?['target_value'] as String? ?? '';
    final window = measure?['window'] as Map?;
    _windowStart = DateTime.tryParse(
      window?['start'] as String? ?? '',
    )?.toLocal();
    _windowEnd = DateTime.tryParse(window?['end'] as String? ?? '')?.toLocal();
    _sources
      ..clear()
      ..addAll((action['source_ids'] as List).cast<String>());
    _dependencies
      ..clear()
      ..addAll((action['depends_on'] as List).cast<String>());
    _invalid = false;
  });
  void _add() {
    if (_target.text.trim().isEmpty ||
        _person.text.trim().isEmpty ||
        _output.text.trim().isEmpty ||
        _sources.isEmpty ||
        (_cost.text.trim().isNotEmpty &&
            !RegExp(r'^\d+(?:\.\d+)?$').hasMatch(_cost.text.trim())) ||
        (_measuring &&
            (_measure.text.trim().isEmpty ||
                _definition.text.trim().isEmpty ||
                _unit.text.trim().isEmpty ||
                _windowStart == null ||
                _windowEnd == null ||
                !_windowEnd!.isAfter(_windowStart!) ||
                [_baseline, _targetValue].any(
                  (c) =>
                      c.text.trim().isNotEmpty &&
                      !RegExp(r'^[+-]?\d+(?:\.\d+)?$').hasMatch(c.text.trim()),
                )))) {
      setState(() => _invalid = true);
      return;
    }
    final old = _actions.where((a) => a['action_id'] == _editing).firstOrNull;
    final action = <String, dynamic>{
      'action_id':
          _editing ?? 'action-${DateTime.now().microsecondsSinceEpoch}',
      'target': _target.text.trim(),
      'responsible': _person.text.trim(),
      'deliverable': _output.text.trim(),
      'due_at': _due?.toUtc().toIso8601String(),
      'source_ids': _sources.toList(),
      'depends_on': _dependencies.toList(),
      'cost_estimate': _cost.text.trim().isEmpty
          ? null
          : {'amount': _cost.text.trim(), 'currency': _currency},
      'success_measure': !_measuring
          ? null
          : {
              'name': _measure.text.trim(),
              'definition': _definition.text.trim(),
              'unit': _unit.text.trim(),
              'baseline_value': _baseline.text.trim().isEmpty
                  ? null
                  : _baseline.text.trim(),
              'target_value': _targetValue.text.trim().isEmpty
                  ? null
                  : _targetValue.text.trim(),
              'window': {
                'start': _windowStart!.toUtc().toIso8601String(),
                'end': _windowEnd!.toUtc().toIso8601String(),
              },
            },
    };
    setState(() {
      if (old == null) {
        _actions.add(action);
      } else {
        _actions[_actions.indexOf(old)] = action;
      }
      _editing = null;
      _due = null;
      _measuring = false;
      _windowStart = _windowEnd = null;
      _invalid = false;
      for (final controller in [
        _target,
        _person,
        _output,
        _cost,
        _measure,
        _definition,
        _unit,
        _baseline,
        _targetValue,
      ]) {
        controller.clear();
      }
      _sources.clear();
      _dependencies.clear();
    });
  }

  Future<void> _pickWindow(bool start) async {
    final current = start ? _windowStart : _windowEnd;
    final date = await showDatePicker(
      context: context,
      initialDate: current ?? DateTime.now(),
      firstDate: DateTime(1900),
      lastDate: DateTime(2200),
    );
    if (date == null || !mounted) return;
    final time = await showTimePicker(
      context: context,
      initialTime: current == null
          ? TimeOfDay.now()
          : TimeOfDay.fromDateTime(current),
    );
    if (time == null || !mounted) return;
    final selected = DateTime(
      date.year,
      date.month,
      date.day,
      time.hour,
      time.minute,
    );
    setState(() {
      if (start) {
        _windowStart = selected;
      } else {
        _windowEnd = selected;
      }
    });
  }

  Future<void> _submit() async {
    if (_saving) return;
    if (_objective.text.trim().isEmpty ||
        _editing != null ||
        [
          _target,
          _person,
          _output,
          _cost,
          _measure,
          _definition,
          _unit,
          _baseline,
          _targetValue,
        ].any((c) => c.text.isNotEmpty) ||
        _sources.isNotEmpty) {
      setState(() => _invalid = true);
      return;
    }
    final plan = <String, dynamic>{
      'workflow': _workflow,
      'objective': _objective.text.trim(),
      'actions': _actions,
    };
    if (widget.onSubmit == null) {
      Navigator.pop(context, plan);
      return;
    }
    setState(() {
      _saving = true;
      _saveFailed = false;
    });
    var saved = false;
    try {
      saved = await widget.onSubmit!(plan);
    } catch (_) {
      saved = false;
    }
    if (!mounted) return;
    if (saved) {
      Navigator.pop(context, plan);
    } else {
      setState(() {
        _saving = false;
        _saveFailed = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final workflows = widget.domain == 'CTH'
        ? {
            'venue_operations': _t('经营优化', 'Venue operations', '시설 운영'),
            'event_response': _t('活动处置', 'Event response', '행사 대응'),
            'feedback_resolution': _t('反馈处理', 'Resolve feedback', '피드백 처리'),
            'consumer_risk': _t('消费者风险', 'Consumer risk', '소비자 위험'),
          }
        : {
            'brand_market': _t('品牌策略', 'Brand strategy', '브랜드 전략'),
            'competitor_review': _t('竞品研究', 'Competitor review', '경쟁사 검토'),
            'creator_collaboration': _t(
              '创作者合作',
              'Creator collaboration',
              '크리에이터 협업',
            ),
            'campaign': _t('营销活动', 'Campaign', '캠페인'),
          };
    return PopScope(
      canPop: !_saving,
      child: AlertDialog(
        title: Text(_t('行动计划', 'Action plan', '실행 계획')),
        content: SizedBox(
          width: 680,
          child: AbsorbPointer(
            absorbing: _saving,
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  DropdownButtonFormField<String>(
                    initialValue: _workflow,
                    isExpanded: true,
                    items: [
                      for (final entry in workflows.entries)
                        DropdownMenuItem(
                          value: entry.key,
                          child: Text(entry.value),
                        ),
                    ],
                    onChanged: (value) {
                      if (value != null) setState(() => _workflow = value);
                    },
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _objective,
                    maxLines: 3,
                    decoration: InputDecoration(
                      labelText: _t('目标', 'Objective', '목표'),
                    ),
                  ),
                  const SizedBox(height: 20),
                  for (final action in _actions)
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(action['target'] as String),
                      subtitle: Text(action['responsible'] as String),
                      onTap: () => _edit(action),
                      trailing: IconButton(
                        tooltip: _t('删除行动', 'Remove action', '작업 삭제'),
                        icon: const Icon(Icons.close),
                        onPressed: () => setState(() {
                          _actions.remove(action);
                          for (final other in _actions) {
                            (other['depends_on'] as List).remove(
                              action['action_id'],
                            );
                          }
                          _dependencies.remove(action['action_id']);
                        }),
                      ),
                    ),
                  const Divider(height: 28),
                  TextField(
                    controller: _target,
                    decoration: InputDecoration(
                      labelText: _t('行动对象', 'Action target', '실행 대상'),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _person,
                    decoration: InputDecoration(
                      labelText: _t('负责人', 'Responsible person', '담당자'),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _output,
                    minLines: 2,
                    maxLines: 4,
                    decoration: InputDecoration(
                      labelText: _t('需要完成什么', 'Deliverable', '완료할 내용'),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _cost,
                          keyboardType: TextInputType.number,
                          decoration: InputDecoration(
                            labelText: _t('预计费用', 'Estimated cost', '예상 비용'),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      SizedBox(
                        width: 100,
                        child: DropdownButtonFormField<String>(
                          initialValue: _currency,
                          items: [
                            for (final c in {
                              'CNY',
                              'USD',
                              'HKD',
                              'KRW',
                              'EUR',
                              _currency,
                            })
                              DropdownMenuItem(value: c, child: Text(c)),
                          ],
                          onChanged: (value) {
                            if (value != null) {
                              setState(() => _currency = value);
                            }
                          },
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          icon: const Icon(Icons.event),
                          label: Text(
                            _due == null
                                ? _t('截止时间', 'Due date', '기한')
                                : MaterialLocalizations.of(
                                    context,
                                  ).formatMediumDate(_due!),
                          ),
                          onPressed: () async {
                            final date = await showDatePicker(
                              context: context,
                              initialDate: _due ?? DateTime.now(),
                              firstDate: DateTime(1900),
                              lastDate: DateTime(2200),
                            );
                            if (date == null || !context.mounted) return;
                            final time = await showTimePicker(
                              context: context,
                              initialTime: _due == null
                                  ? TimeOfDay.now()
                                  : TimeOfDay.fromDateTime(_due!),
                            );
                            if (time != null && mounted) {
                              setState(
                                () => _due = DateTime(
                                  date.year,
                                  date.month,
                                  date.day,
                                  time.hour,
                                  time.minute,
                                ),
                              );
                            }
                          },
                        ),
                      ),
                      if (_due != null)
                        IconButton(
                          onPressed: () => setState(() => _due = null),
                          icon: const Icon(Icons.close),
                          tooltip: _t('清除时间', 'Clear date', '기한 지우기'),
                        ),
                    ],
                  ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(
                      _t('设置成效目标', 'Set an outcome target', '성과 목표 설정'),
                    ),
                    value: _measuring,
                    onChanged: (value) => setState(() => _measuring = value),
                  ),
                  if (_measuring) ...[
                    for (final field in [
                      (_measure, _t('衡量指标', 'Measure', '측정 지표')),
                      (_definition, _t('统计口径', 'Definition', '산정 기준')),
                      (_unit, _t('单位', 'Unit', '단위')),
                      (
                        _baseline,
                        _t('当前基线（可留空）', 'Baseline (optional)', '기준값 (선택)'),
                      ),
                      (
                        _targetValue,
                        _t('目标值（可留空）', 'Target (optional)', '목표값 (선택)'),
                      ),
                    ])
                      Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: TextField(
                          controller: field.$1,
                          decoration: InputDecoration(labelText: field.$2),
                        ),
                      ),
                    for (final start in [true, false])
                      OutlinedButton.icon(
                        onPressed: () => _pickWindow(start),
                        icon: const Icon(Icons.date_range_outlined),
                        label: Text(
                          (start ? _windowStart : _windowEnd) == null
                              ? (start
                                    ? _t('观察开始', 'Observation starts', '관찰 시작')
                                    : _t('观察结束', 'Observation ends', '관찰 종료'))
                              : '${start ? _t('开始', 'Start', '시작') : _t('结束', 'End', '종료')} · '
                                    '${MaterialLocalizations.of(context).formatMediumDate((start ? _windowStart : _windowEnd)!)} '
                                    '${TimeOfDay.fromDateTime((start ? _windowStart : _windowEnd)!).format(context)}',
                        ),
                      ),
                  ],
                  ExpansionTile(
                    title: Text(_t('依据', 'Supporting material', '근거')),
                    initiallyExpanded: true,
                    children: [
                      for (final source in widget.sources)
                        CheckboxListTile(
                          title: Text(
                            source['title'] as String? ??
                                _t('资料', 'Source', '자료'),
                          ),
                          value: _sources.contains(source['source_id']),
                          onChanged: (selected) => setState(() {
                            if (selected == true) {
                              _sources.add(source['source_id'] as String);
                            } else {
                              _sources.remove(source['source_id']);
                            }
                          }),
                        ),
                    ],
                  ),
                  if (_actions.any((a) => a['action_id'] != _editing))
                    ExpansionTile(
                      title: Text(
                        _t('先完成的行动', 'Prerequisite actions', '선행 작업'),
                      ),
                      children: [
                        for (final action in _actions.where(
                          (a) => a['action_id'] != _editing,
                        ))
                          CheckboxListTile(
                            title: Text(action['target'] as String),
                            value: _dependencies.contains(action['action_id']),
                            onChanged: (selected) => setState(() {
                              if (selected == true) {
                                _dependencies.add(
                                  action['action_id'] as String,
                                );
                              } else {
                                _dependencies.remove(action['action_id']);
                              }
                            }),
                          ),
                      ],
                    ),
                  if (_invalid)
                    Text(
                      _t(
                        '请补全行动、负责人、交付内容、依据和已开启的成效目标，并先添加或更新当前行动。',
                        'Complete the action, owner, deliverable, sources and any enabled outcome target, then add or update the action.',
                        '작업, 담당자, 결과물, 근거와 선택한 성과 목표를 입력하고 현재 작업을 추가하거나 수정하세요.',
                      ),
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  Align(
                    alignment: Alignment.centerRight,
                    child: OutlinedButton.icon(
                      onPressed: _add,
                      icon: Icon(_editing == null ? Icons.add : Icons.check),
                      label: Text(
                        _t(
                          _editing == null ? '添加行动' : '更新行动',
                          _editing == null ? 'Add action' : 'Update action',
                          _editing == null ? '작업 추가' : '작업 수정',
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: _saving ? null : () => Navigator.pop(context),
            child: Text(_t('取消', 'Cancel', '취소')),
          ),
          FilledButton(
            onPressed: _saving ? null : _submit,
            child: Text(
              _saving
                  ? _t('保存中…', 'Saving…', '저장 중…')
                  : _t('采用计划', 'Use plan', '계획 적용'),
            ),
          ),
          if (_saveFailed)
            Text(
              _t(
                '未能保存，内容已保留。',
                'Could not save. Your changes are retained.',
                '저장하지 못했습니다. 변경 내용은 보존됩니다.',
              ),
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
        ],
      ),
    );
  }
}
