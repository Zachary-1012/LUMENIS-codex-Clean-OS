import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import '../../../core/lumenis_botanical.dart';
import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_icon.dart';
import '../../../core/lumenis_theme.dart';
import 'sys05_appearance_controller.dart';
import 'sys05_appearance_editor.dart';
import 'sys05_repository.dart';

class Sys05Screen extends StatefulWidget {
  const Sys05Screen({
    required this.client,
    this.repository,
    this.accountRepository,
    this.onOpenSubjects,
    this.onNavigate,
    super.key,
  });
  final LumenisCoreClient client;
  final Sys05Repository? repository;
  final Sys05AccountSettingsRepository? accountRepository;
  final VoidCallback? onOpenSubjects;
  final ValueChanged<String>? onNavigate;
  @override
  State<Sys05Screen> createState() => _Sys05ScreenState();
}

class _Sys05ScreenState extends State<Sys05Screen> with RestorationMixin {
  final _selection = RestorableInt(0);
  final _detail = RestorableBool(false);
  final _name = TextEditingController();
  Sys05AppearanceController? _localAppearance;
  Sys05AccountSettings? _account;
  bool _loading = false, _busy = false, _failed = false, _edited = false;
  String? _feedback;
  int _generation = 0;
  static const _names = [
    ['通用', 'General', '일반'],
    ['账号', 'Account', '계정'],
    ['安全', 'Security', '보안'],
    ['模型与 API', 'Models & API', '모델 및 API'],
    ['连接器', 'Connections', '연결'],
    ['用量', 'Usage', '사용량'],
    ['数据控制', 'Data controls', '데이터 관리'],
    ['开发者', 'Developer', '개발자'],
    ['关于', 'About', '정보'],
  ];
  static const _icons = [
    Icons.tune_rounded,
    Icons.person_outline_rounded,
    Icons.shield_outlined,
    Icons.auto_awesome_outlined,
    Icons.extension_outlined,
    Icons.bar_chart_rounded,
    Icons.storage_outlined,
    Icons.code_rounded,
    Icons.info_outline_rounded,
  ];
  String c(String zh, String en, String ko) =>
      switch (Localizations.localeOf(context).languageCode) {
        'en' => en,
        'ko' => ko,
        _ => zh,
      };
  String title(int i) => c(_names[i][0], _names[i][1], _names[i][2]);
  int get selected => _selection.value.clamp(0, _names.length - 1);
  @override
  String get restorationId => 'sys05-settings';
  @override
  void restoreState(RestorationBucket? oldBucket, bool initialRestore) {
    registerForRestoration(_selection, 'section');
    registerForRestoration(_detail, 'detail');
  }

  @override
  void initState() {
    super.initState();
    _read();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (Sys05AppearanceScope.maybeOf(context) == null &&
        _localAppearance == null) {
      _localAppearance = Sys05AppearanceController()..restore();
    }
  }

