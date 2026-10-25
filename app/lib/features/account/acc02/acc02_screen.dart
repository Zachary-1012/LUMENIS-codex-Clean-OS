import 'dart:async';

import 'package:flutter/material.dart';

import '../../../core/lumenis_icon.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'acc02_repository.dart';
import 'acc02_snapshot.dart';
import 'acc02_view_model.dart';

class Acc02Screen extends StatefulWidget {
  const Acc02Screen({
    required this.client,
    this.repository,
    this.onContinue,
    super.key,
  });

  final LumenisCoreClient client;
  final Acc02Repository? repository;
  final VoidCallback? onContinue;

  @override
  State<Acc02Screen> createState() => _Acc02ScreenState();
}

class _Acc02ScreenState extends State<Acc02Screen> {
  late final CoreAcc02Repository _coreRepository = CoreAcc02Repository(
    client: widget.client,
  );
  late final Acc02ViewModel _viewModel = Acc02ViewModel(
    repository: widget.repository ?? _coreRepository,
  );
  final TextEditingController _searchController = TextEditingController();
  String? _selectedId;
  String _query = '';
  String _directoryDomain = 'CTH';
  bool _registrationBusy = false;
  String? _registrationMessage;
  Map<String, String> _registrationDraft = {};
  List<Map<String, dynamic>>? _pendingRegistration;

  @override
  void initState() {
    super.initState();
    _searchController.addListener(() {
      if (!mounted) return;
      setState(() => _query = _searchController.text.trim().toLowerCase());
    });
    _viewModel.refresh();
  }

