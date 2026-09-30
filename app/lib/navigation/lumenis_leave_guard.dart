import 'dart:ui' show AppExitResponse;

import 'package:flutter/material.dart';

import 'lumenis_leave_guard_platform_stub.dart'
    if (dart.library.js_interop) 'lumenis_leave_guard_platform_web.dart'
    as platform;

/// Coordinates presentation exits. Drafts and server effects remain owned by
/// their existing controllers; allowing an exit does not cancel a server job.
class LumenisLeaveGuard extends ChangeNotifier {
  LumenisLeaveGuard({this.routeDriven = false});

  final bool routeDriven;
  Object? _owner;
  bool Function()? _needsProtection;
  Future<bool> Function()? _requestLeave;
  Future<bool>? _pending;

  bool get needsProtection => _needsProtection?.call() ?? false;

  void register(
    Object owner, {
    required bool Function() needsProtection,
    required Future<bool> Function() requestLeave,
  }) {
    _owner = owner;
    _needsProtection = needsProtection;
    _requestLeave = requestLeave;
    refresh();
  }

  void unregister(Object owner) {
    if (!identical(_owner, owner)) return;
    _owner = null;
    _needsProtection = null;
    _requestLeave = null;
    refresh();
  }

  void refresh() => notifyListeners();

  Future<bool> requestLeave() {
    if (_pending case final pending?) return pending;
    if (!needsProtection) return Future.value(true);
    final decision = _requestLeave!;
    late final Future<bool> pending;
    pending = Future<bool>.sync(decision).whenComplete(() {
      if (identical(_pending, pending)) _pending = null;
    });
    _pending = pending;
    return pending;
  }
}

class LumenisLeaveScope extends StatefulWidget {
  const LumenisLeaveScope({
    required this.guard,
    required this.child,
    super.key,
  });

  final LumenisLeaveGuard guard;
  final Widget child;

  static LumenisLeaveGuard? maybeOf(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<_LeaveScopeBinding>()?.guard;

  @override
  State<LumenisLeaveScope> createState() => _LumenisLeaveScopeState();
}

class _LumenisLeaveScopeState extends State<LumenisLeaveScope> {
  late final AppLifecycleListener _lifecycle;
  final _browserExit = platform.BrowserLeaveProtection();

  @override
  void initState() {
    super.initState();
    widget.guard.addListener(_refresh);
    _lifecycle = AppLifecycleListener(
      onExitRequested: () async => await widget.guard.requestLeave()
          ? AppExitResponse.exit
          : AppExitResponse.cancel,
    );
    _refresh();
  }

  void _refresh() => _browserExit.setProtected(widget.guard.needsProtection);

  @override
  void didUpdateWidget(covariant LumenisLeaveScope oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!identical(oldWidget.guard, widget.guard)) {
      oldWidget.guard.removeListener(_refresh);
      widget.guard.addListener(_refresh);
      _refresh();
    }
  }

  @override
  void dispose() {
    widget.guard.removeListener(_refresh);
    _browserExit.dispose();
    _lifecycle.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) =>
      _LeaveScopeBinding(guard: widget.guard, child: widget.child);
}

class _LeaveScopeBinding extends InheritedWidget {
  const _LeaveScopeBinding({required this.guard, required super.child});

  final LumenisLeaveGuard guard;

  @override
  bool updateShouldNotify(_LeaveScopeBinding oldWidget) =>
      !identical(oldWidget.guard, guard);
}
