import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../core/generated_result_reveal.dart';
import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import '../../shared/read_aloud_action.dart';
import '../../shared/sh02/sh02_repository.dart';
import 'source_brief_copy.dart';
import 'source_brief_view_model.dart';
import 'business_work_panel.dart';
import '../../system/sys02/collected_comments_panel.dart';

enum _DomainImportStage { preparing, importing, startingBrief }

/// A source brief is a saved reading artifact, separate from period reports.
class SourceBriefPanel extends StatefulWidget {
  const SourceBriefPanel({
    required this.client,
    required this.onReturn,
    this.domainId = 'CTH',
    this.documentPicker,
    super.key,
  });

  final String domainId;
  final LumenisCoreClient client;
  final VoidCallback onReturn;
  final Sh02DocumentPicker? documentPicker;

  @override
  State<SourceBriefPanel> createState() => _SourceBriefPanelState();
}

class _SourceBriefPanelState extends State<SourceBriefPanel>
    with WidgetsBindingObserver {
  late final _model = SourceBriefViewModel(
    client: widget.client,
    domainId: widget.domainId,
  );
  static const _motionPreferenceKey =
      'lumenis.source_brief.result_reveal.choice.v1';
  final _reference = TextEditingController();
  final _question = TextEditingController();
  final _scroll = ScrollController();
  final _resultRevealKey = GlobalKey<GeneratedResultRevealState>();
  late final SharedPreferencesAsync _motionStorage = SharedPreferencesAsync();
  Timer? _poll;
  bool _taskReference = false;
  bool _businessWork = false;
  bool _domainImportBusy = false;
  _DomainImportStage _domainImportStage = _DomainImportStage.preparing;
  String? _domainImportMessage;
  Sh02PickedDocument? _pendingDomainFile;
  Map<String, dynamic>? _pendingDomainProvenance;
  String? _domainMaterialContext;
  final List<String> _domainSourceIds = [];
  String? _domainSourceTaskRequestId;
  String? _domainSourceTaskQuestion;
  List<String>? _domainSourceTaskSources;
  bool _domainSourceTaskUnconfirmed = false;
  bool _referenceRequired = false;
  bool _foreground = true;
  bool _motionPreferenceReady = false;
  bool _motionPreferenceSaveFailed = false;
  String? _cancelledResultArrivalToken;
  int _motionPreferenceWriteRevision = 0;
  Future<void> _motionPreferenceWrites = Future<void>.value();
  GeneratedResultMotionChoice _motionChoice =
      GeneratedResultMotionChoice.followSystem;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _scroll.addListener(_finishRevealOnScroll);
    _model.addListener(_schedulePoll);
    unawaited(_loadMotionChoice());
    unawaited(_model.initialize());
  }

  void _finishRevealOnScroll() => _cancelRevealForUserInteraction();

  void _cancelRevealForUserInteraction() {
    final token = _model.resultArrivalToken;
    if (token != null &&
        token.isNotEmpty &&
        token != _cancelledResultArrivalToken) {
      if (mounted) {
        setState(() => _cancelledResultArrivalToken = token);
      } else {
        _cancelledResultArrivalToken = token;
      }
    }
    _resultRevealKey.currentState?.cancelForScrollOrInteraction();
  }

  Future<void> _loadMotionChoice() async {
    try {
      final value = await _motionStorage.getString(_motionPreferenceKey);
      if (!mounted) return;
      setState(() {
        _motionChoice = switch (value) {
          'full' => GeneratedResultMotionChoice.full,
          'off' => GeneratedResultMotionChoice.off,
          _ => GeneratedResultMotionChoice.followSystem,
        };
        _motionPreferenceReady = true;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _motionPreferenceReady = true);
    }
  }

  void _selectMotionChoice(GeneratedResultMotionChoice choice) {
    if (!_motionPreferenceReady || choice == _motionChoice) return;
    final revision = ++_motionPreferenceWriteRevision;
    setState(() {
      _motionChoice = choice;
      _motionPreferenceSaveFailed = false;
    });
    _motionPreferenceWrites = _motionPreferenceWrites.then((_) async {
      try {
        await _motionStorage.setString(_motionPreferenceKey, choice.name);
        if (mounted && revision == _motionPreferenceWriteRevision) {
          setState(() => _motionPreferenceSaveFailed = false);
        }
      } catch (_) {
        if (mounted && revision == _motionPreferenceWriteRevision) {
          setState(() => _motionPreferenceSaveFailed = true);
        }
      }
    });
  }

  bool get _pending =>
      _model.taskState == SourceBriefTaskState.pending ||
      _model.taskState == SourceBriefTaskState.running;

  bool get _questionInvalid {
    final text = _question.text.trim();
    return text.isNotEmpty &&
        (text.runes.length < 4 ||
            text.runes.length > 1500 ||
            RegExp(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]').hasMatch(text));
  }

  void _schedulePoll() {
    _poll?.cancel();
    if (!_foreground || _model.busy || !_pending || _model.errorKind != null) {
      return;
    }
    _poll = Timer(const Duration(seconds: 5), () {
      if (mounted && _foreground && !_model.busy) {
        unawaited(_model.refreshTask());
      }
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _foreground = state == AppLifecycleState.resumed;
    if (!_foreground) _cancelRevealForUserInteraction();
    _schedulePoll();
  }

  @override
  void didUpdateWidget(covariant SourceBriefPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    _model.syncContext();
  }

  @override
  void dispose() {
    _poll?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    _model.removeListener(_schedulePoll);
    _scroll.removeListener(_finishRevealOnScroll);
    _model.dispose();
    _reference.dispose();
    _question.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _copy(String value) async {
    _cancelRevealForUserInteraction();
    final copy = SourceBriefCopy.of(context);
    var message = copy.text('copied');
    try {
      await Clipboard.setData(ClipboardData(text: value));
    } catch (_) {
      message = copy.text('copyFailed');
    }
    if (mounted) {
      ScaffoldMessenger.maybeOf(
        context,
      )?.showSnackBar(SnackBar(content: Text(message)));
    }
  }

  String _importCopy({
    required String zh,
    required String en,
    required String ko,
  }) => switch (Localizations.localeOf(context).languageCode) {
    'en' => en,
    'ko' => ko,
    _ => zh,
  };

  bool get _domainContextMatches =>
      _domainMaterialContext != null &&
      _domainMaterialContext ==
          jsonEncode(widget.client.currentContextEnvelope) &&
      !_model.globalScope;

  Map<String, dynamic> _domainImportResult(Map<String, dynamic> response) {
    if (response['ok'] != true || response['result'] is! Map) {
      throw const FormatException('Domain import response unavailable');
    }
    return Map<String, dynamic>.from(response['result'] as Map);
  }

  Future<Map<String, dynamic>?> _describeDomainFile(
    Sh02PickedDocument file,
  ) async {
    final title = TextEditingController(text: file.filename);
    final url = TextEditingController();
    final publication = TextEditingController();
    final rightsStatement = TextEditingController();
    String? rights;
    String? publicationError;
    DialogRoute<Map<String, dynamic>>? formRoute;
    try {
      formRoute = DialogRoute<Map<String, dynamic>>(
        context: context,
        builder: (dialogContext) => StatefulBuilder(
          builder: (dialogContext, update) => AlertDialog(
            title: Text(
              _importCopy(
                zh: '核对资料来源与用途',
                en: 'Review source and permitted use',
                ko: '자료 출처와 사용 확인',
              ),
            ),
            content: SizedBox(
              width: 560,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(file.filename),
                    const SizedBox(height: 14),
                    TextField(
                      key: const ValueKey('domain-import-title'),
                      controller: title,
                      onChanged: (_) => update(() {}),
                      decoration: InputDecoration(
                        labelText: _importCopy(
                          zh: '资料名称',
                          en: 'Material title',
                          ko: '자료 이름',
                        ),
                      ),
                    ),
                    TextField(
                      key: const ValueKey('domain-import-url'),
                      controller: url,
                      decoration: InputDecoration(
                        labelText: _importCopy(
                          zh: '原始网页（文件原件可留空）',
                          en: 'Original URL (optional for an original file)',
                          ko: '원문 URL (원본 파일은 선택)',
                        ),
                      ),
                    ),
                    TextField(
                      key: const ValueKey('domain-import-publication'),
                      controller: publication,
                      onChanged: (_) => update(() => publicationError = null),
                      decoration: InputDecoration(
                        errorText: publicationError,
                        labelText: _importCopy(
                          zh: '原始发布时间（未知留空，含时区）',
                          en: 'Original publication time (blank if unknown, include time zone)',
                          ko: '원문 게시 시각 (모르면 비움, 시간대 포함)',
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),
                    DropdownButtonFormField<String>(
                      key: const ValueKey('domain-import-rights'),
                      initialValue: rights,
                      decoration: InputDecoration(
                        labelText: _importCopy(
                          zh: '资料使用依据',
                          en: 'Basis for use',
                          ko: '사용 근거',
                        ),
                      ),
                      items: [
                        DropdownMenuItem(
                          value: 'public-reference-only',
                          child: Text(
                            _importCopy(
                              zh: '公开资料，仅作研究引用',
                              en: 'Public material for research reference',
                              ko: '연구 참고용 공개 자료',
                            ),
                          ),
                        ),
                        DropdownMenuItem(
                          value: 'owner-approved',
                          child: Text(
                            _importCopy(
                              zh: '自有或已明确获准的资料',
                              en: 'Owned or explicitly authorized material',
                              ko: '소유 또는 명시적으로 허용된 자료',
                            ),
                          ),
                        ),
                      ],
                      onChanged: (value) => update(() => rights = value),
                    ),
                    TextField(
                      key: const ValueKey('domain-import-rights-statement'),
                      controller: rightsStatement,
                      onChanged: (_) => update(() {}),
                      minLines: 2,
                      maxLines: 4,
                      decoration: InputDecoration(
                        labelText: _importCopy(
                          zh: '使用依据与限制',
                          en: 'Permission basis and limitations',
                          ko: '사용 근거와 제한',
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
                child: Text(_importCopy(zh: '取消', en: 'Cancel', ko: '취소')),
              ),
              FilledButton(
                key: const ValueKey('domain-import-prepare'),
                onPressed:
                    rights == null ||
                        title.text.trim().isEmpty ||
                        rightsStatement.text.trim().isEmpty
                    ? null
                    : () {
                        final published = publication.text.trim();
                        if (published.isNotEmpty &&
                            (DateTime.tryParse(published) == null ||
                                !RegExp(
                                  r'(Z|[+-]\d{2}:\d{2})$',
                                ).hasMatch(published))) {
                          update(
                            () => publicationError = _importCopy(
                              zh: '请填写含时区的有效时间，未知时留空。',
                              en: 'Enter a valid time with a time zone, or leave it blank if unknown.',
                              ko: '시간대를 포함한 유효한 시각을 입력하거나 모르면 비워두세요.',
                            ),
                          );
                          return;
                        }
                        Navigator.pop(dialogContext, <String, dynamic>{
                          'source_url': url.text.trim().isEmpty
                              ? null
                              : url.text.trim(),
                          'published_at': published.isEmpty ? null : published,
                          'captured_at': DateTime.now()
                              .toUtc()
                              .toIso8601String(),
                          'rights': rights,
                          'rights_statement': rightsStatement.text.trim(),
                          'title': title.text.trim(),
                          'intended_use': 'research_reference',
                        });
                      },
                child: Text(
                  _importCopy(zh: '核对导入', en: 'Review import', ko: '가져오기 검토'),
                ),
              ),
            ],
          ),
        ),
      );
      return await Navigator.of(context, rootNavigator: true).push(formRoute);
    } finally {
      void disposeFields() {
        for (final controller in [title, url, publication, rightsStatement]) {
          controller.dispose();
        }
      }

      final completed = formRoute?.completed;
      if (completed != null) {
        unawaited(completed.then((_) => disposeFields()));
      } else {
        disposeFields();
      }
    }
  }

  Future<void> _startImportedDomainBrief() async {
    if (!_domainContextMatches || _domainSourceIds.isEmpty) {
      throw const FormatException('Domain import context changed');
    }
    if (_domainSourceTaskRequestId == null) {
      _domainSourceTaskRequestId =
          'domain_materials_${DateTime.now().microsecondsSinceEpoch}';
      _domainSourceTaskQuestion = _question.text.trim();
      _domainSourceTaskSources = List<String>.unmodifiable(_domainSourceIds);
      _domainSourceTaskUnconfirmed = true;
    }
    _domainImportStage = _DomainImportStage.startingBrief;
    final response = await widget.client.startDomainSourceBriefTask(
      domainId: widget.domainId,
      sourceIds: _domainSourceTaskSources!,
      requestId: _domainSourceTaskRequestId!,
      businessQuestion: _domainSourceTaskQuestion,
    );
    if (!mounted || !_domainContextMatches) {
      throw const FormatException('Domain import context changed');
    }
    final task = response['task'];
    if (response['ok'] != true || task is! Map || task['task_id'] is! String) {
      throw const FormatException('Domain source task unavailable');
    }
    await _model.openTask(task['task_id'] as String);
    if (mounted) {
      _domainSourceTaskUnconfirmed = false;
      _domainImportMessage = _importCopy(
        zh: '资料已导入，简报状态由保存结果读回确认。',
        en: 'Material imported. The brief status is checked against its saved result.',
        ko: '자료를 가져왔습니다. 저장된 결과로 브리핑 상태를 확인합니다.',
      );
    }
  }

  void _domainImportFailed(Object error) {
    final denied =
        error is LumenisCoreException &&
        (error.statusCode == 401 || error.statusCode == 403);
    if (denied) {
      _domainSourceIds.clear();
      _pendingDomainFile = null;
      _pendingDomainProvenance = null;
      _domainSourceTaskRequestId = null;
      _domainSourceTaskQuestion = null;
      _domainSourceTaskSources = null;
      _domainSourceTaskUnconfirmed = false;
    }
    final code = error is LumenisCoreException ? error.errorCode : null;
    final rejected =
        error is LumenisCoreException &&
        const {400, 404, 409, 410, 413, 415, 422}.contains(error.statusCode);
    if (rejected && _domainImportStage != _DomainImportStage.startingBrief) {
      // Preserve uncertain writes for replay; rejected input can be corrected.
      _pendingDomainFile = null;
      _pendingDomainProvenance = null;
    }
    _domainImportMessage = denied
        ? _importCopy(
            zh: '资料或当前范围的权限已改变，请核对后重试。',
            en: 'Access to the material or current scope changed. Review permissions before retrying.',
            ko: '자료 또는 현재 범위의 권한이 변경되었습니다. 확인 후 다시 시도하세요.',
          )
        : !_domainContextMatches
        ? _importCopy(
            zh: '当前范围已改变。请返回原主体核对导入结果。',
            en: 'The scope changed. Return to the original subject to reconcile this import.',
            ko: '범위가 변경되었습니다. 원래 주체에서 가져오기 결과를 확인하세요.',
          )
        : code == 'DOCUMENT_EVIDENCE_SIGNING_UNAVAILABLE'
        ? _importCopy(
            zh: '导入服务的证据签名配置暂不可用，本次未导入新资料。请联系工作区管理员恢复服务后，用同一文件重试。',
            en: 'Evidence signing is unavailable. No new material was imported. Ask the workspace administrator to restore the service, then retry the same file.',
            ko: '증거 서명 설정을 사용할 수 없어 새 자료를 가져오지 않았습니다. 작업 공간 관리자에게 복구를 요청한 뒤 같은 파일로 다시 시도하세요.',
          )
        : _domainImportStage == _DomainImportStage.preparing
        ? _importCopy(
            zh: '资料尚未导入。准备导入失败，请核对文件和来源说明，或待服务恢复后重试。',
            en: 'Material was not imported. Import preparation failed. Review the file and source details, or retry when the service is available.',
            ko: '자료를 가져오지 않았습니다. 가져오기 준비에 실패했습니다. 파일과 출처를 확인하거나 서비스 복구 후 다시 시도하세요.',
          )
        : _domainImportStage == _DomainImportStage.startingBrief
        ? rejected
              ? _importCopy(
                  zh: '资料已导入，但整理简报的请求被拒绝。请核对任务状态后继续，无需重新导入资料。',
                  en: 'Material imported. The brief request was rejected. Review the task status before continuing; do not import the material again.',
                  ko: '자료를 가져왔지만 브리핑 요청이 거부되었습니다. 작업 상태를 확인한 뒤 계속하세요. 자료를 다시 가져올 필요는 없습니다.',
                )
              : _importCopy(
                  zh: '资料已导入，简报请求的结果尚未确认。请核对同一任务后继续，无需重新导入资料。',
                  en: 'Material imported. The brief start is unconfirmed. Check the same task before continuing; do not import the material again.',
                  ko: '자료를 가져왔지만 브리핑 시작 결과가 확인되지 않았습니다. 같은 작업을 확인한 뒤 계속하세요. 자료를 다시 가져오지 마세요.',
                )
        : rejected
        ? _importCopy(
            zh: '本次导入请求被拒绝。请核对文件、来源说明与当前范围后重试。',
            en: 'This import request was rejected. Review the file, source details and current scope before retrying.',
            ko: '이번 가져오기 요청이 거부되었습니다. 파일, 출처와 현재 범위를 확인한 뒤 다시 시도하세요.',
          )
        : _importCopy(
            zh: '结果尚未确认。请核对同一资料后重试；已导入资料可继续整理。',
            en: 'The result is unconfirmed. Reconcile the same material; imported sources can continue into the brief.',
            ko: '결과가 확인되지 않았습니다. 같은 자료를 재확인하거나 가져온 자료로 계속하세요.',
          );
  }

  Future<void> _importDomainMaterial() async {
    if (_domainImportBusy ||
        _model.busy ||
        _pending ||
        _model.globalScope ||
        _model.scopeLabel == null) {
      return;
    }
    setState(() {
      _domainImportBusy = true;
      _domainImportStage = _DomainImportStage.preparing;
      _domainImportMessage = null;
    });
    try {
      if (_domainSourceIds.isNotEmpty && !_domainContextMatches) {
        throw const FormatException('Domain import context changed');
      }
      if (_pendingDomainFile == null) {
        final boundContext = jsonEncode(widget.client.currentContextEnvelope);
        final file =
            await (widget.documentPicker ?? PlatformSh02DocumentPicker())
                .pick();
        if (file == null || !mounted) {
          return;
        }
        if (boundContext != jsonEncode(widget.client.currentContextEnvelope)) {
          throw const FormatException('Domain import context changed');
        }
        final provenance = await _describeDomainFile(file);
        if (provenance == null || !mounted) {
          return;
        }
        _pendingDomainFile = file;
        _pendingDomainProvenance = provenance;
        _domainMaterialContext = boundContext;
      }
      if (!_domainContextMatches) {
        throw const FormatException('Domain import context changed');
      }
      final file = _pendingDomainFile!;
      final prepared = _domainImportResult(
        await widget.client.importDomainDocument(
          domainId: widget.domainId,
          filename: file.filename,
          bytes: file.bytes,
          provenance: _pendingDomainProvenance!,
        ),
      );
      if (!mounted || !_domainContextMatches) {
        throw const FormatException('Domain import context changed');
      }
      if (prepared['state'] != 'PREPARED' || prepared['resource'] is! String) {
        throw const FormatException('Domain import preview unavailable');
      }
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: Text(
            _importCopy(
              zh: '确认导入当前范围',
              en: 'Confirm import into this scope',
              ko: '현재 범위로 가져오기 확인',
            ),
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(file.filename),
              Text(_model.scopeLabel!),
              Text('${_pendingDomainProvenance!['rights_statement']}'),
              const SizedBox(height: 12),
              Text(
                _importCopy(
                  zh: '原件及来源将被保留，仅按所选用途使用；导入不证明来源陈述属实。',
                  en: 'The original and provenance are retained for the declared use. Import does not verify source claims.',
                  ko: '원본과 출처를 선언한 용도로 보관합니다. 가져오기는 출처 주장을 검증하지 않습니다.',
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: Text(_importCopy(zh: '取消', en: 'Cancel', ko: '취소')),
            ),
            FilledButton(
              key: const ValueKey('domain-import-confirm'),
              onPressed: () => Navigator.pop(dialogContext, true),
              child: Text(
                _importCopy(
                  zh: '导入并整理简报',
                  en: 'Import and prepare brief',
                  ko: '가져오고 브리핑 정리',
                ),
              ),
            ),
          ],
        ),
      );
      if (confirmed != true || !mounted) {
        _pendingDomainFile = null;
        _pendingDomainProvenance = null;
        return;
      }
      if (!_domainContextMatches) {
        throw const FormatException('Domain import context changed');
      }
      _domainImportStage = _DomainImportStage.importing;
      final imported = _domainImportResult(
        await widget.client.importDomainDocument(
          domainId: widget.domainId,
          filename: file.filename,
          bytes: file.bytes,
          provenance: _pendingDomainProvenance!,
          mode: 'import',
          confirmedResource: prepared['resource'] as String,
        ),
      );
      if (!mounted || !_domainContextMatches) {
        throw const FormatException('Domain import context changed');
      }
      if (imported['source_id'] is! String ||
          imported['evidence_id'] is! int ||
          imported['scope_status'] != 'VERIFIED') {
        throw const FormatException('Domain import receipt unavailable');
      }
      if (!_domainSourceIds.contains(imported['source_id'])) {
        _domainSourceIds.add(imported['source_id'] as String);
      }
      _pendingDomainFile = null;
      _pendingDomainProvenance = null;
      _domainSourceTaskRequestId = null;
      _domainSourceTaskQuestion = null;
      _domainSourceTaskSources = null;
      await _startImportedDomainBrief();
    } catch (error) {
      if (mounted) {
        _domainImportFailed(error);
      }
    } finally {
      if (mounted) {
        setState(() => _domainImportBusy = false);
      }
    }
  }

  Future<void> _continueDomainBrief() async {
    if (_domainImportBusy || _model.busy || _pending) {
      return;
    }
    setState(() => _domainImportBusy = true);
    try {
      await _startImportedDomainBrief();
    } catch (error) {
      if (mounted) {
        _domainImportFailed(error);
      }
    } finally {
      if (mounted) {
        setState(() => _domainImportBusy = false);
      }
    }
  }

  Widget _domainImportControls() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Wrap(
        spacing: 12,
        runSpacing: 10,
        children: [
          FilledButton.tonalIcon(
            key: const ValueKey('source-brief/import-domain-material'),
            onPressed:
                _domainImportBusy ||
                    _model.busy ||
                    _pending ||
                    _domainSourceTaskUnconfirmed ||
                    _questionInvalid ||
                    _model.scopeLabel == null ||
                    _model.globalScope
                ? null
                : _importDomainMaterial,
            icon: const Icon(Icons.upload_file),
            label: Text(
              _pendingDomainFile == null
                  ? _importCopy(
                      zh: '导入资料',
                      en: 'Import material',
                      ko: '자료 가져오기',
                    )
                  : _importCopy(
                      zh: '核对同一资料导入',
                      en: 'Reconcile this import',
                      ko: '동일 자료 가져오기 재확인',
                    ),
            ),
          ),
          if (_domainSourceIds.isNotEmpty)
            TextButton(
              key: const ValueKey('source-brief/continue-domain-material'),
              onPressed: _domainImportBusy || _model.busy || _pending
                  ? null
                  : _continueDomainBrief,
              child: Text(
                _importCopy(
                  zh: '继续整理已导入资料',
                  en: 'Continue with imported material',
                  ko: '가져온 자료로 계속',
                ),
              ),
            ),
        ],
      ),
      if (_domainImportBusy) const LinearProgressIndicator(minHeight: 2),
      if (_domainImportMessage != null)
        Padding(
          padding: const EdgeInsets.only(top: 10),
          child: Semantics(
            liveRegion: true,
            child: Text(_domainImportMessage!),
          ),
        ),
    ],
  );

  Future<void> _open() async {
    final value = _reference.text.trim();
    setState(() => _referenceRequired = value.isEmpty);
    if (value.isEmpty) return;
    if (value.startsWith('task_')) {
      await _model.analyseSources(taskId: value);
      return;
    }
    if (_taskReference) {
      await _model.openTask(value);
    } else {
      await _model.reopenJob(value);
    }
  }

  Future<void> _reviseSavedResearch(
    SourceBriefSavedWork work,
    SourceBriefCopy copy,
  ) async {
    final scopeKey = _model.result?.scope.scopeKey;
    final title = TextEditingController(text: work.title);
    final markdown = TextEditingController(text: work.markdown);
    final reason = TextEditingController();
    try {
      final values = await showDialog<Map<String, String>>(
        context: context,
        builder: (dialogContext) => AnimatedBuilder(
          animation: _model,
          builder: (dialogContext, _) {
            final valid =
                _model.savedHistory.contains(work) &&
                _model.result?.scope.scopeKey == scopeKey;
            if (!valid) {
              WidgetsBinding.instance.addPostFrameCallback((_) {
                if (dialogContext.mounted &&
                    !_model.savedHistory.contains(work)) {
                  Navigator.of(dialogContext).maybePop();
                }
              });
            }
            return AlertDialog(
              title: Text(copy.text('reviseResearch')),
              content: SizedBox(
                width: 720,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      TextField(
                        controller: title,
                        enabled: valid,
                        maxLength: 300,
                        decoration: InputDecoration(
                          labelText: copy.text('researchTitle'),
                        ),
                      ),
                      TextField(
                        controller: reason,
                        enabled: valid,
                        maxLength: 4000,
                        decoration: InputDecoration(
                          labelText: copy.text('revisionReason'),
                        ),
                      ),
                      TextField(
                        controller: markdown,
                        enabled: valid,
                        minLines: 8,
                        maxLines: 18,
                        maxLength: 100000,
                        decoration: InputDecoration(
                          labelText: copy.text('researchContent'),
                          alignLabelWithHint: true,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(dialogContext).pop(),
                  child: Text(copy.text('cancel')),
                ),
                FilledButton(
                  key: const ValueKey('source-brief/revision-confirm'),
                  onPressed:
                      !valid ||
                          title.text.trim().isEmpty ||
                          reason.text.trim().isEmpty ||
                          markdown.text.trim().isEmpty
                      ? null
                      : () => Navigator.of(dialogContext).pop({
                          'title': title.text,
                          'reason': reason.text,
                          'markdown': markdown.text,
                        }),
                  child: Text(copy.text('saveRevision')),
                ),
              ],
            );
          },
        ),
      );
      if (!mounted ||
          values == null ||
          !_model.savedHistory.contains(work) ||
          _model.result?.scope.scopeKey != scopeKey) {
        return;
      }
      _cancelRevealForUserInteraction();
      await _model.reviseSavedResearchVersion(
        parent: work,
        title: values['title']!,
        reason: values['reason']!,
        markdown: values['markdown']!,
      );
    } finally {
      title.dispose();
      markdown.dispose();
      reason.dispose();
    }
  }

  Future<void> _adoptToShared(SourceBriefCopy copy) async {
    if (_model.busy) return;
    if (_model.sharedAdoptionPreview == null) {
      _cancelRevealForUserInteraction();
      await _model.prepareSharedAdoption();
    }
    if (!mounted) return;
    final preview = _model.sharedAdoptionPreview;
    final result = _model.result;
    if (preview == null ||
        result == null ||
        preview.jobId != result.jobId ||
        preview.sourceBriefHash != result.artifactHash ||
        preview.sourceScopeKey != result.scope.scopeKey) {
      return;
    }
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AnimatedBuilder(
        animation: _model,
        builder: (dialogContext, _) {
          final current = _model.sharedAdoptionPreview;
          final currentResult = _model.result;
          final valid =
              current?.requestId == preview.requestId &&
              currentResult?.jobId == preview.jobId &&
              currentResult?.artifactHash == preview.sourceBriefHash &&
              currentResult?.scope.scopeKey == preview.sourceScopeKey;
          if (!valid) {
            WidgetsBinding.instance.addPostFrameCallback((_) {
              if (dialogContext.mounted) {
                Navigator.of(dialogContext).maybePop(false);
              }
            });
          }
          return AlertDialog(
            title: Text(copy.text('sharedAdoptionConfirmTitle')),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(preview.title),
                const SizedBox(height: 12),
                Text(copy.text('sharedAdoptionTarget')),
                const SizedBox(height: 8),
                Text(
                  copy
                      .text('sharedAdoptionCounts')
                      .replaceFirst(
                        '{sources}',
                        '${preview.guardedSourceCount}',
                      )
                      .replaceFirst(
                        '{citations}',
                        '${preview.displayedCitations}',
                      ),
                ),
                const SizedBox(height: 12),
                Text(copy.text('sharedAdoptionDisclaimer')),
              ],
            ),
            actions: [
              TextButton(
                key: const ValueKey('source-brief/shared-adoption/cancel'),
                onPressed: () => Navigator.of(dialogContext).pop(false),
                child: Text(copy.text('cancel')),
              ),
              FilledButton(
                key: const ValueKey('source-brief/shared-adoption/confirm'),
                onPressed: valid
                    ? () => Navigator.of(dialogContext).pop(true)
                    : null,
                child: Text(copy.text('sharedAdoptionConfirm')),
              ),
            ],
          );
        },
      ),
    );
    if (!mounted || confirmed != true) return;
    final currentPreview = _model.sharedAdoptionPreview;
    final currentResult = _model.result;
    if (currentPreview?.requestId != preview.requestId ||
        currentResult?.jobId != preview.jobId ||
        currentResult?.artifactHash != preview.sourceBriefHash ||
        currentResult?.scope.scopeKey != preview.sourceScopeKey) {
      return;
    }
    _cancelRevealForUserInteraction();
    await _model.applySharedAdoption();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: _model,
    builder: (context, _) {
      final copy = SourceBriefCopy.of(context);
      final palette = LumenisTheme.of(context);
      if (_businessWork) {
        return BusinessWorkPanel(
          client: widget.client,
          domainId: widget.domainId,
          source: _model.result,
          onReturn: () => setState(() => _businessWork = false),
        );
      }
      return LayoutBuilder(
        builder: (context, constraints) {
          final narrow =
              constraints.maxWidth < 980 ||
              MediaQuery.textScalerOf(context).scale(16) > 23;
          final result = _model.result;
          final paper = Container(
            key: const ValueKey('source-brief/report-paper'),
            constraints: BoxConstraints(minHeight: narrow ? 320 : 440),
            decoration: LumenisTheme.paper(palette, radius: 8),
            child: Material(
              type: MaterialType.transparency,
              child: Padding(
                padding: EdgeInsets.symmetric(
                  horizontal: narrow ? 22 : 40,
                  vertical: narrow ? 26 : 36,
                ),
                child: result == null
                    ? _emptyPaper(copy)
                    : _animatedResultSummary(copy, result),
              ),
            ),
          );
          final tools = Container(
            key: const ValueKey('source-brief/source-rail'),
            decoration: LumenisTheme.panel(palette, recessed: true),
            child: Material(
              type: MaterialType.transparency,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(18, 12, 18, 18),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (result != null) _sources(copy, result),
                    _savedResearchHistory(copy),
                    if (!_model.globalScope && _model.scopeLabel != null)
                      TextButton.icon(
                        onPressed: _model.busy
                            ? null
                            : () => setState(() => _businessWork = true),
                        icon: const Icon(Icons.history_rounded, size: 18),
                        label: Text(
                          context.lumenisL10n.text('business.work.recent'),
                        ),
                      ),
                    const SizedBox(height: 14),
                    _recoveryOptions(copy),
                    ExpansionTile(
                      key: const ValueKey('source-brief/preferences'),
                      tilePadding: EdgeInsets.zero,
                      childrenPadding: const EdgeInsets.only(bottom: 12),
                      maintainState: true,
                      title: Text(
                        _importCopy(
                          zh: '阅读偏好',
                          en: 'Reading preferences',
                          ko: '읽기 설정',
                        ),
                        style: const TextStyle(fontSize: 13),
                      ),
                      onExpansionChanged: (_) =>
                          _cancelRevealForUserInteraction(),
                      children: [_motionChoiceControl(copy)],
                    ),
                  ],
                ),
              ),
            ),
          );
          return Scrollbar(
            controller: _scroll,
            child: SingleChildScrollView(
              controller: _scroll,
              padding: EdgeInsets.fromLTRB(
                narrow ? 16 : 28,
                16,
                narrow ? 16 : 28,
                36,
              ),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 1320),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Align(
                        alignment: Alignment.centerLeft,
                        child: TextButton.icon(
                          onPressed: widget.onReturn,
                          icon: const Icon(Icons.arrow_back, size: 18),
                          label: Text(copy.text('return')),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 20,
                        runSpacing: 12,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Text(
                            copy.text('title'),
                            style: TextStyle(
                              color: palette.foreground,
                              fontSize: narrow ? 27 : 34,
                              letterSpacing: -.6,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          Text(
                            _model.scopeLabel == null
                                ? copy.text('scopeUnknown')
                                : _model.globalScope
                                ? copy.text('global')
                                : _model.scopeLabel!,
                            style: TextStyle(
                              color: palette.muted,
                              fontSize: 14,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 22),
                      Wrap(
                        spacing: 18,
                        runSpacing: 12,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          if (!_model.globalScope ||
                              _pendingDomainFile != null ||
                              _domainSourceIds.isNotEmpty)
                            _domainImportControls(),
                          if (result != null && !result.scope.globalScope)
                            FilledButton.icon(
                              key: const ValueKey(
                                'source-brief/continue-business',
                              ),
                              onPressed: _model.busy
                                  ? null
                                  : () => setState(() => _businessWork = true),
                              icon: const Icon(
                                Icons.assignment_outlined,
                                size: 18,
                              ),
                              label: Text(
                                context.lumenisL10n.text('business.work.entry'),
                              ),
                            ),
                          if (_model.taskId != null || result != null)
                            TextButton.icon(
                              onPressed:
                                  _model.busy ||
                                      _domainImportBusy ||
                                      _pending ||
                                      _domainSourceTaskUnconfirmed
                                  ? null
                                  : _newBrief,
                              icon: const Icon(Icons.add_rounded, size: 18),
                              label: Text(copy.text('new')),
                            ),
                        ],
                      ),
                      if (_model.busy) ...[
                        const SizedBox(height: 16),
                        Semantics(
                          liveRegion: true,
                          label: copy.text('loading'),
                          child: const LinearProgressIndicator(minHeight: 2),
                        ),
                      ],
                      if (_model.errorKind case final error?) ...[
                        const SizedBox(height: 18),
                        Semantics(
                          liveRegion: true,
                          child: Text(
                            copy.text(error.name),
                            style: TextStyle(
                              color: palette.danger,
                              height: 1.55,
                            ),
                          ),
                        ),
                        if (_model.taskId == null)
                          Align(
                            alignment: Alignment.centerLeft,
                            child: TextButton(
                              onPressed: _model.busy ? null : _model.initialize,
                              child: Text(copy.text('retry')),
                            ),
                          ),
                      ],
                      if (_model.taskId != null) ...[
                        const SizedBox(height: 12),
                        _task(copy),
                      ],
                      const SizedBox(height: 24),
                      if (narrow) ...[
                        paper,
                        const SizedBox(height: 24),
                        tools,
                      ] else
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(child: paper),
                            const SizedBox(width: 24),
                            SizedBox(width: 300, child: tools),
                          ],
                        ),
                    ],
                  ),
                ),
              ),
            ),
          );
        },
      );
    },
  );

  Widget _emptyPaper(SourceBriefCopy copy) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Icon(
        Icons.description_outlined,
        size: 32,
        color: LumenisTheme.of(context).cth,
      ),
      const SizedBox(height: 28),
      Text(
        copy.text('empty'),
        style: const TextStyle(fontSize: 25, height: 1.3),
      ),
      const SizedBox(height: 24),
      if (_model.taskId == null) ...[
        TextField(
          key: const ValueKey('source-brief/question'),
          controller: _question,
          onChanged: (_) => setState(() {}),
          enabled:
              !_model.busy &&
              !_domainImportBusy &&
              _domainSourceTaskRequestId == null,
          minLines: 2,
          maxLines: 5,
          maxLength: 1500,
          decoration: InputDecoration(
            labelText: _importCopy(
              zh: '想从资料中了解什么？',
              en: 'What would you like to learn from the material?',
              ko: '자료에서 무엇을 알아보고 싶으신가요?',
            ),
            counterText: '',
            errorText: _questionInvalid
                ? _importCopy(
                    zh: '请输入4至1500字的问题。',
                    en: 'Use a question between 4 and 1,500 characters.',
                    ko: '질문을 4~1,500자로 입력하세요.',
                  )
                : null,
          ),
        ),
        const SizedBox(height: 18),
      ],
      if (_model.taskId == null)
        OutlinedButton.icon(
          key: const ValueKey('source-brief/create'),
          onPressed:
              _model.busy || _model.scopeLabel == null || _questionInvalid
              ? null
              : () {
                  if (_domainSourceIds.isNotEmpty) {
                    unawaited(_continueDomainBrief());
                  } else {
                    unawaited(_model.start(businessQuestion: _question.text));
                  }
                },
          icon: const Icon(Icons.description_outlined, size: 18),
          label: Text(copy.text('create')),
        ),
    ],
  );

  void _newBrief() {
    // An uncertain imported-source request must be reconciled with its frozen
    // question before a different request can be created.
    if (_domainSourceTaskUnconfirmed) return;
    setState(() {
      _domainSourceTaskRequestId = null;
      _domainSourceTaskQuestion = null;
      _domainSourceTaskSources = null;
      _domainImportMessage = null;
    });
    _model.clear();
  }

  Widget _recoveryOptions(SourceBriefCopy copy) => ExpansionTile(
    key: const ValueKey('source-brief/recovery-options'),
    tilePadding: EdgeInsets.zero,
    childrenPadding: const EdgeInsets.only(bottom: 18),
    maintainState: true,
    title: Text(
      _importCopy(zh: '按编号恢复工作', en: 'Recover by reference', ko: '번호로 작업 복구'),
      style: const TextStyle(fontSize: 13),
    ),
    onExpansionChanged: (_) => _cancelRevealForUserInteraction(),
    expandedCrossAxisAlignment: CrossAxisAlignment.start,
    children: [
      if (_model.taskId case final task?) ...[
        SelectableText(task, style: const TextStyle(fontSize: 12)),
        TextButton.icon(
          key: const ValueKey('source-brief/copy-task'),
          onPressed: () => _copy(task),
          icon: const Icon(Icons.copy_outlined, size: 16),
          label: Text(copy.text('copyTask')),
        ),
      ],
      if (_model.result case final result?) ...[
        SelectableText(result.jobId, style: const TextStyle(fontSize: 12)),
        const SizedBox(height: 12),
      ],
      Wrap(
        spacing: 8,
        runSpacing: 6,
        children: [
          ChoiceChip(
            label: Text(copy.text('reportKind')),
            selected: !_taskReference,
            onSelected: _model.busy
                ? null
                : (_) => setState(() => _taskReference = false),
          ),
          ChoiceChip(
            label: Text(copy.text('taskKind')),
            selected: _taskReference,
            onSelected: _model.busy
                ? null
                : (_) => setState(() => _taskReference = true),
          ),
        ],
      ),
      const SizedBox(height: 12),
      TextField(
        key: const ValueKey('source-brief/reference'),
        controller: _reference,
        enabled: !_model.busy,
        maxLength: 128,
        textInputAction: TextInputAction.go,
        onSubmitted: (_) => _open(),
        decoration: InputDecoration(
          labelText: copy.text('reference'),
          counterText: '',
          errorText: _referenceRequired ? copy.text('referenceRequired') : null,
        ),
      ),
      const SizedBox(height: 12),
      OutlinedButton(
        onPressed: _model.busy ? null : _open,
        child: Text(copy.text('open')),
      ),
    ],
  );

  Widget _motionChoiceControl(SourceBriefCopy copy) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(copy.text('motionChoiceTitle')),

      const SizedBox(height: 8),
      Wrap(
        spacing: 8,
        runSpacing: 4,
        children: [
          ChoiceChip(
            key: const ValueKey('source-brief/reveal/full'),
            label: Text(copy.text('motionFull')),
            selected: _motionChoice == GeneratedResultMotionChoice.full,
            onSelected: _motionPreferenceReady
                ? (_) => _selectMotionChoice(GeneratedResultMotionChoice.full)
                : null,
          ),
          ChoiceChip(
            key: const ValueKey('source-brief/reveal/system'),
            label: Text(copy.text('motionSystem')),
            selected: _motionChoice == GeneratedResultMotionChoice.followSystem,
            onSelected: _motionPreferenceReady
                ? (_) => _selectMotionChoice(
                    GeneratedResultMotionChoice.followSystem,
                  )
                : null,
          ),
          ChoiceChip(
            key: const ValueKey('source-brief/reveal/off'),
            label: Text(copy.text('motionOff')),
            selected: _motionChoice == GeneratedResultMotionChoice.off,
            onSelected: _motionPreferenceReady
                ? (_) => _selectMotionChoice(GeneratedResultMotionChoice.off)
                : null,
          ),
        ],
      ),
      if (_motionPreferenceSaveFailed)
        Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text(
            copy.text('motionPreferenceSaveFailed'),
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.4,
            ),
          ),
        ),
    ],
  );

  Widget _animatedResultSummary(
    SourceBriefCopy copy,
    SourceBriefResult result,
  ) {
    final palette = LumenisTheme.of(context);
    return GeneratedResultReveal(
      key: _resultRevealKey,
      resultVersion:
          '${result.scope.scopeKey}:${result.jobId}:${result.artifactHash}',
      arrivalToken:
          _motionPreferenceReady &&
              _model.resultArrivalToken != _cancelledResultArrivalToken
          ? _model.resultArrivalToken
          : null,
      choice: _motionChoice,
      skipLabel: copy.text('motionSkip'),
      accent: palette.accent,
      foreground: palette.foreground,
      onUserInteraction: _cancelRevealForUserInteraction,
      child: _resultSummary(copy, result),
    );
  }

  Widget _task(SourceBriefCopy copy) => Wrap(
    spacing: 14,
    runSpacing: 6,
    crossAxisAlignment: WrapCrossAlignment.center,
    children: [
      Semantics(
        liveRegion: true,
        child: Text(
          copy.text(
            _model.result != null
                ? 'taskDone'
                : _model.taskState == SourceBriefTaskState.succeeded &&
                      _model.errorKind != null
                ? 'unknown'
                : _model.taskState.name,
          ),
          style: TextStyle(color: LumenisTheme.of(context).muted, fontSize: 13),
        ),
      ),
      TextButton(
        onPressed: _model.busy
            ? null
            : () {
                _cancelRevealForUserInteraction();
                _model.refreshTask();
              },
        child: Text(copy.text('refresh')),
      ),
      if (_model.canResume)
        FilledButton(
          onPressed: _model.busy
              ? null
              : () {
                  _cancelRevealForUserInteraction();
                  _model.resume();
                },
          child: Text(copy.text('resume')),
        ),
    ],
  );

  Widget _researchBody(
    SourceBriefCopy copy,
    SourceBriefResult result,
    SourceBriefResearchAnalysis research,
  ) {
    final muted = LumenisTheme.of(context).muted;
    String sourceTitle(String id) =>
        result.records.firstWhere((source) => source.sourceId == id).title ??
        copy.text('untitled');
    final summary = research.summary;
    final speech = [
      result.businessQuestion,
      summary,
      ...research.findings.map((finding) => finding.content),
      ...research.questions.map((question) => question.statement),
      ...research.limitations,
    ].whereType<String>().join('\n\n');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (summary != null)
          SelectableText(
            summary,
            style: const TextStyle(fontSize: 17, height: 1.8),
          ),
        if (research.status == 'source_use_unavailable')
          Text(
            _importCopy(
              zh: '原文使用权限尚未核验，请核对来源后重试。',
              en: 'Use of the original text could not be verified. Check the sources before retrying.',
              ko: '원문 사용 권한을 확인하지 못했습니다. 출처를 확인한 후 다시 시도하세요.',
            ),
            style: TextStyle(color: muted, height: 1.6),
          ),
        if (research.findings.isNotEmpty) ...[
          const SizedBox(height: 16),
          Text(
            _importCopy(
              zh: '以下为来源原文摘录，尚未独立核实。',
              en: 'The following excerpts are source statements, not independently verified facts.',
              ko: '다음 인용문은 출처의 서술이며 독립적으로 검증된 사실이 아닙니다.',
            ),
            style: TextStyle(color: muted, fontSize: 12, height: 1.6),
          ),
          ReadAloudAction(
            sessionId: 'source-brief-research:${result.reportId}',
            scopeVersion:
                '${result.scope.scopeKey}:${result.reportId}:${result.artifactHash}',
            text: speech,
            purpose: ReadAloudPurpose.sourceBrief,
            onUserInteraction: _cancelRevealForUserInteraction,
          ),
        ],
        for (final (index, finding) in research.findings.indexed) ...[
          const SizedBox(height: 28),
          Text(
            '${(index + 1).toString().padLeft(2, '0')}  ${sourceTitle(finding.sourceId)}',
            style: TextStyle(color: muted, fontSize: 13, height: 1.6),
          ),
          const SizedBox(height: 12),
          SelectableText(
            finding.content,
            key: ValueKey('source-brief/finding/${finding.id}'),
            style: const TextStyle(fontSize: 16, height: 1.85),
          ),
          if (finding.truncated == true)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                _importCopy(
                  zh: '节选 · 完整内容见来源',
                  en: 'Excerpt · See the source for the full text',
                  ko: '발췌 · 전체 내용은 출처에서 확인하세요',
                ),
                style: TextStyle(color: muted, fontSize: 12),
              ),
            ),
        ],
        if (research.questions.isNotEmpty) ...[
          const SizedBox(height: 32),
          _sectionTitle(
            _importCopy(zh: '接下来核验', en: 'Questions to verify', ko: '다음 확인 사항'),
          ),
          for (final question in research.questions)
            Padding(
              padding: const EdgeInsets.only(top: 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(switch (question.status) {
                    'challenged' => _importCopy(
                      zh: '已提出异议',
                      en: 'Challenged',
                      ko: '이의 제기됨',
                    ),
                    'rejected' => _importCopy(
                      zh: '已否决',
                      en: 'Rejected',
                      ko: '기각됨',
                    ),
                    'reinstated' => _importCopy(
                      zh: '恢复待核验',
                      en: 'Reinstated for review',
                      ko: '다시 검토 중',
                    ),
                    _ => _importCopy(zh: '待核验', en: 'To verify', ko: '확인 필요'),
                  }, style: TextStyle(color: muted, fontSize: 12)),
                  const SizedBox(height: 6),
                  SelectableText(
                    question.statement,
                    style: const TextStyle(height: 1.7),
                  ),
                  for (final need in question.validationNeeded)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: SelectableText(
                        need,
                        style: TextStyle(color: muted, height: 1.6),
                      ),
                    ),
                ],
              ),
            ),
        ],
        if (research.limitations.isNotEmpty ||
            research.numberChecks.any((c) => c.literals.isNotEmpty)) ...[
          const SizedBox(height: 26),
          ExpansionTile(
            key: const ValueKey('source-brief/research-limits'),
            tilePadding: EdgeInsets.zero,
            expandedCrossAxisAlignment: CrossAxisAlignment.start,
            title: Text(
              _importCopy(
                zh: '核对数字与局限',
                en: 'Numbers and limitations',
                ko: '수치와 한계 확인',
              ),
              style: const TextStyle(fontSize: 13),
            ),
            onExpansionChanged: (_) => _cancelRevealForUserInteraction(),
            children: [
              if (research.numberChecks.any((c) => c.literals.isNotEmpty)) ...[
                Text(
                  _importCopy(
                    zh: '这些数字来自原文。单位、币种、期间与分母尚未统一，不能直接比较或推定效果。',
                    en: 'These numbers appear in the sources. Units, currency, periods and denominators have not been aligned; they cannot establish comparisons or results.',
                    ko: '원문에 등장한 수치입니다. 단위·통화·기간·분모가 일치하지 않아 직접 비교하거나 성과로 해석할 수 없습니다.',
                  ),
                  style: TextStyle(color: muted, height: 1.6),
                ),
                for (final check in research.numberChecks.where(
                  (c) => c.literals.isNotEmpty,
                ))
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: _line(
                      sourceTitle(check.sourceId),
                      check.literals.join(' · '),
                    ),
                  ),
              ],
              for (final limitation in research.limitations)
                Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: SelectableText(
                    limitation,
                    style: TextStyle(color: muted, height: 1.6),
                  ),
                ),
            ],
          ),
        ],
      ],
    );
  }

  Widget _resultSummary(
    SourceBriefCopy copy,
    SourceBriefResult result,
  ) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Row(
        children: [
          Expanded(
            child: Semantics(
              liveRegion: true,
              child: Text(
                copy.text('saved'),
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  fontSize: 12,
                ),
              ),
            ),
          ),
          IconButton(
            key: const ValueKey('source-brief/copy-job'),
            onPressed: () => _copy(result.jobId),
            tooltip: copy.text('copyJob'),
            icon: const Icon(Icons.copy_outlined, size: 17),
          ),
        ],
      ),
      const SizedBox(height: 14),
      if (result.businessQuestion case final question?) ...[
        SelectableText(
          question,
          style: const TextStyle(
            fontSize: 24,
            height: 1.4,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 24),
      ],
      if (result.researchAnalysis case final research?)
        _researchBody(copy, result, research),
      if (result.analysis == null && result.researchAnalysis == null) ...[
        Text(
          copy.text(switch (result.businessAnalysisState) {
            SourceBriefBusinessAnalysisState.notRequested =>
              'analysisNotRequested',
            SourceBriefBusinessAnalysisState.draft => 'analysisDraft',
            SourceBriefBusinessAnalysisState.unavailable ||
            SourceBriefBusinessAnalysisState.error => 'analysisError',
            SourceBriefBusinessAnalysisState.unknown => 'analysisUnknown',
          }),
          style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.6),
        ),
        const SizedBox(height: 26),
        for (final (index, source) in result.records.indexed) ...[
          Text(
            '${index + 1}'.padLeft(2, '0'),
            style: TextStyle(
              fontSize: 12,
              color: LumenisTheme.of(context).muted,
            ),
          ),
          const SizedBox(height: 8),
          SelectableText(
            source.title ?? copy.text('untitled'),
            style: const TextStyle(
              fontSize: 21,
              height: 1.5,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 24),
        ],
        if (result.records.isEmpty) Text(copy.text('noSources')),
      ],
      if (result.analysis case final analysis?)
        ReadAloudAction(
          sessionId: 'source-brief:${result.reportId}',
          scopeVersion:
              '${result.scope.scopeKey}:${result.reportId}:${result.artifactHash}',
          text: _speechText(result, analysis),
          purpose: ReadAloudPurpose.sourceBrief,
          onUserInteraction: _cancelRevealForUserInteraction,
        ),
      if (result.analysis case final analysis?) ...[
        for (final observation in analysis.sourceObservations) ...[
          const SizedBox(height: 16),
          _line(copy.text('observations'), observation.excerpt),
          SelectableText(
            observation.sourceId,
            style: const TextStyle(fontSize: 12),
          ),
        ],
        for (final interpretation in analysis.interpretations) ...[
          const SizedBox(height: 16),
          _line(copy.text('interpretations'), interpretation.text),
          SelectableText(
            interpretation.sourceIds.join(' · '),
            style: const TextStyle(fontSize: 12),
          ),
        ],
        for (final action in analysis.proposedActions) ...[
          const SizedBox(height: 20),
          _line(copy.text('actions'), action.action),
          const SizedBox(height: 8),
          _line(copy.text('reason'), action.reason),
          const SizedBox(height: 8),
          _line(copy.text('check'), action.check),
          const SizedBox(height: 8),
          SelectableText(
            action.sourceIds.join(' · '),
            style: const TextStyle(fontSize: 12),
          ),
          if (action.pilot case final pilot?) ...[
            const SizedBox(height: 12),
            _line(copy.text('audience'), pilot.audience),
            const SizedBox(height: 8),
            _line(copy.text('procedure'), pilot.procedure),
            const SizedBox(height: 8),
            _line(copy.text('measure'), pilot.measure),
            const SizedBox(height: 8),
            _line(copy.text('continueIf'), pilot.continueIf),
            const SizedBox(height: 8),
            _line(copy.text('stopIf'), pilot.stopIf),
          ],
        ],
        if (analysis.unknowns.isNotEmpty) ...[
          const SizedBox(height: 20),
          _line(copy.text('unknowns'), analysis.unknowns.join('\n\n')),
        ],
      ],

      const SizedBox(height: 24),
      Divider(color: LumenisTheme.of(context).line),
      const SizedBox(height: 12),
      FilledButton.tonalIcon(
        key: const ValueKey('source-brief/save-research'),
        onPressed: _model.busy
            ? null
            : () {
                _cancelRevealForUserInteraction();
                if (_model.savedWorkState == SourceBriefSavedWorkState.saved ||
                    _model.savedWorkState ==
                        SourceBriefSavedWorkState.reopened) {
                  _model.reopenSavedResearch();
                } else {
                  _model.saveAsEditableResearch(title: copy.text('title'));
                }
              },
        icon: Icon(
          _model.savedWorkState == SourceBriefSavedWorkState.saving
              ? Icons.hourglass_top
              : _model.savedWorkState == SourceBriefSavedWorkState.saved ||
                    _model.savedWorkState == SourceBriefSavedWorkState.reopened
              ? Icons.open_in_new
              : Icons.save_outlined,
          size: 18,
        ),
        label: Text(
          _model.savedWorkState == SourceBriefSavedWorkState.saving
              ? copy.text('savingResearch')
              : _model.savedWorkState == SourceBriefSavedWorkState.saved ||
                    _model.savedWorkState == SourceBriefSavedWorkState.reopened
              ? copy.text('openSavedResearch')
              : copy.text('saveResearch'),
        ),
      ),
      if (_model.savedWorkState == SourceBriefSavedWorkState.saved ||
          _model.savedWorkState == SourceBriefSavedWorkState.reopened) ...[
        const SizedBox(height: 8),
        Semantics(
          liveRegion: true,
          child: Text(
            copy.text(
              _model.savedWorkState == SourceBriefSavedWorkState.reopened
                  ? 'reopenedResearch'
                  : 'savedResearch',
            ),
          ),
        ),
      ],
      if (_model.savedWorkState == SourceBriefSavedWorkState.failed) ...[
        const SizedBox(height: 8),
        Semantics(
          liveRegion: true,
          child: Text(
            copy.text(
              _model.savedWorkErrorKind == SourceBriefErrorKind.accessDenied
                  ? 'saveResearchDenied'
                  : 'saveResearchFailed',
            ),
            style: TextStyle(color: LumenisTheme.of(context).danger),
          ),
        ),
      ],
      if (_model.savedWorkState == SourceBriefSavedWorkState.reopened &&
          _model.savedWorkMarkdown != null) ...[
        const SizedBox(height: 12),
        SelectableText(
          _model.savedWorkMarkdown!,
          key: const ValueKey('source-brief/reopened-research'),
        ),
      ],
      const SizedBox(height: 16),
      OutlinedButton.icon(
        key: const ValueKey('source-brief/adopt-to-shared'),
        onPressed: _model.busy ? null : () => _adoptToShared(copy),
        icon: Icon(switch (_model.sharedAdoptionState) {
          SourceBriefSharedAdoptionState.preparing ||
          SourceBriefSharedAdoptionState.applying => Icons.hourglass_top,
          SourceBriefSharedAdoptionState.reopened => Icons.open_in_new,
          _ => Icons.drive_file_move_outline,
        }, size: 18),
        label: Text(switch (_model.sharedAdoptionState) {
          SourceBriefSharedAdoptionState.preparing => copy.text(
            'sharedAdoptionPreparing',
          ),
          SourceBriefSharedAdoptionState.applying => copy.text(
            'sharedAdoptionApplying',
          ),
          SourceBriefSharedAdoptionState.reopened => copy.text(
            'sharedAdoptionDone',
          ),
          _ => copy.text('sharedAdoptionAction'),
        }),
      ),
      if (_model.sharedAdoptionState ==
          SourceBriefSharedAdoptionState.reopened) ...[
        const SizedBox(height: 8),
        Semantics(
          liveRegion: true,
          child: Text(copy.text('sharedAdoptionReopened')),
        ),
        if (_model.sharedAdoptedWork case final adopted?) ...[
          const SizedBox(height: 12),
          SelectableText(
            adopted.markdown,
            key: const ValueKey('source-brief/shared-adoption/reopened'),
          ),
        ],
      ],
      if (_model.sharedAdoptionState ==
          SourceBriefSharedAdoptionState.failed) ...[
        const SizedBox(height: 8),
        Semantics(
          liveRegion: true,
          child: Text(
            copy.text(
              _model.sharedAdoptionErrorKind ==
                      SourceBriefErrorKind.accessDenied
                  ? 'sharedAdoptionDenied'
                  : 'sharedAdoptionFailed',
            ),
            style: TextStyle(color: LumenisTheme.of(context).danger),
          ),
        ),
      ],
      const SizedBox(height: 24),

      const SizedBox(height: 20),
      ExpansionTile(
        key: const ValueKey('source-brief/result-details'),
        tilePadding: EdgeInsets.zero,
        childrenPadding: const EdgeInsets.only(bottom: 18),
        maintainState: true,
        expandedCrossAxisAlignment: CrossAxisAlignment.start,
        title: Text(
          _importCopy(
            zh: '来源、审核与方法',
            en: 'Sources, review and methods',
            ko: '출처·검토·방법',
          ),
          style: const TextStyle(fontSize: 13),
        ),
        onExpansionChanged: (_) => _cancelRevealForUserInteraction(),
        children: [
          if (result.markdown case final markdown?) ...[
            ExpansionTile(
              key: const ValueKey('source-brief/original-report'),
              tilePadding: EdgeInsets.zero,
              title: Text(
                _importCopy(
                  zh: '完整来源记录',
                  en: 'Full source record',
                  ko: '전체 출처 기록',
                ),
              ),
              children: [SelectableText(markdown)],
            ),
            const SizedBox(height: 16),
          ],
          _line(
            copy.text('count'),
            result.sourceCount?.toString() ?? copy.text('unknownValue'),
          ),
          const SizedBox(height: 20),
          _sectionTitle(copy.text('review')),
          const SizedBox(height: 8),
          Text(
            copy.text(
              result.reviewStatus == 'HUMAN_PENDING'
                  ? 'reviewPending'
                  : 'reviewUnknown',
            ),
            style: const TextStyle(height: 1.6),
          ),
          const SizedBox(height: 24),
          _sectionTitle(copy.text('analysis')),
          const SizedBox(height: 8),
          Text(
            copy.text(switch (result.businessAnalysisState) {
              SourceBriefBusinessAnalysisState.notRequested =>
                'analysisNotRequested',
              SourceBriefBusinessAnalysisState.draft => 'analysisDraft',
              SourceBriefBusinessAnalysisState.unavailable ||
              SourceBriefBusinessAnalysisState.error => 'analysisError',
              SourceBriefBusinessAnalysisState.unknown => 'analysisUnknown',
            }),
            style: const TextStyle(height: 1.6),
          ),
          const SizedBox(height: 16),
          _sampleMetadata(copy, result),
          _sectionTitle(copy.text('sourceStatistics')),
          const SizedBox(height: 8),
          Text(copy.text('sourceStatisticsHint')),
          const SizedBox(height: 8),
          FilledButton.tonal(
            onPressed: _model.busy
                ? null
                : () {
                    _cancelRevealForUserInteraction();
                    _model.analyseSources();
                  },
            child: Text(copy.text('calculateSources')),
          ),
          if (_model.sourceStatistics case final statistics?) ...[
            const SizedBox(height: 12),
            Semantics(
              liveRegion: true,
              child: Text(copy.text('statisticsSaved')),
            ),
            _line(
              copy.text('uniqueSourceCount'),
              statistics['unique_source_count']?.toString() ??
                  copy.text('unknownValue'),
            ),
            _line(
              copy.text('publicationKnown'),
              statistics['publication_time_known_count']?.toString() ??
                  copy.text('unknownValue'),
            ),
            _line(
              copy.text('publicationUnknown'),
              statistics['publication_time_unknown_count']?.toString() ??
                  copy.text('unknownValue'),
            ),
            if (statistics['platform_counts'] case final Map counts)
              for (final entry in counts.entries)
                _line(entry.key.toString(), entry.value.toString()),
          ],
          if (_model.statisticsTaskId case final taskId?)
            TextButton.icon(
              onPressed: () => _copy(taskId),
              icon: const Icon(Icons.copy_outlined, size: 16),
              label: Text('${copy.text('statisticsReference')}: $taskId'),
            ),
          const SizedBox(height: 16),
        ],
      ),
    ],
  );

  Widget _sampleMetadata(SourceBriefCopy copy, SourceBriefResult result) {
    final sourceSample = result.sourceSample;
    final analysisSample = result.analysisSample;
    final showAnalysisSample =
        analysisSample != null ||
        result.businessAnalysisState == SourceBriefBusinessAnalysisState.draft;
    String count(int? value) => value?.toString() ?? copy.text('unknownValue');
    String flag(bool? value, {required String yes, required String no}) =>
        value == null ? copy.text('unknownValue') : copy.text(value ? yes : no);

    final queryCounts = [
      '${copy.text('candidateCount')}: ${count(sourceSample?.candidateCount)}',
      '${copy.text('scannedCount')}: ${count(sourceSample?.scannedCount)}',
      '${copy.text('rejectedCount')}: ${count(sourceSample?.rejectedCount)}',
      '${copy.text('returnedCount')}: ${count(sourceSample?.returnedCount)}',
      '${copy.text('withheldCount')}: ${count(sourceSample?.withheldCount)}',
    ].join(' · ');
    final platformCounts = sourceSample?.platformCountsSample;
    final analysisCounts = [
      '${copy.text('availableBriefCount')}: ${count(analysisSample?.availableBriefCount)}',
      '${copy.text('analyzedSourceCount')}: ${count(analysisSample?.analyzedSourceCount)}',
      '${copy.text('omittedSourceCount')}: ${count(analysisSample?.omittedSourceCount)}',
    ].join(' · ');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionTitle(copy.text('sourceQuerySample')),
        const SizedBox(height: 8),
        _line(
          copy.text('returnedVerifiedCount'),
          count(sourceSample?.returnedVerifiedCount),
        ),
        const SizedBox(height: 8),
        _line(copy.text('queryCounts'), queryCounts),
        const SizedBox(height: 8),
        _line(
          copy.text('queryTruncation'),
          flag(sourceSample?.truncated, yes: 'truncatedYes', no: 'truncatedNo'),
        ),
        if (platformCounts != null && platformCounts.isNotEmpty) ...[
          const SizedBox(height: 8),
          _line(
            copy.text('platformCountsSample'),
            platformCounts.entries
                .map((entry) => '${entry.key}: ${entry.value}')
                .join(' · '),
          ),
        ],
        const SizedBox(height: 8),
        _line(
          copy.text('countsBasis'),
          _countsBasisLabel(copy, sourceSample?.countsBasis),
        ),
        if (showAnalysisSample) ...[
          const SizedBox(height: 16),
          _sectionTitle(copy.text('analysisInputSample')),
          const SizedBox(height: 8),
          _line(copy.text('analysisCounts'), analysisCounts),
          const SizedBox(height: 8),
          _line(
            copy.text('selection'),
            _selectionLabel(copy, analysisSample?.selection),
          ),
          const SizedBox(height: 8),
          _line(
            copy.text('analysisBodyTruncation'),
            flag(
              analysisSample?.hasTruncatedBodies,
              yes: 'truncatedYes',
              no: 'truncatedNo',
            ),
          ),
          const SizedBox(height: 8),
          _line(
            copy.text('coverage'),
            _coverageLabel(copy, analysisSample?.coverage),
          ),
        ],
        const SizedBox(height: 12),
        Text(
          copy.text('sampleLimit'),
          style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
        ),
      ],
    );
  }

  String _countsBasisLabel(
    SourceBriefCopy copy,
    String? value,
  ) => switch (value) {
    'returned verified Canonical records only; not coverage or business metrics' =>
      copy.text('countsBasisValue'),
    null => copy.text('unknownValue'),
    _ => value,
  };

  String _selectionLabel(
    SourceBriefCopy copy,
    String? value,
  ) => switch (value) {
    'explicit operator-selected verified sources; task-term window up to 1200 characters each' =>
      copy.text('selectionExplicit'),
    'latest verified nonempty bodies; at most 8, task-term window up to 1200 characters each' =>
      copy.text('selectionLatest'),
    null => copy.text('unknownValue'),
    _ => value,
  };

  String _coverageLabel(SourceBriefCopy copy, String? value) => switch (value) {
    'PARTIAL' => copy.text('coveragePartial'),
    'UNKNOWN' => copy.text('unknownValue'),
    null => copy.text('unknownValue'),
    _ => value,
  };

  String _speechText(
    SourceBriefResult result,
    SourceBriefBusinessAnalysis analysis,
  ) {
    final lines = <String>[];
    final question = result.businessQuestion?.trim();
    if (question != null && question.isNotEmpty) lines.add(question);
    for (final observation in analysis.sourceObservations) {
      if (observation.excerpt.trim().isNotEmpty) lines.add(observation.excerpt);
    }
    for (final interpretation in analysis.interpretations) {
      if (interpretation.text.trim().isNotEmpty) lines.add(interpretation.text);
    }
    for (final action in analysis.proposedActions) {
      lines.addAll([action.action, action.reason, action.check]);
      if (action.pilot case final pilot?) {
        lines.addAll([
          pilot.audience,
          pilot.procedure,
          pilot.measure,
          pilot.continueIf,
          pilot.stopIf,
        ]);
      }
    }
    lines.addAll(analysis.unknowns);
    return lines.where((line) => line.trim().isNotEmpty).join('\n\n');
  }

  Widget _sources(SourceBriefCopy copy, SourceBriefResult result) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Padding(
        padding: const EdgeInsets.symmetric(vertical: 12),
        child: Text(
          copy.text('sources'),
          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
        ),
      ),
      if (result.records.isEmpty) Text(copy.text('noSources')),
      for (final (index, source) in result.records.indexed)
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: DecoratedBox(
            decoration: LumenisTheme.paper(LumenisTheme.of(context), radius: 6),
            child: Material(
              type: MaterialType.transparency,
              child: ExpansionTile(
                key: ValueKey('source-brief/source/${source.sourceId}'),
                tilePadding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 4,
                ),
                childrenPadding: const EdgeInsets.fromLTRB(14, 0, 14, 16),
                leading: Text(
                  '${index + 1}'.padLeft(2, '0'),
                  style: TextStyle(
                    fontSize: 12,
                    color: LumenisTheme.of(context).muted,
                  ),
                ),
                title: Text(
                  source.title ?? copy.text('untitled'),
                  style: const TextStyle(
                    fontSize: 14,
                    height: 1.45,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                subtitle: source.sourceUrl == null
                    ? null
                    : Text(
                        Uri.tryParse(source.sourceUrl!)?.host ??
                            source.sourceUrl!,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 12,
                          color: LumenisTheme.of(context).muted,
                        ),
                      ),
                expandedCrossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _line(
                    copy.text('published'),
                    source.publishedAt ?? copy.text('unknownValue'),
                  ),
                  const SizedBox(height: 10),
                  _line(
                    copy.text('captured'),
                    source.capturedAt ?? copy.text('unknownValue'),
                  ),
                  if (source.sourceUrl != null) ...[
                    const SizedBox(height: 10),
                    _line(copy.text('sourceLink'), source.sourceUrl!),
                  ],
                  const SizedBox(height: 10),
                  _line(copy.text('sourceProof'), source.evidenceRef),
                  const SizedBox(height: 10),
                  TextButton.icon(
                    onPressed: () => showDialog<void>(
                      context: context,
                      barrierDismissible: false,
                      builder: (_) => CollectedCommentsPanel(
                        client: widget.client,
                        domainId: widget.domainId,
                        sourceId: source.sourceId,
                        title: source.title ?? copy.text('untitled'),
                      ),
                    ),
                    icon: const Icon(Icons.forum_outlined),
                    label: Text(switch (Localizations.localeOf(
                      context,
                    ).languageCode) {
                      'en' => 'Comments and replies',
                      'ko' => '댓글 및 답글',
                      _ => '评论与回复',
                    }),
                  ),
                ],
              ),
            ),
          ),
        ),
    ],
  );

  Widget _savedResearchHistory(SourceBriefCopy copy) {
    final state = _model.savedHistoryState;
    final history = _model.savedHistory;
    final palette = LumenisTheme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 28),
        Divider(color: palette.line),
        const SizedBox(height: 18),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _sectionTitle(copy.text('researchHistory')),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              key: const ValueKey('source-brief/research-history/load'),
              onPressed: _model.busy || state == SourceBriefHistoryState.loading
                  ? null
                  : () {
                      _cancelRevealForUserInteraction();
                      _model.loadSavedResearchHistory();
                    },
              icon: Icon(
                state == SourceBriefHistoryState.loading
                    ? Icons.hourglass_top
                    : Icons.refresh,
                size: 18,
              ),
              label: Text(
                state == SourceBriefHistoryState.loading
                    ? copy.text('loadingResearchHistory')
                    : state == SourceBriefHistoryState.loaded
                    ? copy.text('refreshResearchHistory')
                    : copy.text('loadResearchHistory'),
              ),
            ),
          ],
        ),

        if (state == SourceBriefHistoryState.failed) ...[
          const SizedBox(height: 10),
          Semantics(
            liveRegion: true,
            child: Text(
              copy.text(
                _model.savedHistoryErrorKind ==
                        SourceBriefErrorKind.accessDenied
                    ? 'researchHistoryDenied'
                    : 'researchHistoryFailed',
              ),
              style: TextStyle(color: palette.danger),
            ),
          ),
        ],
        if (state == SourceBriefHistoryState.loaded) ...[
          if (!_model.savedHistoryVerificationComplete ||
              (_model.savedHistoryUnverifiedCount ?? 0) > 0) ...[
            const SizedBox(height: 10),
            Text(
              copy.text('researchHistoryIncomplete'),
              style: TextStyle(color: palette.muted, height: 1.5),
            ),
          ],
          if (history.isEmpty) ...[
            const SizedBox(height: 12),
            Text(copy.text('researchHistoryEmpty')),
          ],
          for (final work in history) ...[
            const SizedBox(height: 10),
            Card(
              key: ValueKey('source-brief/research-history/${work.artifactId}'),
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      work.title,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${copy.text('researchVersion')} ${work.version}',
                      style: TextStyle(color: palette.muted, fontSize: 12),
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        OutlinedButton.icon(
                          key: ValueKey(
                            'source-brief/research-history/open/${work.artifactId}',
                          ),
                          onPressed: _model.busy
                              ? null
                              : () {
                                  _cancelRevealForUserInteraction();
                                  _model.reopenSavedResearchVersion(work);
                                },
                          icon: const Icon(Icons.open_in_new, size: 16),
                          label: Text(copy.text('openResearchVersion')),
                        ),
                        if (_isLatestResearchVersion(work))
                          TextButton.icon(
                            key: ValueKey(
                              'source-brief/research-history/revise/${work.artifactId}',
                            ),
                            onPressed: _model.busy
                                ? null
                                : () => _reviseSavedResearch(work, copy),
                            icon: const Icon(Icons.edit_outlined, size: 16),
                            label: Text(copy.text('reviseResearch')),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
          if (_model.openedHistoryWork case final opened?) ...[
            const SizedBox(height: 14),
            Semantics(
              liveRegion: true,
              child: Text(
                '${copy.text('openedResearchVersion')} ${opened.version}',
                style: TextStyle(color: palette.muted),
              ),
            ),
            const SizedBox(height: 6),
            SelectableText(
              opened.markdown,
              key: const ValueKey('source-brief/research-history/opened'),
            ),
          ],
          if (_model.savedHistoryHasMore) ...[
            const SizedBox(height: 8),
            TextButton(
              key: const ValueKey('source-brief/research-history/more'),
              onPressed: _model.busy
                  ? null
                  : () => _model.loadSavedResearchHistory(loadMore: true),
              child: Text(copy.text('moreResearchHistory')),
            ),
          ],
        ],
      ],
    );
  }

  bool _isLatestResearchVersion(SourceBriefSavedWork work) {
    final latest = _model.savedHistory
        .where((item) => item.workId == work.workId)
        .fold<int>(
          0,
          (value, item) => item.version > value ? item.version : value,
        );
    return latest == work.version;
  }

  Widget _sectionTitle(String text) => Text(
    text,
    style: TextStyle(
      color: LumenisTheme.of(context).foreground,
      fontSize: 18,
      fontWeight: FontWeight.w600,
    ),
  );

  Widget _line(String label, String value) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        label,
        style: TextStyle(color: LumenisTheme.of(context).muted, fontSize: 12),
      ),
      const SizedBox(height: 4),
      SelectableText(
        value,
        style: TextStyle(
          color: LumenisTheme.of(context).foreground,
          height: 1.5,
        ),
      ),
    ],
  );
}