  @override
  void dispose() {
    _searchController.dispose();
    _viewModel.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: LumenisTheme.of(context).canvas,
      child: SafeArea(
        child: AnimatedBuilder(
          animation: _viewModel,
          builder: (context, _) => Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _directoryHeader(),
              const Divider(),
              Expanded(
                child: switch (_viewModel.phase) {
                  Acc02LoadPhase.loading => const _LoadingState(),
                  Acc02LoadPhase.failed => _FailureState(
                    kind: _viewModel.failureKind!,
                    onRetry: _viewModel.refresh,
                  ),
                  Acc02LoadPhase.ready => _buildReady(
                    context,
                    _viewModel.snapshot!,
                  ),
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _directoryHeader() {
    final selectionPending =
        _viewModel.isCandidateNavigationLocked || _registrationBusy;
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 20, 24, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            context.lumenisL10n.text('screen.ACC-02'),
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 16,
            runSpacing: 12,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              DropdownButton<String>(
                key: const ValueKey('acc02-directory-domain'),
                value: _directoryDomain,
                items: [
                  DropdownMenuItem(
                    value: 'CTH',
                    child: Text(
                      _copy(
                        context,
                        zh: '经营主体',
                        en: 'Operating subjects',
                        ko: '운영 주체',
                      ),
                    ),
                  ),
                  DropdownMenuItem(
                    value: 'BMP',
                    child: Text(
                      _copy(context, zh: '品牌', en: 'Brands', ko: '브랜드'),
                    ),
                  ),
                ],
                onChanged: selectionPending
                    ? null
                    : (domain) async {
                        if (domain == null || domain == _directoryDomain) {
                          return;
                        }
                        setState(() {
                          _directoryDomain = domain;
                          _selectedId = null;
                        });
                        _coreRepository.domainId = domain;
                        await _viewModel.refresh();
                      },
              ),
              TextButton.icon(
                key: const ValueKey('acc02-add-subject'),
                onPressed: selectionPending || _pendingRegistration != null
                    ? null
                    : _registerSubject,
                icon: const Icon(Icons.add),
                label: Text(
                  _copy(context, zh: '添加主体', en: 'Add subject', ko: '주체 추가'),
                ),
              ),
              if (_pendingRegistration != null && !_registrationBusy)
                TextButton(
                  key: const ValueKey('acc02-retry-registration'),
                  onPressed: _registerSubject,
                  child: Text(
                    _copy(
                      context,
                      zh: '重新核对登记',
                      en: 'Reconcile registration',
                      ko: '등록 재확인',
                    ),
                  ),
                ),
              if (_registrationBusy)
                const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
            ],
          ),
          if (_registrationMessage != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Semantics(
                liveRegion: true,
                child: Text(_registrationMessage!),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildReady(BuildContext context, Acc02Snapshot snapshot) {
    final subjects = snapshot.subjects
        .where(
          (subject) =>
              _query.isEmpty ||
              subject.name.toLowerCase().contains(_query) ||
              subject.id.toLowerCase().contains(_query),
        )
        .toList(growable: false);
    final selected =
        _firstSubject(subjects, _selectedId) ??
        _firstSubject(snapshot.subjects, _selectedId);
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= 900;
        final inset = constraints.maxWidth < 680 ? 18.0 : 34.0;
        final retryEnabled =
            !_viewModel.isSelectionPending &&
            !_viewModel.isRefreshing &&
            !_registrationBusy;
        final list = _SubjectList(
          subjects: subjects,
          selectedId: _selectedId,
          searchController: _searchController,
          state: snapshot.subjectState,
          bounded: true,
          onRetry: _viewModel.refresh,
          retryEnabled: retryEnabled,
          candidateNavigationEnabled:
              !_viewModel.isCandidateNavigationLocked && !_registrationBusy,
          onSelect: (subject) {
            if (_viewModel.isCandidateNavigationLocked || _registrationBusy) {
              return;
            }
            final previousIndex = subjects.indexWhere(
              (item) => item.id == _selectedId,
            );
            final nextIndex = subjects.indexWhere(
              (item) => item.id == subject.id,
            );
            _transitionDirection =
                previousIndex < 0 || nextIndex >= previousIndex ? 1 : -1;
            setState(() => _selectedId = subject.id);
            if (!wide) {
              unawaited(_openCandidateSheet(context, subjects, subject));
            }
          },
        );
        final detail = _SubjectDetail(
          key: ValueKey<String>('acc02-inspector-${selected?.id ?? 'empty'}'),
          subject: selected,
          viewModel: _viewModel,
          canContinue: _canContinue(selected),
          onRetry: _viewModel.refresh,
          onContinue: widget.onContinue == null
              ? null
              : () {
                  if (_canContinue(selected)) widget.onContinue?.call();
                },
        );
        final reducedMotion = MediaQuery.disableAnimationsOf(context);
        final inspector = AnimatedSwitcher(
          duration: reducedMotion
              ? Duration.zero
              : const Duration(milliseconds: 180),
          switchInCurve: Curves.easeOutCubic,
          switchOutCurve: Curves.easeOutCubic,
          transitionBuilder: (child, animation) {
            if (reducedMotion) return child;
            final isOutgoing = animation.status == AnimationStatus.reverse;
            final direction = _transitionDirection * (isOutgoing ? -1 : 1);
            return FadeTransition(
              opacity: animation,
              child: SlideTransition(
                position:
                    Tween<Offset>(
                      begin: Offset(direction * 0.04, 0),
                      end: Offset.zero,
                    ).animate(
                      CurvedAnimation(
                        parent: animation,
                        curve: Curves.easeOutCubic,
                      ),
                    ),
                child: child,
              ),
            );
          },
          layoutBuilder: (currentChild, previousChildren) => ClipRect(
            child: Stack(
              fit: StackFit.expand,
              children: [
                for (final child in previousChildren)
                  IgnorePointer(
                    ignoring: true,
                    child: ExcludeSemantics(excluding: true, child: child),
                  ),
                ?currentChild,
              ],
            ),
          ),
          child: detail,
        );

        return Padding(
          key: const ValueKey<String>('acc02-page-scroll'),
          padding: EdgeInsets.fromLTRB(inset, 16, inset, 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _ContextBanner(
                snapshot: snapshot,
                onRetry: _viewModel.refresh,
                retryEnabled: retryEnabled,
                selectionPending: _viewModel.isSelectionPending,
                readbackPending: _viewModel.needsReadback,
              ),
              const SizedBox(height: 16),
              Expanded(
                child: wide
                    ? Row(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Expanded(flex: 6, child: list),
                          const SizedBox(width: 24),
                          Expanded(flex: 5, child: inspector),
                        ],
                      )
                    : list,
              ),
            ],
          ),
        );
      },
    );
  }

  int _transitionDirection = 1;

  Future<List<Map<String, dynamic>>?> _registrationForm() async {
    final fields = {
      'name_zh': _copy(context, zh: '中文名称', en: 'Chinese name', ko: '중국어 이름'),
      'name_en': _copy(context, zh: '英文名称', en: 'English name', ko: '영어 이름'),
      'industry': _copy(
        context,
        zh: '行业（可选）',
        en: 'Industry (optional)',
        ko: '업종 (선택)',
      ),
      'keywords': _copy(
        context,
        zh: '相关名称（可选，逗号分隔）',
        en: 'Related names (optional, comma separated)',
        ko: '관련 이름 (선택, 쉼표 구분)',
      ),
    };
    final controllers = {
      for (final key in fields.keys)
        key: TextEditingController(text: _registrationDraft[key] ?? ''),
    };
    DialogRoute<bool>? formRoute;
    try {
      formRoute = DialogRoute<bool>(
        context: context,
        builder: (dialogContext) => StatefulBuilder(
          builder: (dialogContext, update) => AlertDialog(
            title: Text(
              _copy(context, zh: '添加主体', en: 'Add subject', ko: '주체 추가'),
            ),
            content: SizedBox(
              width: 520,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    for (final field in fields.entries)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 16),
                        child: TextField(
                          key: ValueKey('acc02-register-${field.key}'),
                          controller: controllers[field.key],
                          onChanged: (_) => update(() {}),
                          decoration: InputDecoration(labelText: field.value),
                        ),
                      ),
                  ],
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, false),
                child: Text(_copy(context, zh: '取消', en: 'Cancel', ko: '취소')),
              ),
              FilledButton(
                key: const ValueKey('acc02-prepare-registration'),
                onPressed:
                    controllers['name_zh']!.text.trim().isEmpty ||
                        controllers['name_en']!.text.trim().isEmpty
                    ? null
                    : () => Navigator.pop(dialogContext, true),
                child: Text(
                  _copy(context, zh: '核对信息', en: 'Review details', ko: '정보 검토'),
                ),
              ),
            ],
          ),
        ),
      );
      final accepted = await Navigator.of(
        context,
        rootNavigator: true,
      ).push(formRoute);
      _registrationDraft = {
        for (final entry in controllers.entries)
          entry.key: entry.value.text.trim(),
      };
      if (accepted != true) return null;
      return [
        {
          'baseline_id': 'directory_${DateTime.now().microsecondsSinceEpoch}',
          'identity': {
            'domain_id': _directoryDomain,
            'subject_type': _directoryDomain == 'CTH' ? 'company' : 'brand',
            'name_zh': _registrationDraft['name_zh'],
            'name_en': _registrationDraft['name_en'],
            'industry': _registrationDraft['industry'],
            'keywords': _registrationDraft['keywords']!
                .split(RegExp('[,，]'))
                .map((term) => term.trim())
                .where((term) => term.isNotEmpty)
                .toList(),
          },
        },
      ];
    } finally {
      void disposeControllers() {
        for (final controller in controllers.values) {
          controller.dispose();
        }
      }

      final completed = formRoute?.completed;
      if (completed != null) {
        unawaited(completed.then((_) => disposeControllers()));
      } else {
        disposeControllers();
      }
    }
  }

  Future<void> _registerSubject() async {
    if (_registrationBusy || _viewModel.isCandidateNavigationLocked) return;
    final entries = _pendingRegistration ?? await _registrationForm();
    if (entries == null || !mounted) return;
    setState(() {
      _registrationBusy = true;
      _registrationMessage = null;
      _pendingRegistration = entries;
    });
    try {
      final prepared = await widget.client.subjectBatch(entries: entries);
      if (!mounted) return;
      if (prepared['ok'] != true ||
          prepared['state'] != 'PREPARED' ||
          prepared['resource'] is! String ||
          prepared['entries'] is! List) {
        throw const FormatException('Invalid subject registration preview');
      }
      final normalized = (prepared['entries'] as List)
          .map((entry) => Map<String, dynamic>.from(entry as Map))
          .toList();
      _pendingRegistration = normalized;
      final identity = Map<String, dynamic>.from(
        normalized.single['identity'] as Map,
      );
      final confirm = await showDialog<bool>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: Text(
            _copy(
              context,
              zh: '确认登记并选择',
              en: 'Register and select',
              ko: '등록 및 선택',
            ),
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('${identity['name_zh']}'),
              Text('${identity['name_en']}'),
              if ((identity['industry'] as String? ?? '').isNotEmpty)
                Text('${identity['industry']}'),
              const SizedBox(height: 16),
              Text(
                _copy(
                  context,
                  zh: '仅添加目录身份，不采集资料，也不改变已有事实或作品。',
                  en: 'Adds a directory identity. No collection starts and existing facts and work stay intact.',
                  ko: '디렉터리 신원만 추가합니다. 수집을 시작하거나 기존 사실 및 작업을 변경하지 않습니다.',
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: Text(_copy(context, zh: '取消', en: 'Cancel', ko: '취소')),
            ),
            FilledButton(
              key: const ValueKey('acc02-confirm-registration'),
              onPressed: () => Navigator.pop(dialogContext, true),
              child: Text(
                _copy(
                  context,
                  zh: '登记并选择',
                  en: 'Register and select',
                  ko: '등록 및 선택',
                ),
              ),
            ),
          ],
        ),
      );
      if (confirm != true || !mounted) {
        if (mounted) _pendingRegistration = null;
        return;
      }
      final applied = await widget.client.subjectBatch(
        entries: normalized,
        mode: 'apply',
        confirmedResource: prepared['resource'] as String,
      );
      if (!mounted) return;
      final results = applied['results'];
      if (applied['ok'] != true ||
          applied['state'] != 'COMPLETED' ||
          results is! List ||
          results.length != 1) {
        throw const FormatException(
          'Subject registration needs reconciliation',
        );
      }
      final row = Map<String, dynamic>.from(results.single as Map);
      if (!const {'CREATED', 'EXISTING'}.contains(row['status']) ||
          row['subject'] is! Map) {
        throw const FormatException('Subject registration not confirmed');
      }
      final registered = Acc02Subject.fromJson(
        Map<String, dynamic>.from(row['subject'] as Map),
      );
      _coreRepository.domainId = registered.domainId;
      _directoryDomain = registered.domainId;
      await _viewModel.refresh();
      if (!mounted) return;
      final verified = _firstSubject(
        _viewModel.snapshot?.subjects ?? const [],
        registered.id,
      );
      if (verified == null) {
        throw const FormatException(
          'Subject registration readback unavailable',
        );
      }
      _selectedId = verified.id;
      await _viewModel.selectSubject(verified);
      if (!mounted) return;
      _pendingRegistration = null;
      _registrationDraft = {};
      _registrationMessage = _viewModel.hasMatchingServerContext(verified)
          ? _copy(
              context,
              zh: '已登记并选中。',
              en: 'Registered and selected.',
              ko: '등록 및 선택되었습니다.',
            )
          : _copy(
              context,
              zh: '已登记；选择结果尚待确认，请刷新查看范围。',
              en: 'Registered. Refresh to confirm the selected scope.',
              ko: '등록되었습니다. 선택 범위를 새로고침하여 확인하세요.',
            );
    } on LumenisCoreException catch (error) {
      if (!mounted) return;
      _registrationMessage = error.statusCode == 401 || error.statusCode == 403
          ? _copy(
              context,
              zh: '当前权限不允许登记主体。',
              en: 'Current permissions do not allow registration.',
              ko: '현재 권한으로 등록할 수 없습니다.',
            )
          : _copy(
              context,
              zh: '登记结果尚未确认。请重新核对同一登记，避免重复添加。',
              en: 'Registration is unconfirmed. Reconcile the same entry before adding it again.',
              ko: '등록 결과가 확인되지 않았습니다. 같은 항목을 재확인하세요.',
            );
    } catch (_) {
      if (!mounted) return;
      _registrationMessage = _copy(
        context,
        zh: '登记或读回尚未确认。请重新核对，不覆盖已有主体。',
        en: 'Registration or readback is unconfirmed. Reconcile without replacing an existing subject.',
        ko: '등록 또는 재확인이 완료되지 않았습니다. 기존 주체를 덮어쓰지 말고 재확인하세요.',
      );
    } finally {
      if (mounted) setState(() => _registrationBusy = false);
    }
  }

  Future<void> _openCandidateSheet(
    BuildContext context,
    List<Acc02Subject> candidates,
    Acc02Subject subject,
  ) async {
    final initialPage = candidates.indexWhere((item) => item.id == subject.id);
    if (initialPage < 0) return;
    final continueRequested = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (sheetContext) => FractionallySizedBox(
        heightFactor: 0.94,
        child: _SubjectCandidateSheet(
          candidates: candidates,
          initialPage: initialPage,
          viewModel: _viewModel,
          onCandidateChanged: (candidate) {
            if (mounted) setState(() => _selectedId = candidate.id);
          },
          onContinue: widget.onContinue == null
              ? null
              : () => Navigator.of(sheetContext).pop(true),
        ),
      ),
    );
    if (continueRequested != true || !mounted) return;
    final candidate = _firstSubject(
      _viewModel.snapshot?.subjects ?? const <Acc02Subject>[],
      _selectedId,
    );
    if (_canContinue(candidate)) widget.onContinue?.call();
  }

  bool _canContinue(Acc02Subject? subject) {
    return widget.onContinue != null &&
        subject != null &&
        _selectedId == subject.id &&
        _viewModel.hasMatchingServerContext(subject) &&
        !_viewModel.isSelectionPending &&
        !_viewModel.isRefreshing &&
        !_viewModel.needsReadback &&
        !_registrationBusy &&
        _viewModel.actionErrorFor(subject) == null &&
        switch (_viewModel.confirmationStatusFor(subject)) {
          Acc02ConfirmationStatus.idle ||
          Acc02ConfirmationStatus.confirmed => true,
          Acc02ConfirmationStatus.submitting ||
          Acc02ConfirmationStatus.denied ||
          Acc02ConfirmationStatus.outcomeUnknown ||
          Acc02ConfirmationStatus.readbackUnavailable ||
          Acc02ConfirmationStatus.mismatch => false,
        };
  }
}

