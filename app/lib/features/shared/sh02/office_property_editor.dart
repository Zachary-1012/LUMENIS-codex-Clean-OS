import 'package:flutter/material.dart';

import '../../../l10n/lumenis_localizations.dart';

String officePropertyLabel(BuildContext context, String key) {
  const labels = {
    'bold': ['粗体', 'Bold', '굵게'],
    'italic': ['斜体', 'Italic', '기울임'],
    'underline': ['下划线', 'Underline', '밑줄'],
    'color': ['文字颜色', 'Text color', '글자색'],
    'size_half_points': ['字号 · pt', 'Font size · pt', '글자 크기 · pt'],
    'size_hundredth_points': ['字号 · pt', 'Font size · pt', '글자 크기 · pt'],
    'alignment': ['对齐', 'Alignment', '정렬'],
    'keep_with_next': ['与下段同页', 'Keep with next', '다음 문단과 함께'],
    'page_break_before': ['段前分页', 'Page break before', '문단 앞 페이지 나누기'],
    'space_before_twips': ['段前 · pt', 'Space before · pt', '문단 앞 · pt'],
    'space_after_twips': ['段后 · pt', 'Space after · pt', '문단 뒤 · pt'],
    'x_emu': ['水平位置 · cm', 'Horizontal position · cm', '가로 위치 · cm'],
    'y_emu': ['垂直位置 · cm', 'Vertical position · cm', '세로 위치 · cm'],
    'width_emu': ['宽度 · cm', 'Width · cm', '너비 · cm'],
    'height_emu': ['高度 · cm', 'Height · cm', '높이 · cm'],
    'rotation_60000deg': ['旋转 · °', 'Rotation · °', '회전 · °'],
    'flip_horizontal': ['水平翻转', 'Flip horizontally', '좌우 반전'],
    'flip_vertical': ['垂直翻转', 'Flip vertically', '상하 반전'],
    'style_index': ['单元格样式', 'Cell style', '셀 스타일'],
  };
  final language = context.lumenisL10n.locale.languageCode;
  return (labels[key] ?? ['', '', ''])[language == 'en'
      ? 1
      : language == 'ko'
      ? 2
      : 0];
}

String officeValueSummary(BuildContext context, Object value) {
  if (value is! Map) return '$value';
  return value.entries
      .where((entry) => entry.value != null)
      .map((entry) {
        final name = officePropertyLabel(context, '${entry.key}');
        final raw = entry.value;
        final display = raw is num
            ? _number(raw / _scale('${entry.key}'))
            : raw == true
            ? '✓'
            : raw == false
            ? '—'
            : '$raw';
        return name.isEmpty ? '' : '$name: $display';
      })
      .where((line) => line.isNotEmpty)
      .join(' · ');
}

double _scale(String field) => field.endsWith('_emu')
    ? 360000
    : switch (field) {
        'rotation_60000deg' => 60000,
        'size_half_points' => 2,
        'size_hundredth_points' => 100,
        'space_before_twips' || 'space_after_twips' => 20,
        _ => 1,
      };
String _number(num value) =>
    value.toStringAsFixed(5).replaceFirst(RegExp(r'\.?0+$'), '');

class OfficePropertyEditor extends StatelessWidget {
  const OfficePropertyEditor({
    required this.kind,
    required this.value,
    required this.enabled,
    required this.onChanged,
    this.styleOptions = const [],
    super.key,
  });
  final String kind;
  final Map<String, dynamic> value;
  final bool enabled;
  final ValueChanged<Object> onChanged;
  final List<Map<String, dynamic>> styleOptions;

