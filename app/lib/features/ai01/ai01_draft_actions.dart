import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../l10n/lumenis_localizations.dart';
import 'ai01_draft_files.dart';

class Ai01DraftActions extends StatefulWidget {
  const Ai01DraftActions({
    required this.controller,
    this.focusNode,
    this.files,
    super.key,
  });

  final TextEditingController controller;
  final FocusNode? focusNode;
  final Ai01DraftFiles? files;

  @override
  State<Ai01DraftActions> createState() => _Ai01DraftActionsState();
}

class _Ai01DraftActionsState extends State<Ai01DraftActions> {
  late final _files = widget.files ?? Ai01DraftFiles();
  bool _busy = false;
  String? _statusKey;

  Future<void> _run(Future<String?> Function() action) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _statusKey = null;
    });
    try {
      final message = await action();
      if (mounted) setState(() => _statusKey = message);
    } on FormatException {
      if (mounted) setState(() => _statusKey = 'ai01.file.invalid');
    } catch (_) {
      if (mounted) setState(() => _statusKey = 'ai01.file.failed');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<String?> _open() async {
    final text = await _files.open();
    if (!mounted || text == null) return null;
    final before = widget.controller.text;
    if (before.isNotEmpty && before != text) {
      final replace = await showDialog<bool>(
        context: context,
        builder: (context) {
          final copy = context.lumenisL10n;
          return AlertDialog(
            title: Text(copy.text('ai01.file.replaceTitle')),
            content: Text(copy.text('ai01.file.replaceDetail')),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: Text(copy.text('ai01.file.keep')),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(context, true),
                child: Text(copy.text('ai01.file.replace')),
              ),
            ],
          );
        },
      );
      if (!mounted || replace != true) return null;
    }
    if (widget.controller.text != before) return 'ai01.file.changed';
    widget.controller.value = TextEditingValue(
      text: text,
      selection: TextSelection.collapsed(offset: text.length),
    );
    widget.focusNode?.requestFocus();
    return 'ai01.file.opened';
  }

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return ValueListenableBuilder<TextEditingValue>(
      valueListenable: widget.controller,
      builder: (context, value, _) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: [
              TextButton.icon(
                onPressed: _busy ? null : () => _run(_open),
                icon: const Icon(Icons.folder_open_outlined, size: 18),
                label: Text(copy.text('ai01.file.open')),
              ),
              if (_files.canSave)
                TextButton.icon(
                  onPressed: _busy || value.text.trim().isEmpty
                      ? null
                      : () => _run(() async {
                          final saved = await _files.save(value.text);
                          return saved
                              ? (kIsWeb
                                    ? 'ai01.file.downloaded'
                                    : 'ai01.file.saved')
                              : null;
                        }),
                  icon: const Icon(Icons.save_alt_outlined, size: 18),
                  label: Text(copy.text('ai01.file.save')),
                ),
              TextButton.icon(
                onPressed: _busy || value.text.trim().isEmpty
                    ? null
                    : () => _run(() async {
                        await Clipboard.setData(
                          ClipboardData(text: value.text),
                        );
                        return 'ai01.file.copied';
                      }),
                icon: const Icon(Icons.copy_outlined, size: 18),
                label: Text(copy.text('ai01.file.copy')),
              ),
            ],
          ),
          if (_busy || _statusKey != null)
            Semantics(
              liveRegion: true,
              child: Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  copy.text(_busy ? 'ai01.file.working' : _statusKey!),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            ),
        ],
      ),
    );
  }
}