Acc02Subject? _firstSubject(Iterable<Acc02Subject> subjects, String? id) {
  if (id == null) return null;
  for (final subject in subjects) {
    if (subject.id == id) return subject;
  }
  return null;
}

class _ContextBanner extends StatelessWidget {
  const _ContextBanner({
    required this.snapshot,
    required this.onRetry,
    required this.retryEnabled,
    required this.selectionPending,
    required this.readbackPending,
  });

  final Acc02Snapshot snapshot;
  final VoidCallback onRetry;
  final bool retryEnabled;
  final bool selectionPending;
  final bool readbackPending;

  @override
  Widget build(BuildContext context) {
    final title = readbackPending
        ? _copy(
            context,
            zh: '查看范围待确认',
            en: 'View scope needs confirmation',
            ko: '보기 범위 확인 필요',
          )
        : selectionPending
        ? _copy(
            context,
            zh: '正在确认查看范围',
            en: 'Confirming view scope',
            ko: '보기 범위 확인 중',
          )
        : switch (snapshot.contextState) {
            Acc02ContextState.globalAll => _copy(
              context,
              zh: '全局查看范围',
              en: 'Global view',
              ko: '전체 보기 범위',
            ),
            Acc02ContextState.focused =>
              snapshot.contextName ??
                  _copy(
                    context,
                    zh: '已选择查看范围',
                    en: 'Focused view',
                    ko: '집중 보기',
                  ),
            Acc02ContextState.unavailable => _copy(
              context,
              zh: '查看范围待确认',
              en: 'View scope unconfirmed',
              ko: '보기 범위 확인 안 됨',
            ),
          };
    final detail = readbackPending
        ? _copy(
            context,
            zh: '变更结果尚未核对。刷新以读取服务器当前范围。',
            en: 'The change outcome has not been checked. Refresh to read the current server scope.',
            ko: '변경 결과를 아직 확인하지 못했습니다. 새로고침하여 서버의 현재 범위를 읽으세요.',
          )
        : selectionPending
        ? _copy(
            context,
            zh: '正在等待服务器返回当前范围。关闭候选层不会取消这次请求。',
            en: 'Waiting for the server to return the current scope. Closing candidates does not cancel the request.',
            ko: '서버가 현재 범위를 반환하기를 기다리고 있습니다. 후보를 닫아도 요청은 취소되지 않습니다.',
          )
        : switch (snapshot.contextState) {
            Acc02ContextState.globalAll => _copy(
              context,
              zh: '全局是查看筛选，不代表所有资料都已收集或都可访问。',
              en: 'Global is a view filter; it does not mean every record is collected or accessible.',
              ko: '전체는 보기 필터일 뿐 모든 기록이 수집되었거나 접근 가능하다는 뜻이 아닙니다.',
            ),
            Acc02ContextState.focused => _copy(
              context,
              zh: '当前服务器已返回一个查看范围。',
              en: 'The server returned a current view scope.',
              ko: '서버가 현재 보기 범위를 반환했습니다.',
            ),
            Acc02ContextState.unavailable => _copy(
              context,
              zh: '没有用本地选择替代服务器确认。',
              en: 'No local selection is used as a substitute for server confirmation.',
              ko: '서버 확인을 대신해 로컬 선택을 사용하지 않습니다.',
            ),
          };
    return _Panel(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          LumenisIcon(
            Icons.tune_rounded,
            color: LumenisTheme.of(context).bmp,
            size: 21,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 4),
                Text(
                  detail,
                  style: TextStyle(color: LumenisTheme.of(context).muted),
                ),
                if (snapshot.contextState == Acc02ContextState.unavailable ||
                    readbackPending) ...[
                  const SizedBox(height: 8),
                  Align(
                    alignment: AlignmentDirectional.centerStart,
                    child: TextButton.icon(
                      onPressed: retryEnabled ? onRetry : null,
                      icon: const Icon(Icons.refresh),
                      label: Text(context.lumenisL10n.text('common.refresh')),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SubjectList extends StatelessWidget {
  const _SubjectList({
    required this.subjects,
    required this.selectedId,
    required this.searchController,
    required this.state,
    required this.bounded,
    required this.onRetry,
    required this.retryEnabled,
    required this.candidateNavigationEnabled,
    required this.onSelect,
  });

  final List<Acc02Subject> subjects;
  final String? selectedId;
  final TextEditingController searchController;
  final Acc02SubjectState state;
  final bool bounded;
  final VoidCallback onRetry;
  final bool retryEnabled;
  final bool candidateNavigationEnabled;
  final ValueChanged<Acc02Subject> onSelect;

  @override
  Widget build(BuildContext context) {
    final body = switch (state) {
      Acc02SubjectState.blocked => _ListState(
        icon: Icons.lock_outline,
        title: _copy(
          context,
          zh: '主体列表暂不可访问',
          en: 'Subject list is not accessible',
          ko: '주체 목록에 접근할 수 없음',
        ),
        detail: _copy(
          context,
          zh: '服务器尚未确认当前查看权限。',
          en: 'The server has not confirmed the current access.',
          ko: '서버가 현재 접근을 확인하지 않았습니다.',
        ),
        actionLabel: context.lumenisL10n.text('common.refresh'),
        onAction: retryEnabled ? onRetry : null,
      ),
      Acc02SubjectState.unavailable => _ListState(
        icon: Icons.sync_problem_outlined,
        title: _copy(
          context,
          zh: '主体列表暂不可用',
          en: 'Subject list unavailable',
          ko: '주체 목록을 사용할 수 없음',
        ),
        detail: _copy(
          context,
          zh: '请刷新后再读取实际列表。',
          en: 'Refresh to read the actual list again.',
          ko: '새로고침하여 실제 목록을 다시 읽으세요.',
        ),
        actionLabel: context.lumenisL10n.text('common.refresh'),
        onAction: retryEnabled ? onRetry : null,
      ),
      Acc02SubjectState.empty => _ListState(
        icon: Icons.inbox_outlined,
        title: _copy(
          context,
          zh: '当前没有可选择的主体',
          en: 'No Subject is available',
          ko: '선택 가능한 주체 없음',
        ),
        detail: _copy(
          context,
          zh: '添加主体后可在这里管理。',
          en: 'Add a subject to manage it here.',
          ko: '주체를 추가하면 여기에서 관리할 수 있습니다.',
        ),
      ),
      Acc02SubjectState.unknown => _ListState(
        icon: Icons.help_outline,
        title: _copy(
          context,
          zh: '主体列表状态未知',
          en: 'Subject list state is unknown',
          ko: '주체 목록 상태를 알 수 없음',
        ),
        detail: _copy(
          context,
          zh: '刷新后重新读取服务器返回的列表。',
          en: 'Refresh to read the list returned by the server again.',
          ko: '새로고침하여 서버가 반환한 목록을 다시 읽으세요.',
        ),
        actionLabel: context.lumenisL10n.text('common.refresh'),
        onAction: retryEnabled ? onRetry : null,
      ),
      Acc02SubjectState.ready =>
        subjects.isEmpty
            ? _ListState(
                icon: Icons.filter_alt_off_outlined,
                title: _copy(
                  context,
                  zh: '没有匹配项',
                  en: 'No matches',
                  ko: '일치 항목 없음',
                ),
                detail: _copy(
                  context,
                  zh: '可以清除搜索条件后重新查看。',
                  en: 'Clear the search to see the returned list again.',
                  ko: '검색을 지우고 반환된 목록을 다시 보세요.',
                ),
              )
            : ListView.separated(
                key: const ValueKey<String>('acc02-subject-list-scroll'),
                primary: false,
                keyboardDismissBehavior:
                    ScrollViewKeyboardDismissBehavior.onDrag,
                itemCount: subjects.length,
                separatorBuilder: (_, _) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final subject = subjects[index];
                  final selected = subject.id == selectedId;
                  return Material(
                    color: Colors.transparent,
                    child: ListTile(
                      key: ValueKey<String>('acc02-subject-${subject.id}'),
                      selected: selected,
                      selectedTileColor: LumenisTheme.of(
                        context,
                      ).bmp.withValues(alpha: 0.09),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 4),
                      leading: Icon(
                        selected
                            ? Icons.radio_button_checked
                            : Icons.radio_button_off,
                        color: selected
                            ? LumenisTheme.of(context).bmp
                            : LumenisTheme.of(context).quiet,
                      ),
                      title: Text(subject.name),
                      subtitle: Text(
                        subject.subjectType,
                        style: TextStyle(color: LumenisTheme.of(context).quiet),
                      ),
                      onTap: candidateNavigationEnabled
                          ? () => onSelect(subject)
                          : null,
                    ),
                  );
                },
              ),
    };
    final count = switch (state) {
      Acc02SubjectState.ready ||
      Acc02SubjectState.empty => '${subjects.length}',
      Acc02SubjectState.blocked ||
      Acc02SubjectState.unavailable ||
      Acc02SubjectState.unknown => null,
    };
    return _Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  _copy(
                    context,
                    zh: '可选择的主体',
                    en: 'Available Subjects',
                    ko: '선택 가능한 주체',
                  ),
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              if (count != null)
                Text(
                  count,
                  style: TextStyle(color: LumenisTheme.of(context).quiet),
                ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            key: const ValueKey<String>('acc02-subject-search-field'),
            controller: searchController,
            enabled:
                state == Acc02SubjectState.ready && candidateNavigationEnabled,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              prefixIcon: const LumenisIcon(Icons.search),
              hintText: context.lumenisL10n.text('common.search'),
              suffixIcon: searchController.text.isEmpty
                  ? null
                  : IconButton(
                      tooltip: _copy(
                        context,
                        zh: '清除搜索',
                        en: 'Clear search',
                        ko: '검색 지우기',
                      ),
                      onPressed: candidateNavigationEnabled
                          ? searchController.clear
                          : null,
                      icon: const LumenisIcon(Icons.clear),
                    ),
              border: const OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          bounded ? Expanded(child: body) : SizedBox(height: 300, child: body),
        ],
      ),
    );
  }
}

class _SubjectDetail extends StatelessWidget {
  const _SubjectDetail({
    super.key,
    required this.subject,
    required this.viewModel,
    required this.canContinue,
    required this.onRetry,
    required this.onContinue,
  });

  final Acc02Subject? subject;
  final Acc02ViewModel viewModel;
  final bool canContinue;
  final VoidCallback onRetry;
  final VoidCallback? onContinue;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _copy(context, zh: '当前主体', en: 'Current Subject', ko: '현재 주체'),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Expanded(
            child: SingleChildScrollView(
              primary: false,
              child: subject == null
                  ? Padding(
                      padding: const EdgeInsets.only(top: 20),
                      child: Text(
                        _copy(
                          context,
                          zh: '选择一个主体',
                          en: 'Select a subject',
                          ko: '주체를 선택하세요',
                        ),
                        style: TextStyle(
                          color: LumenisTheme.of(context).muted,
                          height: 1.45,
                        ),
                      ),
                    )
                  : _CandidateDetails(subject: subject!),
            ),
          ),
          if (subject != null) ...[
            const Divider(height: 20),
            _CandidateActions(
              subject: subject!,
              viewModel: viewModel,
              canContinue: canContinue,
              onRetry: onRetry,
              onContinue: onContinue,
            ),
          ],
        ],
      ),
    );
  }
}

