import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../core/lumenis_botanical.dart';
import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'acc01_repository.dart';

class Acc01Screen extends StatefulWidget {
  const Acc01Screen({
    required this.client,
    this.repository,
    this.identityActions,
    this.onContinue,
    super.key,
  });

  final LumenisCoreClient client;
  final Acc01Repository? repository;
  final Acc01IdentityActions? identityActions;
  final VoidCallback? onContinue;

  @override
  State<Acc01Screen> createState() => _Acc01ScreenState();
}

class _Acc01ScreenState extends State<Acc01Screen> {
  final _email = TextEditingController();
  final _code = TextEditingController();
  final _codeFocus = FocusNode();
  final _emailForm = GlobalKey<FormState>();
  Acc01EmailChallenge? _challenge;
  Acc01IdentityOutcome? _outcome;
  Acc01IdentityFailure? _failure;
  DateTime? _retryAt;
  Timer? _clock;
  bool _busy = false;
  int _request = 0;

  Set<Acc01IdentityMethod> get _methods =>
      widget.identityActions?.availableMethods ?? const {};

  @override
  void didUpdateWidget(Acc01Screen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!identical(oldWidget.client, widget.client) ||
        !identical(oldWidget.identityActions, widget.identityActions)) {
      _resetChallenge(clearEmail: true);
    }
  }

  void _resetChallenge({bool clearEmail = false}) {
    _request++;
    _clock?.cancel();
    _challenge = null;
    _outcome = null;
    _failure = null;
    _retryAt = null;
    _busy = false;
    _code.clear();
    if (clearEmail) _email.clear();
  }

  @override
  void dispose() {
    _request++;
    _clock?.cancel();
    _email.dispose();
    _code.dispose();
    _codeFocus.dispose();
    super.dispose();
  }

  int get _resendSeconds {
    final at = _retryAt ?? _challenge?.resendAt;
    if (at == null) return 0;
    final milliseconds = at.difference(DateTime.now()).inMilliseconds;
    return milliseconds > 0 ? (milliseconds / 1000).ceil() : 0;
  }

  void _tick() {
    _clock?.cancel();
    _clock = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() {});
      if (_resendSeconds == 0 &&
          (_challenge == null ||
              DateTime.now().isAfter(_challenge!.expiresAt))) {
        _clock?.cancel();
      }
    });
  }

  Future<void> _perform(Future<void> Function() operation) async {
    if (_busy || widget.identityActions == null) return;
    final request = ++_request;
    setState(() {
      _busy = true;
      _failure = null;
    });
    try {
      await operation();
    } on Acc01IdentityException catch (error) {
      if (!mounted || request != _request) return;
      _failure = error.failure;
      _retryAt = error.retryAt;
      if (_retryAt != null) _tick();
    } catch (_) {
      if (!mounted || request != _request) return;
      _failure = Acc01IdentityFailure.unavailable;
    } finally {
      if (mounted && request == _request) setState(() => _busy = false);
    }
  }

  Future<void> _requestCode() async {
    if ((_emailForm.currentState?.validate() ??
                RegExp(
                  r'^[^\s@]+@[^\s@]+\.[^\s@]+$',
                ).hasMatch(_email.text.trim())) !=
            true ||
        !_methods.contains(Acc01IdentityMethod.email) ||
        _resendSeconds > 0) {
      return;
    }
    final identity = widget.identityActions!;
    final email = _email.text.trim();
    await _perform(() async {
      final request = _request;
      final challenge = await identity.requestEmail(email);
      if (!mounted || request != _request) return;
      if (challenge.reference.isEmpty ||
          challenge.displayEmail.isEmpty ||
          challenge.codeLength < 4 ||
          challenge.codeLength > 8 ||
          !challenge.expiresAt.isAfter(DateTime.now())) {
        throw const Acc01IdentityException(Acc01IdentityFailure.unavailable);
      }
      _challenge = challenge;
      _retryAt = null;
      _code.clear();
      _tick();
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && request == _request) _codeFocus.requestFocus();
      });
    });
  }

  Future<void> _verifyCode() async {
    final challenge = _challenge;
    if (challenge == null ||
        _code.text.length != challenge.codeLength ||
        widget.identityActions == null) {
      return;
    }
    if (!challenge.expiresAt.isAfter(DateTime.now())) {
      setState(() => _failure = Acc01IdentityFailure.expiredCode);
      return;
    }
    await _perform(() async {
      final request = _request;
      final outcome = await widget.identityActions!.verifyEmail(
        challenge.reference,
        _code.text,
      );
      if (mounted && request == _request) _accept(outcome);
    });
  }

  Future<void> _provider(Acc01IdentityMethod method) async {
    if (!_methods.contains(method)) return;
    await _perform(() async {
      final request = _request;
      final outcome = await widget.identityActions!.signIn(method);
      if (mounted && request == _request) _accept(outcome);
    });
  }

  void _accept(Acc01IdentityOutcome outcome) {
    if (outcome.status == Acc01IdentityStatus.cancelled) return;
    _outcome = outcome;
    if (outcome.status == Acc01IdentityStatus.signedIn) {
      _code.clear();
      _clock?.cancel();
      widget.onContinue?.call();
    }
  }

  Future<void> _continueIdentity() async {
    final outcome = _outcome;
    final continuation = outcome?.continuation;
    final identity = widget.identityActions;
    if (outcome == null || continuation == null || identity == null) return;
    await _perform(() async {
      final request = _request;
      final result = outcome.status == Acc01IdentityStatus.linkRequired
          ? await identity.confirmLink(continuation)
          : await identity.restoreAccount(continuation);
      if (mounted && request == _request) _accept(result);
    });
  }

  String copy(String zh, String en, String ko) =>
      switch (context.lumenisL10n.locale.languageCode) {
        'en' => en,
        'ko' => ko,
        _ => zh,
      };

  String get _failureText => switch (_failure) {
    Acc01IdentityFailure.invalidCode => copy(
      '验证码不正确',
      'The code is incorrect',
      '인증 코드가 올바르지 않습니다',
    ),
    Acc01IdentityFailure.expiredCode => copy(
      '验证码已过期，请重新发送',
      'The code expired. Request a new one.',
      '코드가 만료되었습니다. 다시 요청하세요.',
    ),
    Acc01IdentityFailure.rateLimited => copy(
      '发送太频繁，请稍后再试',
      'Please wait before requesting another code.',
      '잠시 후 코드를 다시 요청하세요.',
    ),
    _ => copy(
      '登录暂不可用，可先不登录继续使用。',
      'Sign-in is unavailable. You can continue without signing in.',
      '지금은 로그인할 수 없습니다. 로그인 없이 계속 사용할 수 있습니다.',
    ),
  };

  @override
  Widget build(BuildContext context) {
    final palette = LumenisTheme.of(context);
    final challenge = _challenge;
    final outcome = _outcome;
    final specialOutcome =
        outcome != null && outcome.status != Acc01IdentityStatus.signedIn;
    return ColoredBox(
      color: palette.canvas,
      child: LayoutBuilder(
        builder: (context, box) => SingleChildScrollView(
          padding: const EdgeInsets.all(LumenisSpace.section),
          child: ConstrainedBox(
            constraints: BoxConstraints(
              minHeight: (box.maxHeight - 48).clamp(0, double.infinity),
            ),
            child: Center(
              child: SizedBox(
                width: 424,
                child: AutofillGroup(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Center(child: LumenisBotanical(size: 72)),
                      const SizedBox(height: LumenisSpace.section),
                      Text(
                        copy(
                          '登录或创建账号',
                          'Sign in or create an account',
                          '로그인 또는 계정 만들기',
                        ),
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: LumenisSpace.section),
                      FilledButton(
                        key: const ValueKey('acc01-continue-without-account'),
                        onPressed: widget.onContinue,
                        child: Text(
                          copy(
                            '先不登录，直接使用',
                            'Continue without signing in',
                            '로그인 없이 시작',
                          ),
                        ),
                      ),
                      const SizedBox(height: LumenisSpace.section),
                      if (specialOutcome)
                        _identityDecision(outcome)
                      else if (challenge != null)
                        _verification(challenge)
                      else ...[
                        OutlinedButton(
                          key: const ValueKey('acc01-google'),
                          onPressed:
                              !_busy &&
                                  _methods.contains(Acc01IdentityMethod.google)
                              ? () => _provider(Acc01IdentityMethod.google)
                              : null,
                          child: Text(
                            copy(
                              '使用 Google 登录',
                              'Continue with Google',
                              'Google로 계속',
                            ),
                          ),
                        ),
                        if (_methods.contains(Acc01IdentityMethod.apple)) ...[
                          const SizedBox(height: LumenisSpace.tight),
                          OutlinedButton(
                            onPressed: _busy
                                ? null
                                : () => _provider(Acc01IdentityMethod.apple),
                            child: Text(
                              copy(
                                '使用 Apple 登录',
                                'Continue with Apple',
                                'Apple로 계속',
                              ),
                            ),
                          ),
                        ],
                        const Padding(
                          padding: EdgeInsets.symmetric(
                            vertical: LumenisSpace.section,
                          ),
                          child: Divider(height: 1),
                        ),
                        Form(
                          key: _emailForm,
                          child: TextFormField(
                            key: const ValueKey('acc01-email'),
                            controller: _email,
                            keyboardType: TextInputType.emailAddress,
                            autofillHints: const [AutofillHints.email],
                            textInputAction: TextInputAction.go,
                            autocorrect: false,
                            enabled: !_busy,
                            decoration: InputDecoration(
                              labelText: copy('邮箱', 'Email', '이메일'),
                              hintText: 'name@example.com',
                            ),
                            validator: (value) {
                              if (RegExp(
                                r'^[^\s@]+@[^\s@]+\.[^\s@]+$',
                              ).hasMatch(value?.trim() ?? '')) {
                                return null;
                              }
                              return copy(
                                '请输入有效邮箱',
                                'Enter a valid email address',
                                '유효한 이메일을 입력하세요',
                              );
                            },
                            onFieldSubmitted: (_) => _requestCode(),
                          ),
                        ),
                        const SizedBox(height: LumenisSpace.inset),
                        OutlinedButton(
                          key: const ValueKey('acc01-request-code'),
                          onPressed:
                              !_busy &&
                                  _resendSeconds == 0 &&
                                  _methods.contains(Acc01IdentityMethod.email)
                              ? _requestCode
                              : null,
                          child: Text(
                            copy('发送验证码', 'Send a code', '인증 코드 보내기'),
                          ),
                        ),
                      ],
                      if (_busy) ...[
                        const SizedBox(height: LumenisSpace.control),
                        const LinearProgressIndicator(),
                        TextButton(
                          onPressed: () => setState(_resetChallenge),
                          child: Text(copy('取消', 'Cancel', '취소')),
                        ),
                      ],
                      if (_failure != null ||
                          widget.identityActions == null) ...[
                        const SizedBox(height: LumenisSpace.control),
                        Semantics(
                          liveRegion: true,
                          child: Text(
                            _failureText,
                            style: Theme.of(context).textTheme.bodySmall
                                ?.copyWith(
                                  color: _failure == null
                                      ? palette.muted
                                      : palette.danger,
                                ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _verification(Acc01EmailChallenge challenge) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Text(
        challenge.displayEmail,
        style: Theme.of(context).textTheme.titleMedium,
      ),
      const SizedBox(height: LumenisSpace.control),
      TextField(
        key: const ValueKey('acc01-verification-code'),
        controller: _code,
        focusNode: _codeFocus,
        keyboardType: TextInputType.number,
        autofillHints: const [AutofillHints.oneTimeCode],
        inputFormatters: [
          FilteringTextInputFormatter.digitsOnly,
          LengthLimitingTextInputFormatter(challenge.codeLength),
        ],
        maxLength: challenge.codeLength,
        style: Theme.of(
          context,
        ).textTheme.headlineMedium?.copyWith(letterSpacing: 12),
        textAlign: TextAlign.center,
        enabled: !_busy,
        decoration: InputDecoration(
          labelText: copy('验证码', 'Verification code', '인증 코드'),
          counterText: '',
        ),
        onChanged: (_) => setState(() => _failure = null),
        onSubmitted: (_) => _verifyCode(),
      ),
      const SizedBox(height: LumenisSpace.control),
      OutlinedButton(
        key: const ValueKey('acc01-verify'),
        onPressed: !_busy && _code.text.length == challenge.codeLength
            ? _verifyCode
            : null,
        child: Text(copy('验证并继续', 'Verify and continue', '인증 후 계속')),
      ),
      const SizedBox(height: LumenisSpace.tight),
      Wrap(
        alignment: WrapAlignment.spaceBetween,
        children: [
          TextButton(
            onPressed: _busy || _resendSeconds > 0 ? null : _requestCode,
            child: Text(
              _resendSeconds > 0
                  ? copy(
                      '重新发送（$_resendSeconds 秒）',
                      'Resend in $_resendSeconds s',
                      '$_resendSeconds초 후 재전송',
                    )
                  : copy('重新发送', 'Resend code', '다시 보내기'),
            ),
          ),
          TextButton(
            onPressed: () => setState(_resetChallenge),
            child: Text(copy('换个邮箱', 'Use another email', '다른 이메일 사용')),
          ),
        ],
      ),
    ],
  );

  Widget _identityDecision(Acc01IdentityOutcome outcome) {
    final linking = outcome.status == Acc01IdentityStatus.linkRequired;
    final date = outcome.deletionAt?.toLocal();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          linking
              ? copy('关联现有账号？', 'Link your existing account?', '기존 계정에 연결할까요?')
              : copy('账号正在等待删除', 'Account deletion is pending', '계정 삭제 대기 중'),
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: LumenisSpace.inset),
        Text(
          linking
              ? copy(
                  '确认后使用已核验的账号继续。',
                  'Continue with your verified account after confirming.',
                  '확인 후 인증된 계정으로 계속합니다.',
                )
              : date == null
              ? copy(
                  '登录不会自动撤销删除。',
                  'Signing in does not cancel deletion.',
                  '로그인해도 삭제가 자동 취소되지 않습니다.',
                )
              : copy(
                  '计划删除日期：${date.year}-${date.month}-${date.day}',
                  'Scheduled deletion: ${date.year}-${date.month}-${date.day}',
                  '삭제 예정일: ${date.year}-${date.month}-${date.day}',
                ),
        ),
        const SizedBox(height: LumenisSpace.control),
        OutlinedButton(
          onPressed: _busy || outcome.continuation == null
              ? null
              : _continueIdentity,
          child: Text(
            linking
                ? copy('确认关联', 'Confirm link', '연결 확인')
                : copy(
                    '撤销删除，恢复账号',
                    'Cancel deletion and restore',
                    '삭제 취소 및 계정 복구',
                  ),
          ),
        ),
        TextButton(
          onPressed: () => setState(_resetChallenge),
          child: Text(copy('返回', 'Back', '돌아가기')),
        ),
      ],
    );
  }
}
