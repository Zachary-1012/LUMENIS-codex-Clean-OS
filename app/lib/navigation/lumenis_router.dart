import 'package:flutter/material.dart';

import '../core/lumenis_icon.dart';
import 'package:go_router/go_router.dart';

import '../core/lumenis_core_client.dart';
import '../core/lumenis_theme.dart';
import '../features/launch/launch_surface.dart';
import '../l10n/lumenis_localizations.dart';
import 'lumenis_leave_guard.dart';
import 'lumenis_workspace_routes.dart';

GoRouter createLumenisRouter({
  required LumenisCoreClient client,
  required ValueChanged<Locale?> onLocaleChanged,
  String? initialLocation,
}) {
  final leaveGuard = LumenisLeaveGuard(routeDriven: true);
  return GoRouter(
    initialLocation: initialLocation ?? LumenisWorkspaceRoutes.root,
    restorationScopeId: 'lumenis-router',
    onEnter: (context, current, next, router) async {
      if (current.uri == next.uri) return const Allow();
      // SYS-06 is pushed above the current workspace task.  The underlying
      // page remains mounted, so opening a read-only controlled preview cannot
      // discard a draft and must not be treated as a destructive leave.
      final sys06Path = LumenisWorkspaceRoutes.pathForScreen('SYS-06');
      if (next.uri.path == sys06Path) {
        return const Allow();
      }
      return await leaveGuard.requestLeave()
          ? const Allow()
          : const Block.stop();
    },
    routes: [
      GoRoute(path: '/', redirect: (_, _) => LumenisWorkspaceRoutes.root),
      GoRoute(
        path: '/workspace',
        redirect: (_, _) => LumenisWorkspaceRoutes.root,
      ),
      GoRoute(
        path: LumenisWorkspaceRoutes.cth02,
        builder: (context, state) => _workspace(
          context,
          client: client,
          leaveGuard: leaveGuard,
          screenId: 'CTH-02',
          onLocaleChanged: onLocaleChanged,
        ),
      ),
      GoRoute(
        path: '/workspace/:screenId',
        builder: (context, state) {
          final screenId = state.pathParameters['screenId'] ?? '';
          if (LumenisWorkspaceRoutes.supportsWorkspaceScreen(screenId)) {
            return _workspace(
              context,
              client: client,
              leaveGuard: leaveGuard,
              screenId: screenId,
              workspaceEntry:
                  screenId == 'SH-01' &&
                      state.uri.queryParameters['entry'] == 'media' &&
                      state.uri.queryParameters['return'] == 'BMP-08'
                  ? 'media'
                  : null,
              returnScreenId:
                  screenId == 'SH-01' &&
                      state.uri.queryParameters['entry'] == 'media' &&
                      state.uri.queryParameters['return'] == 'BMP-08'
                  ? 'BMP-08'
                  : null,
              onLocaleChanged: onLocaleChanged,
            );
          }
          return const LumenisRouteBoundary.unavailable();
        },
      ),
    ],
    errorBuilder: (_, _) => const LumenisRouteBoundary.unavailable(),
  );
}

Widget _workspace(
  BuildContext context, {
  required LumenisCoreClient client,
  required LumenisLeaveGuard leaveGuard,
  required String screenId,
  String? workspaceEntry,
  String? returnScreenId,
  required ValueChanged<Locale?> onLocaleChanged,
}) => LumenisLeaveScope(
  guard: leaveGuard,
  child: LaunchSurface(
    client: client,
    initialScreenId: screenId,
    initialWorkspaceEntry: workspaceEntry,
    returnScreenId: returnScreenId,
    onScreenSelected: (nextScreenId) {
      final path = LumenisWorkspaceRoutes.pathForScreen(nextScreenId);
      if (LumenisWorkspaceRoutes.focusedReturnScreenIds.contains(
        nextScreenId,
      )) {
        context.push(path);
        return;
      }
      if (nextScreenId == 'SH-01' &&
          GoRouterState.of(context).uri.path ==
              LumenisWorkspaceRoutes.pathForScreen('BMP-08')) {
        context.go('$path?entry=media&return=BMP-08');
        return;
      }
      if (GoRouterState.of(context).uri.path != path) {
        context.go(path);
      }
    },
    onLocaleChanged: onLocaleChanged,
  ),
);

class LumenisRouteBoundary extends StatelessWidget {
  const LumenisRouteBoundary.unavailable({super.key})
    : _titleKey = 'workspace.route.unavailable.title',
      _detailKey = 'workspace.route.unavailable.detail',
      _icon = Icons.route_outlined;

  final String _titleKey;
  final String _detailKey;
  final IconData _icon;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return Scaffold(
      backgroundColor: LumenisTheme.of(context).canvas,
      body: SafeArea(
        child: SingleChildScrollView(
          key: const ValueKey('workspace-route-boundary-scroll'),
          padding: const EdgeInsets.all(28),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 620),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    _icon,
                    color: LumenisTheme.of(context).caution,
                    size: 30,
                  ),
                  const SizedBox(height: 16),
                  Semantics(
                    liveRegion: true,
                    child: Text(
                      copy.text(_titleKey),
                      style: TextStyle(
                        color: LumenisTheme.of(context).foreground,
                        fontSize: 26,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    copy.text(_detailKey),
                    style: TextStyle(
                      color: LumenisTheme.of(context).muted,
                      height: 1.55,
                    ),
                  ),
                  const SizedBox(height: 24),
                  OutlinedButton.icon(
                    onPressed: () {
                      if (context.canPop()) {
                        context.pop();
                      } else {
                        context.go(LumenisWorkspaceRoutes.root);
                      }
                    },
                    icon: const LumenisIcon(Icons.arrow_back_rounded),
                    label: Text(copy.text('workspace.route.return')),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