class _SubjectCandidateSheet extends StatefulWidget {
  const _SubjectCandidateSheet({
    required this.candidates,
    required this.initialPage,
    required this.viewModel,
    required this.onCandidateChanged,
    required this.onContinue,
  });

  final List<Acc02Subject> candidates;
  final int initialPage;
  final Acc02ViewModel viewModel;
  final ValueChanged<Acc02Subject> onCandidateChanged;
  final VoidCallback? onContinue;

  @override
  State<_SubjectCandidateSheet> createState() => _SubjectCandidateSheetState();
}

class _SubjectCandidateSheetState extends State<_SubjectCandidateSheet> {
  late final PageController _pageController = PageController(
    initialPage: widget.initialPage,
  );
  late int _page = widget.initialPage;

  Acc02Subject get _subject => widget.candidates[_page];

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _changePage(int nextPage, {required bool reducedMotion}) {
    if (widget.viewModel.isCandidateNavigationLocked ||
        nextPage < 0 ||
        nextPage >= widget.candidates.length) {
      return;
    }
    if (reducedMotion) {
      _pageController.jumpToPage(nextPage);
    } else {
      unawaited(
        _pageController.animateToPage(
          nextPage,
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
        ),
      );
    }
  }

  void _onPageChanged(int page) {
    setState(() => _page = page);
    widget.onCandidateChanged(_subject);
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: widget.viewModel,
    builder: (context, _) {
      final reducedMotion = MediaQuery.disableAnimationsOf(context);
      final navigationLocked = widget.viewModel.isCandidateNavigationLocked;
      final candidateCount = widget.candidates.length;
      return Material(
        color: LumenisTheme.of(context).surface,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
              child: Column(
                children: [
                  Row(
                    children: [
                      IconButton(
                        key: const ValueKey<String>('acc02-close-candidates'),
                        tooltip: _copy(
                          context,
                          zh: '关闭候选层',
                          en: 'Close candidates',
                          ko: '후보 닫기',
                        ),
                        onPressed: () => Navigator.of(context).pop(),
                        icon: const LumenisIcon(Icons.close),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _copy(
                            context,
                            zh: '确认主体范围',
                            en: 'Confirm Subject scope',
                            ko: '주체 범위 확인',
                          ),
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                      ),
                    ],
                  ),
                  Wrap(
                    alignment: WrapAlignment.center,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    spacing: 4,
                    runSpacing: 2,
                    children: [
                      TextButton.icon(
                        key: const ValueKey<String>('acc02-previous-candidate'),
                        onPressed: !navigationLocked && _page > 0
                            ? () => _changePage(
                                _page - 1,
                                reducedMotion: reducedMotion,
                              )
                            : null,
                        icon: const LumenisIcon(Icons.chevron_left),
                        label: Text(
                          _copy(context, zh: '上一个', en: 'Previous', ko: '이전'),
                        ),
                      ),
                      Semantics(
                        liveRegion: true,
                        label: _copy(
                          context,
                          zh: '候选 ${_page + 1} / $candidateCount',
                          en: 'Candidate ${_page + 1} of $candidateCount',
                          ko: '후보 ${_page + 1} / $candidateCount',
                        ),
                        child: Text(
                          _copy(
                            context,
                            zh: '候选 ${_page + 1} / $candidateCount',
                            en: 'Candidate ${_page + 1} of $candidateCount',
                            ko: '후보 ${_page + 1} / $candidateCount',
                          ),
                        ),
                      ),
                      TextButton.icon(
                        key: const ValueKey<String>('acc02-next-candidate'),
                        onPressed:
                            !navigationLocked && _page < candidateCount - 1
                            ? () => _changePage(
                                _page + 1,
                                reducedMotion: reducedMotion,
                              )
                            : null,
                        icon: const LumenisIcon(Icons.chevron_right),
                        label: Text(
                          _copy(context, zh: '下一个', en: 'Next', ko: '다음'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const Divider(height: 1),
            Expanded(
              child: PageView.builder(
                key: const ValueKey<String>('acc02-candidate-page-view'),
                controller: _pageController,
                physics: navigationLocked || reducedMotion
                    ? const NeverScrollableScrollPhysics()
                    : const PageScrollPhysics(),
                itemCount: candidateCount,
                onPageChanged: _onPageChanged,
                itemBuilder: (context, index) => SingleChildScrollView(
                  key: ValueKey<String>(
                    'acc02-candidate-details-${widget.candidates[index].id}',
                  ),
                  primary: false,
                  padding: const EdgeInsets.fromLTRB(24, 24, 24, 32),
                  child: _CandidateDetails(subject: widget.candidates[index]),
                ),
              ),
            ),
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
              child: _CandidateActions(
                subject: _subject,
                viewModel: widget.viewModel,
                canContinue: _canContinueCurrent,
                onRetry: widget.viewModel.refresh,
                onContinue: widget.onContinue,
              ),
            ),
          ],
        ),
      );
    },
  );

  bool get _canContinueCurrent {
    final status = widget.viewModel.confirmationStatusFor(_subject);
    return widget.onContinue != null &&
        widget.viewModel.hasMatchingServerContext(_subject) &&
        !widget.viewModel.isSelectionPending &&
        !widget.viewModel.isRefreshing &&
        !widget.viewModel.needsReadback &&
        widget.viewModel.actionErrorFor(_subject) == null &&
        (status == Acc02ConfirmationStatus.idle ||
            status == Acc02ConfirmationStatus.confirmed);
  }
}

class _CandidateDetails extends StatelessWidget {
  const _CandidateDetails({required this.subject});

  final Acc02Subject subject;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(subject.name, style: Theme.of(context).textTheme.headlineSmall),
      const SizedBox(height: 12),
      _DetailRow(
        label: _copy(context, zh: '主体类型', en: 'Type', ko: '유형'),
        value: subject.subjectType,
      ),
      _DetailRow(
        label: _copy(context, zh: '工作领域', en: 'Domain', ko: '업무 영역'),
        value: subject.domainId,
      ),
      _DetailRow(
        label: _copy(context, zh: '选择含义', en: 'Selection meaning', ko: '선택 의미'),
        value: _copy(context, zh: '只改变查看范围', en: 'View only', ko: '보기만 변경'),
      ),
      const SizedBox(height: 18),
      Text(
        _copy(
          context,
          zh: '当前页只是候选。服务器确认前，不会改变已授权的查看范围。',
          en: 'This page is a candidate only. The authorized view changes only after server confirmation.',
          ko: '현재 페이지는 후보입니다. 서버 확인 전에는 승인된 보기 범위가 바뀌지 않습니다.',
        ),
        style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.45),
      ),
    ],
  );
}

class _CandidateActions extends StatelessWidget {
  const _CandidateActions({
    required this.subject,
    required this.viewModel,
    required this.canContinue,
    required this.onRetry,
    required this.onContinue,
  });