  @override
  void didUpdateWidget(covariant Sys05Screen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.client != widget.client ||
        oldWidget.accountRepository != widget.accountRepository) {
      _generation++;
      _account = null;
      _busy = false;
      _feedback = null;
      _edited = false;
      _name.clear();
      _read();
    }
  }

  Future<void> _read() async {
    final repo = widget.accountRepository;
    if (repo == null) return;
    final generation = ++_generation;
    setState(() {
      _loading = true;
      _failed = false;
    });
    try {
      final account = await repo.read();
      if (!mounted || generation != _generation) return;
      setState(() {
        _account = account;
        if (!_edited) _name.text = account.displayName ?? '';
      });
    } catch (_) {
      if (mounted && generation == _generation) {
        setState(() {
          _failed = true;
        });
      }
    } finally {
      if (mounted && generation == _generation) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  bool can(Sys05AccountAction action) =>
      !_busy &&
      !_loading &&
      !_failed &&
      widget.accountRepository != null &&
      (_account?.allowedActions.contains(action) ?? false);
  Future<void> perform(Sys05SettingsRequest request) async {
    if (!can(request.action)) return;
    final repo = widget.accountRepository!;
    final client = widget.client;
    final generation = ++_generation;
    setState(() {
      _busy = true;
      _feedback = null;
    });
    try {
      final receipt = await repo.perform(request);
      final account = await repo.read();
      if (!mounted || generation != _generation) return;
      if (request.action == Sys05AccountAction.editProfile) _edited = false;
      setState(() {
        _account = account;
        if (!_edited) _name.text = account.displayName ?? '';
        _feedback = receipt.pending
            ? c('请求已提交', 'Request submitted', '요청 제출됨')
            : c('操作已完成', 'Action completed', '작업 완료');
      });
    } catch (_) {
      if (mounted && generation == _generation) {
        setState(() {
          _feedback = c(
            '未能确认结果，请刷新后查看。',
            'The result could not be confirmed. Refresh to check.',
            '결과를 확인하지 못했습니다. 새로 고침하세요.',
          );
          _failed = true;
        });
      }
    } finally {
      if (mounted &&
          identical(repo, widget.accountRepository) &&
          identical(client, widget.client)) {
        setState(() {
          _busy = false;
        });
      }
    }
  }

  Future<void> confirm(
    Sys05AccountAction action,
    String label,
    String detail, {
    bool requireEmail = false,
  }) async {
    if (!can(action)) return;
    final email = _account?.email;
    final repo = widget.accountRepository;
    if (requireEmail && (email == null || email.isEmpty)) return;
    final input = TextEditingController();
    final accepted = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, update) => AlertDialog(
          title: Text(label),
          content: SizedBox(
            width: 400,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(detail),
                if (requireEmail) ...[
                  const SizedBox(height: 24),
                  Text(email!),
                  const SizedBox(height: 8),
                  TextField(
                    autofocus: true,
                    controller: input,
                    onChanged: (_) => update(() {}),
                    decoration: InputDecoration(
                      labelText: c(
                        '输入邮箱确认',
                        'Type your email to confirm',
                        '확인하려면 이메일을 입력하세요',
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: Text(c('取消', 'Cancel', '취소')),
            ),
            FilledButton(
              onPressed:
                  !requireEmail ||
                      input.text.trim().toLowerCase() == email?.toLowerCase()
                  ? () => Navigator.pop(context, true)
                  : null,
              child: Text(label),
            ),
          ],
        ),
      ),
    );
    input.dispose();
    if (!mounted ||
        accepted != true ||
        !can(action) ||
        !identical(repo, widget.accountRepository) ||
        _account?.email != email) {
      return;
    }
    await perform(
      Sys05SettingsRequest(action, value: requireEmail ? email : null),
    );
  }

  Widget action(String label, Sys05AccountAction value, {String? reference}) =>
      OutlinedButton(
        onPressed: can(value)
            ? () => perform(Sys05SettingsRequest(value, reference: reference))
            : null,
        child: Text(label),
      );
  Widget open(String label, String route) => OutlinedButton.icon(
    onPressed: widget.onNavigate == null
        ? null
        : () => widget.onNavigate!(route),
    icon: const LumenisIcon(Icons.arrow_outward_rounded, size: 18),
    label: Text(label),
  );
  Widget row(
    String label,
    Widget control, {
    String? detail,
    bool danger = false,
  }) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 16),
    child: LayoutBuilder(
      builder: (context, box) {
        final heading = Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: TextStyle(
                fontWeight: FontWeight.w500,
                color: danger ? LumenisTheme.of(context).danger : null,
              ),
            ),
            if (detail != null) ...[
              const SizedBox(height: 4),
              Text(
                detail,
                style: TextStyle(color: LumenisTheme.of(context).muted),
              ),
            ],
          ],
        );
        return box.maxWidth < 440
            ? Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [heading, const SizedBox(height: 12), control],
              )
            : Row(
                children: [
                  Expanded(child: heading),
                  const SizedBox(width: 24),
                  Flexible(
                    child: Align(
                      alignment: Alignment.centerRight,
                      child: control,
                    ),
                  ),
                ],
              );
      },
    ),
  );
  Widget notice() {
    if (_loading) return const LinearProgressIndicator();
    if (_account != null && !_failed) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 24),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const LumenisIcon(Icons.info_outline_rounded, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              c(
                '账号服务暂不可用，已填写的内容会保留。',
                'Account services are unavailable. Your entries are kept here.',
                '계정 서비스를 사용할 수 없습니다. 입력 내용은 유지됩니다.',
              ),
            ),
          ),
          if (widget.accountRepository != null)
            TextButton(
              onPressed: _busy ? null : _read,
              child: Text(c('刷新', 'Refresh', '새로 고침')),
            ),
        ],
      ),
    );
  }

  Widget page(List<Widget> children) => ListView(
    key: PageStorageKey('sys05/$selected'),
    padding: const EdgeInsets.only(bottom: 48),
    children: children,
  );
  Widget content(Sys05AppearanceController appearance) {
    final data = _account;
    switch (selected) {
      case 0:
        return page([
          row(
            c('语言', 'Language', '언어'),
            DropdownButton<String>(
              value: appearance.localeTag,
              onChanged: (value) {
                if (value != null) appearance.update(localeTag: value);
              },
              items: [
                DropdownMenuItem(
                  value: 'system',
                  child: Text(c('跟随系统', 'System default', '시스템 설정')),
                ),
                const DropdownMenuItem(value: 'zh-CN', child: Text('简体中文')),
                const DropdownMenuItem(value: 'en', child: Text('English')),
                const DropdownMenuItem(value: 'ko', child: Text('한국어')),
              ],
            ),
          ),
          const Divider(),
          row(
            c('通知', 'Notifications', '알림'),
            open(c('查看通知', 'View notifications', '알림 보기'), 'SH-06'),
          ),
          const Divider(),
          row(
            c('主体目录', 'Subject directory', '대상 목록'),
            OutlinedButton.icon(
              key: const ValueKey('sys05/open-subject-directory'),
              onPressed: widget.onOpenSubjects,
              icon: const LumenisIcon(Icons.domain_outlined, size: 18),
              label: Text(c('管理主体', 'Manage subjects', '대상 관리')),
            ),
          ),
          const Divider(),
          Sys05AppearanceEditor(controller: appearance, embedded: true),
        ]);
      case 1:
        return page([
          notice(),
          if (data?.signedIn != true) ...[
            row(
              c('登录', 'Sign in', '로그인'),
              open(c('登录或注册', 'Sign in or register', '로그인 또는 가입'), 'ACC-01'),
              detail: data?.signedIn == false
                  ? c('未登录', 'Not signed in', '로그인하지 않음')
                  : null,
            ),
            const Divider(),
          ],
          row(
            c('显示名', 'Display name', '표시 이름'),
            SizedBox(
              width: 300,
              child: TextField(
                controller: _name,
                readOnly: !can(Sys05AccountAction.editProfile),
                onChanged: (_) => setState(() => _edited = true),
                decoration: InputDecoration(
                  hintText: data == null ? '—' : null,
                  suffixIcon: IconButton(
                    tooltip: c('保存', 'Save', '저장'),
                    icon: const LumenisIcon(Icons.check_rounded),
                    onPressed:
                        _edited &&
                            _name.text.trim().isNotEmpty &&
                            can(Sys05AccountAction.editProfile)
                        ? () => perform(
                            Sys05SettingsRequest(
                              Sys05AccountAction.editProfile,
                              value: _name.text.trim(),
                            ),
                          )
                        : null,
                  ),
                ),
              ),
            ),
          ),
          const Divider(),
          row(
            c('邮箱', 'Email', '이메일'),
            action(c('更改', 'Change', '변경'), Sys05AccountAction.changeEmail),
            detail: data?.email ?? '—',
          ),
          const Divider(),
          for (final method in [
            'email',
            'google',
            if (data?.availableLoginMethods.contains('apple') == true ||
                data?.loginMethods.contains('apple') == true)
              'apple',
          ])
            row(
              switch (method) {
                'email' => c('邮箱验证码', 'Email code', '이메일 인증 코드'),
                'google' => 'Google',
                _ => 'Apple',
              },
              action(
                data?.loginMethods.contains(method) == true
                    ? c('解除关联', 'Unlink', '연결 해제')
                    : c('关联', 'Link', '연결'),
                data?.loginMethods.contains(method) == true
                    ? Sys05AccountAction.unlinkIdentity
                    : Sys05AccountAction.linkIdentity,
                reference: method,
              ),
            ),
        ]);
      case 2:
        return page([
          notice(),
          if (data?.signedIn == false)
            row(
              c('未登录', 'Not signed in', '로그인하지 않음'),
              open(c('登录或注册', 'Sign in or register', '로그인 또는 가입'), 'ACC-01'),
            ),
          Text(
            c('设备与会话', 'Devices & sessions', '기기 및 세션'),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 16),
          if (data?.sessions == null)
            Text(c('暂时无法读取设备', 'Devices could not be loaded', '기기를 불러올 수 없습니다'))
          else if (data!.sessions!.isEmpty)
            Text(c('没有其他会话', 'No other sessions', '다른 세션 없음'))
          else
            for (final session in data.sessions!) ...[
              row(
                session.name,
                action(
                  c('退出', 'Sign out', '로그아웃'),
                  Sys05AccountAction.revokeSession,
                  reference: session.id,
                ),
                detail: [
                  if (session.current) c('当前设备', 'This device', '현재 기기'),
                  if (session.location != null) session.location!,
                  if (session.lastActive != null)
                    MaterialLocalizations.of(
                      context,
                    ).formatFullDate(session.lastActive!.toLocal()),
                ].join(' · '),
              ),
              const Divider(),
            ],
          const SizedBox(height: 16),
          row(
            c('新设备登录邮件提醒', 'New-device email alerts', '새 기기 로그인 이메일 알림'),
            data?.newDeviceAlerts == null
                ? const Text('—')
                : Switch(
                    value: data!.newDeviceAlerts!,
                    onChanged: can(Sys05AccountAction.newDeviceAlerts)
                        ? (value) => perform(
                            Sys05SettingsRequest(
                              Sys05AccountAction.newDeviceAlerts,
                              value: value.toString(),
                            ),
                          )
                        : null,
                  ),
          ),
          const Divider(),
          row(
            c('所有设备', 'All devices', '모든 기기'),
            OutlinedButton(
              onPressed: can(Sys05AccountAction.revokeAllSessions)
                  ? () => confirm(
                      Sys05AccountAction.revokeAllSessions,
                      c('退出所有设备', 'Sign out everywhere', '모든 기기 로그아웃'),
                      c(
                        '包括当前设备。已保存的作品会保留。',
                        'Includes this device. Saved work is retained.',
                        '현재 기기도 포함됩니다. 저장한 작업은 유지됩니다.',
                      ),
                    )
                  : null,
              child: Text(c('退出所有设备', 'Sign out everywhere', '모든 기기 로그아웃')),
            ),
          ),
        ]);
      case 3:
        return page([
          const Align(
            alignment: Alignment.centerLeft,
            child: LumenisBotanical(plant: LumenisPlant.jasmine, size: 64),
          ),
          const SizedBox(height: 24),
          row(
            c('我的模型与 API', 'My models & API', '내 모델 및 API'),
            open(c('管理', 'Manage', '관리'), 'AI-05'),
          ),
          const Divider(),
          row(
            c('任务中的 AI', 'AI for your work', '작업용 AI'),
            open(c('查看任务', 'View tasks', '작업 보기'), 'AI-02'),
          ),
        ]);
      case 4:
        return page([
          row(
            c('工具与连接器', 'Tools & connectors', '도구 및 연결'),
            open(c('管理连接器', 'Manage connections', '연결 관리'), 'AI-04'),
          ),
          const Divider(),
          row(
            c('平台登录', 'Platform sign-in', '플랫폼 로그인'),
            open(c('打开浏览器', 'Open browser', '브라우저 열기'), 'SYS-06'),
          ),
        ]);
      case 5:
        return page([
          notice(),
          if (data?.usagePeriod != null) Text(data!.usagePeriod!),
          row(
            c('模型调用', 'Model requests', '모델 요청'),
            Text(
              count(data?.modelCalls),
              style: Theme.of(context).textTheme.headlineMedium,
            ),
          ),
          const Divider(),
          row(
            c('采集任务', 'Collection tasks', '수집 작업'),
            Text(
              count(data?.collectionTasks),
              style: Theme.of(context).textTheme.headlineMedium,
            ),
          ),
          const Divider(),
          row(
            c('存储', 'Storage', '저장 공간'),
            Text(
              storage(data?.storageBytes),
              style: Theme.of(context).textTheme.headlineMedium,
            ),
          ),
          if (data?.modelCalls == null ||
              data?.collectionTasks == null ||
              data?.storageBytes == null)
            Text(
              c(
                '— 表示尚无统计数据',
                '— means no usage data is available',
                '— 표시는 사용량 데이터가 없음을 의미합니다',
              ),
              style: TextStyle(color: LumenisTheme.of(context).muted),
            ),
        ]);
      case 6:
        return page([
          notice(),
          row(
            c(
              '允许使用数据改进模型',
              'Allow data to improve models',
              '모델 개선을 위한 데이터 사용 허용',
            ),
            DropdownButton<bool>(
              value: data?.modelLearning,
              hint: Text(c('尚未选择', 'Not selected', '선택하지 않음')),
              onChanged: can(Sys05AccountAction.modelLearning)
                  ? (value) {
                      if (value != null) {
                        perform(
                          Sys05SettingsRequest(
                            Sys05AccountAction.modelLearning,
                            value: value.toString(),
                          ),
                        );
                      }
                    }
                  : null,
              items: [
                DropdownMenuItem(
                  value: true,
                  child: Text(c('允许', 'Allow', '허용')),
                ),
                DropdownMenuItem(
                  value: false,
                  child: Text(c('不允许', 'Do not allow', '허용하지 않음')),
                ),
              ],
            ),
          ),
          const Divider(),
          row(
            c('导出全部数据', 'Export all data', '모든 데이터 내보내기'),
            action(
              c('请求导出', 'Request export', '내보내기 요청'),
              Sys05AccountAction.exportData,
            ),
          ),
          const Divider(),
          row(
            c('备份', 'Backup', '백업'),
            action(
              c('创建备份', 'Create backup', '백업 만들기'),
              Sys05AccountAction.backupData,
            ),
          ),
          const Divider(),
          row(
            c('恢复', 'Restore', '복원'),
            action(
              c('选择备份', 'Choose backup', '백업 선택'),
              Sys05AccountAction.restoreData,
            ),
          ),
          const Divider(),
          row(
            c('全部对话', 'All conversations', '모든 대화'),
            OutlinedButton(
              onPressed: can(Sys05AccountAction.deleteConversations)
                  ? () => confirm(
                      Sys05AccountAction.deleteConversations,
                      c('删除全部对话', 'Delete all conversations', '모든 대화 삭제'),
                      c(
                        '将删除此账号的对话。独立保存的作品保留。',
                        'Deletes conversations for this account. Independently saved work is retained.',
                        '이 계정의 대화를 삭제합니다. 별도로 저장한 작업은 유지됩니다.',
                      ),
                    )
                  : null,
              child: Text(c('删除', 'Delete', '삭제')),
            ),
            danger: true,
          ),
          const Divider(),
          if (data?.deletionAt != null)
            row(
              c('账号等待删除', 'Account pending deletion', '계정 삭제 예정'),
              action(
                c('撤销删除', 'Undo deletion', '삭제 취소'),
                Sys05AccountAction.restoreAccount,
              ),
              detail: MaterialLocalizations.of(
                context,
              ).formatFullDate(data!.deletionAt!.toLocal()),
              danger: true,
            )
          else
            row(
              c('删除账号', 'Delete account', '계정 삭제'),
              OutlinedButton(
                onPressed:
                    can(Sys05AccountAction.deleteAccount) && data?.email != null
                    ? () => confirm(
                        Sys05AccountAction.deleteAccount,
                        c('申请删除账号', 'Request account deletion', '계정 삭제 요청'),
                        c(
                          '提交后 30 天内可撤销。到期时间由账号服务确认。',
                          'You can undo this within 30 days. The account service confirms the deletion date.',
                          '30일 이내에 취소할 수 있습니다. 계정 서비스에서 삭제 날짜를 확인합니다.',
                        ),
                        requireEmail: true,
                      )
                    : null,
                child: Text(c('删除账号', 'Delete account', '계정 삭제')),
              ),
              danger: true,
            ),
        ]);
      case 7:
        return page([
          row(
            c('用户开发者模式', 'User developer mode', '사용자 개발자 모드'),
            open(c('打开', 'Open', '열기'), 'SYS-04'),
          ),
          const Divider(),
          row(
            c('内部发布', 'Internal releases', '내부 릴리스'),
            open(c('查看', 'View', '보기'), 'SYS-07'),
          ),
        ]);
      default:
        const version = String.fromEnvironment('OEVIRA_BUILD_VERSION');
        return page([
          const Align(
            alignment: Alignment.centerLeft,
            child: LumenisBotanical(size: 72),
          ),
          const SizedBox(height: 24),
          Text(
            'OEVIRA',
            style: Theme.of(
              context,
            ).textTheme.headlineMedium?.copyWith(letterSpacing: 3),
          ),
          const SizedBox(height: 8),
          Text(
            c(
              '寰意',
              'An open space for thought and creation.',
              '생각과 창작을 위한 열린 공간.',
            ),
          ),
          const SizedBox(height: 32),
          row(c('版本', 'Version', '버전'), Text(version.isEmpty ? '—' : version)),
          const Divider(),
          row(
            c('当前应用', 'Application', '앱'),
            Text(kIsWeb ? 'Web' : defaultTargetPlatform.name),
          ),
          const Divider(),
          row(
            c('开源许可', 'Open-source licenses', '오픈소스 라이선스'),
            OutlinedButton(
              onPressed: () =>
                  showLicensePage(context: context, applicationName: 'OEVIRA'),
              child: Text(c('查看', 'View', '보기')),
            ),
          ),
          const Divider(),
          row(
            c('账号', 'Account', '계정'),
            OutlinedButton(
              onPressed: can(Sys05AccountAction.signOut)
                  ? () => confirm(
                      Sys05AccountAction.signOut,
                      c('退出登录', 'Sign out', '로그아웃'),
                      c(
                        '退出当前账号，已保存作品会保留。',
                        'Sign out of this account. Saved work is retained.',
                        '현재 계정에서 로그아웃합니다. 저장한 작업은 유지됩니다.',
                      ),
                    )
                  : null,
              child: Text(c('退出登录', 'Sign out', '로그아웃')),
            ),
          ),
        ]);
    }
  }

  String count(int? value) =>
      value == null || value < 0 ? '—' : value.toString();
  String storage(int? bytes) {
    if (bytes == null || bytes < 0) return '—';
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1048576) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    if (bytes < 1073741824) return '${(bytes / 1048576).toStringAsFixed(1)} MB';
    return '${(bytes / 1073741824).toStringAsFixed(1)} GB';
  }

  @override
  void dispose() {
    _generation++;
    _selection.dispose();
    _detail.dispose();
    _name.dispose();
    _localAppearance?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final appearance =
        Sys05AppearanceScope.maybeOf(context) ?? _localAppearance!;
    final palette = LumenisTheme.of(context);
    return AnimatedBuilder(
      animation: appearance,
      builder: (context, _) => LayoutBuilder(
        builder: (context, box) {
          final wide = box.maxWidth >= 860;
          final menu = ListView(
            padding: const EdgeInsets.symmetric(vertical: 16),
            children: [
              for (var i = 0; i < _names.length; i++)
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 2,
                  ),
                  child: Semantics(
                    selected: selected == i && (wide || _detail.value),
                    child: TextButton(
                      key: ValueKey('sys05/section/$i'),
                      style: TextButton.styleFrom(
                        alignment: Alignment.centerLeft,
                        backgroundColor: wide && selected == i
                            ? palette.surfaceRaised
                            : Colors.transparent,
                        foregroundColor: wide && selected == i
                            ? palette.foreground
                            : palette.muted,
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 14,
                        ),
                      ),
                      onPressed: () => setState(() {
                        _selection.value = i;
                        _detail.value = true;
                        _feedback = null;
                      }),
                      child: Row(
                        children: [
                          LumenisIcon(_icons[i], size: 20),
                          const SizedBox(width: 12),
                          Expanded(child: Text(title(i))),
                          if (!wide)
                            const LumenisIcon(
                              Icons.chevron_right_rounded,
                              size: 18,
                            ),
                        ],
                      ),
                    ),
                  ),
                ),
            ],
          );
          final body = Align(
            alignment: Alignment.topCenter,
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 800),
              child: Padding(
                padding: EdgeInsets.fromLTRB(
                  wide ? 32 : 16,
                  24,
                  wide ? 32 : 16,
                  0,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      children: [
                        if (!wide) ...[
                          IconButton(
                            tooltip: c('返回设置', 'Back to settings', '설정으로 돌아가기'),
                            onPressed: () =>
                                setState(() => _detail.value = false),
                            icon: const LumenisIcon(Icons.arrow_back_rounded),
                          ),
                          const SizedBox(width: 8),
                        ],
                        Expanded(
                          child: Semantics(
                            header: true,
                            child: Text(
                              title(selected),
                              style: Theme.of(context).textTheme.headlineSmall,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    if (_busy) const LinearProgressIndicator(),
                    if (_feedback != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 16),
                        child: Semantics(
                          liveRegion: true,
                          child: Text(_feedback!),
                        ),
                      ),
                    Expanded(
                      child: AnimatedSwitcher(
                        duration: LumenisMotion.of(context, LumenisMotion.exit),
                        layoutBuilder: (current, previous) => Stack(
                          fit: StackFit.expand,
                          children: [
                            for (final old in previous)
                              ExcludeFocus(
                                child: ExcludeSemantics(
                                  child: IgnorePointer(child: old),
                                ),
                              ),
                            ?current,
                          ],
                        ),
                        child: KeyedSubtree(
                          key: ValueKey(selected),
                          child: content(appearance),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
          return SafeArea(
            child: wide
                ? Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      SizedBox(
                        width: 200,
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            color: palette.surface,
                            border: Border(
                              right: BorderSide(color: palette.line),
                            ),
                          ),
                          child: menu,
                        ),
                      ),
                      Expanded(child: body),
                    ],
                  )
                : _detail.value
                ? body
                : menu,
          );
        },
      ),
    );
  }
}
