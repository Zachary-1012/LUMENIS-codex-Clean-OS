import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../core/lumenis_core_client.dart';
import '../core/lumenis_theme.dart';
import '../features/launch/launch_surface.dart';
import '../l10n/lumenis_localizations.dart';
import 'lumenis_workspace_routes.dart';

GoRouter createLumenisRouter({
  required LumenisCoreClient client,
  required ValueChanged<Locale?> onLocaleChanged,
  String? initialLocation,
}) => GoRouter(
  initialLocation: initialLocation ?? LumenisWorkspaceRoutes.root,
  restorationScopeId: 'lumenis-router',
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
        screenId: 'CTH-02',
        onLocaleChanged: onLocaleChanged,
      ),
    ),
    GoRoute(
      path: '/workspace/:screenId',
      builder: (context, state) {
        final screenId = state.pathParameters['screenId'] ?? '';
        if (LumenisWorkspaceRoutes.desktopRequiredScreenIds.contains(
          screenId,
        )) {
          return const LumenisRouteBoundary.desktopRequired();
        }
        if (LumenisWorkspaceRoutes.supportsWorkspaceScreen(screenId)) {
          return _workspace(
            context,
            client: client,
            screenId: screenId,
            onLocaleChanged: onLocaleChanged,
          );
        }
        return const LumenisRouteBoundary.unavailable();
      },
    ),
  ],
  errorBuilder: (_, _) => const LumenisRouteBoundary.unavailable(),
);

Widget _workspace(
  BuildContext context, {
  required LumenisCoreClient client,
  required String screenId,
  required ValueChanged<Locale?> onLocaleChanged,
}) => LaunchSurface(
  client: client,
  initialScreenId: screenId,
  onScreenSelected: (nextScreenId) {
    final path = LumenisWorkspaceRoutes.pathForScreen(nextScreenId);
    if (GoRouterState.of(context).uri.path != path) {
      context.go(path);
    }
  },
  onLocaleChanged: onLocaleChanged,
);

class LumenisRouteBoundary extends StatelessWidget {
  const LumenisRouteBoundary.unavailable({super.key}) : desktopRequired = false;

  const LumenisRouteBoundary.desktopRequired({super.key})
    : desktopRequired = true;

  final bool desktopRequired;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final titleKey = desktopRequired
        ? 'workspace.capability.desktop_required.title'
        : 'workspace.route.unavailable.title';
    final detailKey = desktopRequired
        ? 'workspace.capability.desktop_required.detail'
        : 'workspace.route.unavailable.detail';
    return Scaffold(
      backgroundColor: LumenisTheme.of(context).canvas,
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 620),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    desktopRequired
                        ? Icons.desktop_windows_outlined
                        : Icons.route_outlined,
                    color: LumenisTheme.of(context).caution,
                    size: 30,
                  ),
                  const SizedBox(height: 16),
                  Semantics(
                    liveRegion: true,
                    child: Text(
                      copy.text(titleKey),
                      style: TextStyle(
                        color: LumenisTheme.of(context).foreground,
                        fontSize: 26,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    copy.text(detailKey),
                    style: TextStyle(
                      color: LumenisTheme.of(context).muted,
                      height: 1.55,
                    ),
                  ),
                  const SizedBox(height: 24),
                  OutlinedButton.icon(
                    onPressed: () => context.go(LumenisWorkspaceRoutes.root),
                    icon: const Icon(Icons.arrow_back_rounded),
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