  final Acc02Subject subject;
  final Acc02ViewModel viewModel;
  final bool canContinue;
  final VoidCallback onRetry;
  final VoidCallback? onContinue;

  @override
  Widget build(BuildContext context) {
    final status = viewModel.confirmationStatusFor(subject);
    final pending = viewModel.selectingId == subject.id;
    final current = viewModel.hasMatchingServerContext(subject);
    final actionError = viewModel.actionErrorFor(subject);
    final canConfirm = viewModel.canConfirm(subject);
    final confirmLabel = switch (status) {
      Acc02ConfirmationStatus.submitting => _copy(
        context,
        zh: '正在请求服务器确认',
        en: 'Waiting for server confirmation',
        ko: '서버 확인 대기 중',
      ),
      Acc02ConfirmationStatus.confirmed => _copy(
        context,
        zh: '服务器已确认',
        en: 'Confirmed by server',
        ko: '서버 확인 완료',
      ),
      Acc02ConfirmationStatus.denied || Acc02ConfirmationStatus.mismatch =>
        _copy(context, zh: '重试确认', en: 'Try confirmation again', ko: '확인 재시도'),
      Acc02ConfirmationStatus.outcomeUnknown ||
      Acc02ConfirmationStatus.readbackUnavailable => _copy(
        context,
        zh: '先刷新核对',
        en: 'Refresh to check first',
        ko: '먼저 새로고침하여 확인',
      ),
      Acc02ConfirmationStatus.idle =>
        current
            ? _copy(
                context,
                zh: '服务器已确认',
                en: 'Confirmed by server',
                ko: '서버 확인 완료',
              )
            : _copy(context, zh: '设为当前范围', en: 'Use this view', ko: '이 보기 사용'),
    };
    final canRefresh =
        viewModel.needsReadback &&
        !viewModel.isSelectionPending &&
        !viewModel.isRefreshing;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (actionError != null) ...[
          Text(
            actionError,
            style: TextStyle(color: LumenisTheme.of(context).caution),
          ),
          const SizedBox(height: 8),
        ],
        if (viewModel.needsReadback) ...[
          Align(
            alignment: AlignmentDirectional.centerStart,
            child: TextButton.icon(
              onPressed: canRefresh ? onRetry : null,
              icon: const Icon(Icons.refresh),
              label: Text(context.lumenisL10n.text('common.refresh')),
            ),
          ),
          const SizedBox(height: 4),
        ],
        Wrap(
          alignment: WrapAlignment.end,
          spacing: 8,
          runSpacing: 4,
          children: [
            FilledButton.icon(
              key: const ValueKey<String>('acc02-confirm-candidate'),
              onPressed: canConfirm
                  ? () => viewModel.selectSubject(subject)
                  : null,
              icon: pending
                  ? const SizedBox.square(
                      dimension: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const LumenisIcon(Icons.check_rounded),
              label: Text(confirmLabel),
            ),
            if (onContinue != null)
              OutlinedButton(
                key: const ValueKey<String>('acc02-continue-current'),
                onPressed: canContinue ? onContinue : null,
                child: Text(context.lumenisL10n.text('acc.continue')),
              ),
          ],
        ),
      ],
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 12),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 105,
          child: Text(
            label,
            style: TextStyle(color: LumenisTheme.of(context).quiet),
          ),
        ),
        Expanded(child: Text(value)),
      ],
    ),
  );
}

