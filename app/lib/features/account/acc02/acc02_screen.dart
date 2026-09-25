import 'package:flutter/material.dart';

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
  late final Acc02ViewModel _viewModel = Acc02ViewModel(
    repository: widget.repository ?? CoreAcc02Repository(client: widget.client),
  );
  final TextEditingController _searchController = TextEditingController();
  String? _selectedId;
  String _query = '';

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
          builder: (context, _) => switch (_viewModel.phase) {
            Acc02LoadPhase.loading => const _LoadingState(),
            Acc02LoadPhase.failed => _FailureState(
              kind: _viewModel.failureKind!,
              onRetry: _viewModel.refresh,
            ),
            Acc02LoadPhase.ready => _buildReady(context, _viewModel.snapshot!),
          },
        ),
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
    final selectionPending = _viewModel.selectingId != null;
    final canContinue = _canContinue(selected);

    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= 1000;
        final inset = constraints.maxWidth < 680 ? 18.0 : 34.0;
        final list = _SubjectList(
          subjects: subjects,
          selectedId: _selectedId,
          searchController: _searchController,
          state: snapshot.subjectState,
          bounded: wide,
          onSelect: (subject) => setState(() => _selectedId = subject.id),
        );
        final detail = _SubjectDetail(
          subject: selected,
          bounded: wide,
          selecting: selectionPending,
          canContinue: canContinue,
          actionError: _viewModel.actionError,
          onConfirm: selected == null || selectionPending
              ? null
              : () => _viewModel.selectSubject(selected),
          onContinue: widget.onContinue == null
              ? null
              : () {
                  if (_canContinue(selected)) {
                    widget.onContinue?.call();
                  }
                },
        );

        return SingleChildScrollView(
          padding: EdgeInsets.fromLTRB(inset, 26, inset, 40),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1320),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _Heading(
                    title: context.lumenisL10n.text('screen.ACC-02'),
                    subtitle: _copy(
                      context,
                      zh: '先选择服务器返回的主体，再确认查看视角。选择只改变当前查看范围，不改变数据归属。',
                      en: 'Choose a Subject returned by the server, then confirm the view lens. Selection changes the view only, never data ownership.',
                      ko: '서버가 반환한 주체를 선택한 뒤 보기 렌즈를 확인합니다. 선택은 보기 범위만 바꾸며 데이터 소유권은 바꾸지 않습니다.',
                    ),
                  ),
                  const SizedBox(height: 20),
                  _ContextBanner(snapshot: snapshot),
                  const SizedBox(height: 16),
                  if (_viewModel.actionError != null) ...[
                    _Notice(
                      icon: Icons.info_outline,
                      color: LumenisTheme.of(context).caution,
                      text: _viewModel.actionError!,
                    ),
                    const SizedBox(height: 12),
                  ],
                  if (wide)
                    SizedBox(
                      height: 540,
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Expanded(flex: 6, child: list),
                          const SizedBox(width: 16),
                          Expanded(flex: 5, child: detail),
                        ],
                      ),
                    )
                  else ...[
                    list,
                    const SizedBox(height: 14),
                    detail,
                  ],
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  bool _canContinue(Acc02Subject? subject) {
    final snapshot = _viewModel.snapshot;
    return widget.onContinue != null &&
        subject != null &&
        _selectedId == subject.id &&
        _viewModel.phase == Acc02LoadPhase.ready &&
        snapshot != null &&
        snapshot.contextState == Acc02ContextState.focused &&
        snapshot.contextDomainId == subject.domainId &&
        snapshot.selectedSubjectId == subject.id &&
        _viewModel.selectingId == null &&
        _viewModel.actionError == null;
  }
}

Acc02Subject? _firstSubject(Iterable<Acc02Subject> subjects, String? id) {
  if (id == null) return null;
  for (final subject in subjects) {
    if (subject.id == id) return subject;
  }
  return null;
}

class _Heading extends StatelessWidget {
  const _Heading({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        title,
        style: Theme.of(context).textTheme.headlineMedium?.copyWith(
          fontWeight: FontWeight.w600,
          letterSpacing: -0.6,
        ),
      ),
      const SizedBox(height: 8),
      Text(
        subtitle,
        style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
      ),
    ],
  );
}

class _ContextBanner extends StatelessWidget {
  const _ContextBanner({required this.snapshot});

  final Acc02Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final title = switch (snapshot.contextState) {
      Acc02ContextState.globalAll => _copy(
        context,
        zh: '全局查看范围',
        en: 'Global view',
        ko: '전체 보기 범위',
      ),
      Acc02ContextState.focused =>
        snapshot.contextName ??
            _copy(context, zh: '已选择查看范围', en: 'Focused view', ko: '집중 보기'),
      Acc02ContextState.unavailable => _copy(
        context,
        zh: '查看范围待确认',
        en: 'View scope unconfirmed',
        ko: '보기 범위 확인 안 됨',
      ),
    };
    final detail = switch (snapshot.contextState) {
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
          Icon(
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
    required this.onSelect,
  });