  @override
  Widget build(BuildContext context) => Column(
    children: [
      for (final entry in value.entries)
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: entry.key == 'style_index'
              ? DropdownButtonFormField<int>(
                  initialValue:
                      styleOptions.any(
                        (style) => style['style_index'] == entry.value,
                      )
                      ? entry.value as int
                      : null,
                  isExpanded: true,
                  decoration: InputDecoration(
                    labelText: officePropertyLabel(context, entry.key),
                  ),
                  items: [
                    for (final style in styleOptions)
                      DropdownMenuItem<int>(
                        value: style['style_index'] as int,
                        child: Text(
                          style['name'] as String,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                  ],
                  onChanged: enabled && styleOptions.isNotEmpty
                      ? (next) {
                          if (next != null) {
                            onChanged({...value, entry.key: next});
                          }
                        }
                      : null,
                )
              : _OfficePropertyField(
                  key: ValueKey(entry.key),
                  field: entry.key,
                  kind: kind,
                  value: entry.value,
                  enabled: enabled,
                  onChanged: (next) => onChanged({...value, entry.key: next}),
                ),
        ),
    ],
  );
}

class _OfficePropertyField extends StatefulWidget {
  const _OfficePropertyField({
    required this.field,
    required this.kind,
    required this.value,
    required this.enabled,
    required this.onChanged,
    super.key,
  });
  final String field, kind;
  final Object? value;
  final bool enabled;
  final ValueChanged<Object?> onChanged;
  @override
  State<_OfficePropertyField> createState() => _OfficePropertyFieldState();
}

class _OfficePropertyFieldState extends State<_OfficePropertyField> {
  late final _controller = TextEditingController(text: _display(widget.value));
  String _display(Object? value) => value == null
      ? ''
      : value is num
      ? _number(value / _scale(widget.field))
      : '$value';
  @override
  void didUpdateWidget(covariant _OfficePropertyField oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.value != widget.value &&
        _display(widget.value) != _controller.text) {
      _controller.text = _display(widget.value);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  String _text(String zh, String en, String ko) =>
      switch (context.lumenisL10n.locale.languageCode) {
        'en' => en,
        'ko' => ko,
        _ => zh,
      };

  @override
  Widget build(BuildContext context) {
    final field = widget.field;
    final label = officePropertyLabel(context, field);
    if (const {
      'bold',
      'italic',
      'keep_with_next',
      'page_break_before',
      'flip_horizontal',
      'flip_vertical',
    }.contains(field)) {
      return CheckboxListTile(
        contentPadding: EdgeInsets.zero,
        title: Text(label),
        tristate: !field.startsWith('flip_'),
        value: widget.value as bool?,
        onChanged: widget.enabled ? widget.onChanged : null,
      );
    }
    if (field == 'alignment' || field == 'underline') {
      final word = widget.kind == 'word_run_format';
      final options = field == 'alignment'
          ? <String, String>{
              'left': _text('左对齐', 'Left', '왼쪽'),
              'center': _text('居中', 'Center', '가운데'),
              'right': _text('右对齐', 'Right', '오른쪽'),
              'both': _text('两端对齐', 'Justified', '양쪽'),
              'distribute': _text('分散对齐', 'Distributed', '균등'),
            }
          : <String, String>{
              'none': _text('无', 'None', '없음'),
              word ? 'single' : 'sng': _text('单线', 'Single', '한 줄'),
              word ? 'double' : 'dbl': _text('双线', 'Double', '두 줄'),
              'dotted': _text('点线', 'Dotted', '점선'),
              word ? 'wave' : 'wavy': _text('波浪线', 'Wave', '물결'),
            };
      final current = widget.value as String?;
      if (current != null && !options.containsKey(current)) {
        options[current] = _text('保留原格式', 'Keep original format', '원래 서식 유지');
      }
      return DropdownButtonFormField<String>(
        key: ValueKey('$field:$current'),
        initialValue: current ?? '',
        isExpanded: true,
        decoration: InputDecoration(labelText: label),
        items: [
          DropdownMenuItem(
            value: '',
            child: Text(_text('继承样式', 'Inherit style', '스타일 상속')),
          ),
          ...options.entries.map(
            (entry) =>
                DropdownMenuItem(value: entry.key, child: Text(entry.value)),
          ),
        ],
        onChanged: widget.enabled
            ? (next) => widget.onChanged(next == '' ? null : next)
            : null,
      );
    }
    final color = field == 'color';
    return TextField(
      controller: _controller,
      enabled: widget.enabled,
      keyboardType: color
          ? TextInputType.text
          : const TextInputType.numberWithOptions(decimal: true, signed: true),
      decoration: InputDecoration(
        labelText: label,
        hintText: _text('继承样式', 'Inherit style', '스타일 상속'),
      ),
      onChanged: (raw) {
        final text = raw.trim();
        if (text.isEmpty &&
            !field.endsWith('_emu') &&
            field != 'rotation_60000deg' &&
            field != 'style_index') {
          widget.onChanged(null);
          return;
        }
        if (color) {
          widget.onChanged(text.replaceFirst('#', ''));
          return;
        }
        final parsed = double.tryParse(text);
        widget.onChanged(
          parsed != null && parsed.isFinite
              ? (parsed * _scale(field)).round()
              : text,
        );
      },
    );
  }
}