class _ListState extends StatelessWidget {
  const _ListState({
    required this.icon,
    required this.title,
    required this.detail,
    this.actionLabel,
    this.onAction,
  });

  final IconData icon;
  final String title;
  final String detail;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) => SingleChildScrollView(
      primary: false,
      child: ConstrainedBox(
        constraints: BoxConstraints(minHeight: constraints.maxHeight),
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(icon, color: LumenisTheme.of(context).quiet, size: 28),
                const SizedBox(height: 12),
                Text(
                  title,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 6),
                Text(
                  detail,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: LumenisTheme.of(context).muted,
                    height: 1.45,
                  ),
                ),
                if (actionLabel != null) ...[
                  const SizedBox(height: 10),
                  OutlinedButton.icon(
                    onPressed: onAction,
                    icon: const Icon(Icons.refresh),
                    label: Text(actionLabel!),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    ),
  );
}

class _Panel extends StatelessWidget {
  const _Panel({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(18),
    decoration: ShapeDecoration(
      color: LumenisTheme.of(context).surface,
      shape: LumenisPixelBorder(
        step: 3,
        side: BorderSide(color: LumenisTheme.of(context).line),
      ),
    ),
    child: child,
  );
}

class _LoadingState extends StatelessWidget {
  const _LoadingState();
  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: EdgeInsets.all(32),
      child: CircularProgressIndicator(color: LumenisTheme.of(context).bmp),
    ),
  );
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.kind, required this.onRetry});
  final Acc02FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final title = switch (kind) {
      Acc02FailureKind.authentication => _copy(
        context,
        zh: '访问身份未确认',
        en: 'Access identity unconfirmed',
        ko: '접근 신원 확인 안 됨',
      ),
      Acc02FailureKind.permissionDenied => _copy(
        context,
        zh: '主体范围未获确认',
        en: 'Subject scope not confirmed',
        ko: '주체 범위 확인 안 됨',
      ),
      Acc02FailureKind.offline => _copy(
        context,
        zh: '主体目录暂时离线',
        en: 'Subject directory is offline',
        ko: '주체 디렉터리 오프라인',
      ),
      Acc02FailureKind.server => _copy(
        context,
        zh: '主体目录暂不可用',
        en: 'Subject directory unavailable',
        ko: '주체 디렉터리 사용 불가',
      ),
    };
    return LayoutBuilder(
      builder: (context, constraints) => SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: BoxConstraints(minHeight: constraints.maxHeight),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 560),
              child: _Panel(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 8),
                    Text(
                      _copy(
                        context,
                        zh: switch (kind) {
                          Acc02FailureKind.authentication =>
                            '暂时无法确认当前访问身份，请重试。',
                          Acc02FailureKind.permissionDenied =>
                            '服务器未确认当前主体范围，请检查权限后重试。',
                          Acc02FailureKind.offline => '暂时无法连接，恢复连接后可重试。',
                          Acc02FailureKind.server => '暂时无法读取可查看的范围，请重试。',
                        },
                        en: switch (kind) {
                          Acc02FailureKind.authentication =>
                            'We could not confirm access right now. Please try again.',
                          Acc02FailureKind.permissionDenied =>
                            'The server did not confirm this Subject scope. Check access and try again.',
                          Acc02FailureKind.offline =>
                            'The connection is unavailable. Try again when it returns.',
                          Acc02FailureKind.server =>
                            'We could not read your available scope right now. Please try again.',
                        },
                        ko: switch (kind) {
                          Acc02FailureKind.authentication =>
                            '현재 접근 신원을 확인할 수 없습니다. 다시 시도하세요.',
                          Acc02FailureKind.permissionDenied =>
                            '서버가 이 주체 범위를 확인하지 않았습니다. 접근 권한을 확인하고 다시 시도하세요.',
                          Acc02FailureKind.offline =>
                            '연결할 수 없습니다. 연결이 복구된 뒤 다시 시도하세요.',
                          Acc02FailureKind.server =>
                            '현재 볼 수 있는 범위를 읽을 수 없습니다. 다시 시도하세요.',
                        },
                      ),
                      style: TextStyle(color: LumenisTheme.of(context).muted),
                    ),
                    const SizedBox(height: 16),
                    FilledButton.icon(
                      onPressed: onRetry,
                      icon: const Icon(Icons.refresh),
                      label: Text(context.lumenisL10n.text('common.refresh')),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

String _copy(
  BuildContext context, {
  required String zh,
  required String en,
  required String ko,
}) => switch (context.lumenisL10n.locale.languageCode) {
  'en' => en,
  'ko' => ko,
  _ => zh,
};