  final List<Acc02Subject> subjects;
  final String? selectedId;
  final TextEditingController searchController;
  final Acc02SubjectState state;
  final bool bounded;
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
          zh: '这是已确认的空列表，不等同于访问失败。',
          en: 'This is a confirmed empty list, not an access failure.',
          ko: '확인된 빈 목록이며 접근 실패가 아닙니다.',
        ),
      ),
      _ =>
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
                shrinkWrap: !bounded,
                physics: bounded ? null : const NeverScrollableScrollPhysics(),
                itemCount: subjects.length,
                separatorBuilder: (_, _) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final subject = subjects[index];
                  final selected = subject.id == selectedId;
                  return Material(
                    color: Colors.transparent,
                    child: ListTile(
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
                      onTap: () => onSelect(subject),
                    ),
                  );
                },
              ),
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
              Text(
                '${subjects.length}',
                style: TextStyle(color: LumenisTheme.of(context).quiet),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: searchController,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              prefixIcon: const Icon(Icons.search),
              hintText: context.lumenisL10n.text('common.search'),
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
    required this.subject,
    required this.bounded,
    required this.selecting,
    required this.canContinue,
    required this.actionError,
    required this.onConfirm,
    required this.onContinue,
  });

  final Acc02Subject? subject;
  final bool bounded;
  final bool selecting;
  final bool canContinue;
  final String? actionError;
  final VoidCallback? onConfirm;
  final VoidCallback? onContinue;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _copy(
              context,
              zh: '确认当前视角',
              en: 'Confirm the view lens',
              ko: '현재 보기 렌즈 확인',
            ),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 14),
          if (subject == null)
            bounded
                ? Expanded(
                    child: _ListState(
                      icon: Icons.touch_app_outlined,
                      title: _copy(
                        context,
                        zh: '选择一个主体',
                        en: 'Select a Subject',
                        ko: '주체를 선택하세요',
                      ),
                      detail: _copy(
                        context,
                        zh: '选择后再由服务器确认当前查看范围。',
                        en: 'The server confirms the view scope after selection.',
                        ko: '선택 후 서버가 보기 범위를 확인합니다.',
                      ),
                    ),
                  )
                : SizedBox(
                    height: 180,
                    child: _ListState(
                      icon: Icons.touch_app_outlined,
                      title: _copy(
                        context,
                        zh: '选择一个主体',
                        en: 'Select a Subject',
                        ko: '주체를 선택하세요',
                      ),
                      detail: _copy(
                        context,
                        zh: '选择后再由服务器确认当前查看范围。',
                        en: 'The server confirms the view scope after selection.',
                        ko: '선택 후 서버가 보기 범위를 확인합니다.',
                      ),
                    ),
                  )
          else ...[
            Text(
              subject!.name,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            _DetailRow(
              label: _copy(context, zh: '主体类型', en: 'Type', ko: '유형'),
              value: subject!.subjectType,
            ),
            _DetailRow(
              label: _copy(context, zh: '工作领域', en: 'Domain', ko: '업무 영역'),
              value: subject!.domainId,
            ),
            _DetailRow(
              label: _copy(
                context,
                zh: '选择含义',
                en: 'Selection meaning',
                ko: '선택 의미',
              ),
              value: _copy(
                context,
                zh: '只改变查看范围',
                en: 'View only',
                ko: '보기만 변경',
              ),
            ),
            bounded ? const Spacer() : const SizedBox(height: 18),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: selecting ? null : onConfirm,
                icon: selecting
                    ? const SizedBox.square(
                        dimension: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.check_rounded),
                label: Text(
                  _copy(
                    context,
                    zh: '设为当前范围',
                    en: 'Use this view',
                    ko: '이 보기 사용',
                  ),
                ),
              ),
            ),
            if (onContinue != null) ...[
              const SizedBox(height: 8),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  onPressed: canContinue ? onContinue : null,
                  child: Text(context.lumenisL10n.text('acc.continue')),
                ),
              ),
            ],
            const SizedBox(height: 10),
            Text(
              _copy(
                context,
                zh: '只有服务器确认的主体才会出现在这里；本地选择不会自行授予访问权。',
                en: 'Only server-confirmed Subjects appear here; a local selection never grants access.',
                ko: '서버가 확인한 주체만 표시되며 로컬 선택만으로 접근 권한이 부여되지 않습니다.',
              ),
              style: TextStyle(
                color: LumenisTheme.of(context).quiet,
                height: 1.45,
              ),
            ),
            if (actionError != null) ...[
              const SizedBox(height: 9),
              Text(
                actionError!,
                style: TextStyle(color: LumenisTheme.of(context).caution),
              ),
            ],
          ],
        ],
      ),
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
  });

  final IconData icon;
  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(22),
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
        ],
      ),
    ),
  );
}

class _Notice extends StatelessWidget {
  const _Notice({required this.icon, required this.color, required this.text});

  final IconData icon;
  final Color color;
  final String text;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.08),
      border: Border.all(color: color.withValues(alpha: 0.3)),
      borderRadius: BorderRadius.circular(14),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: color, size: 19),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            text,
            style: TextStyle(color: LumenisTheme.of(context).muted),
          ),
        ),
      ],
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
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: LumenisTheme.of(context).line),
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
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
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
                  zh: '没有使用本地或示例主体替代真实列表。',
                  en: 'No local or sample Subject was used as a substitute.',
                  ko: '실제 목록을 대신해 로컬 또는 샘플 주체를 사용하지 않았습니다.',
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
