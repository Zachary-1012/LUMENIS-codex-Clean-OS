import 'package:flutter/material.dart';

import '../core/lumenis_core_client.dart';
import '../core/lumenis_theme.dart';
import '../features/launch/launch_surface.dart';

class LumenisApp extends StatefulWidget {
  const LumenisApp({super.key});

  @override
  State<LumenisApp> createState() => _LumenisAppState();
}

class _LumenisAppState extends State<LumenisApp> {
  late final LumenisCoreClient _client = LumenisCoreClient();

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '序境 · LUMENIS',
      theme: LumenisTheme.dark,
      themeMode: ThemeMode.dark,
      restorationScopeId: 'lumenis',
      debugShowCheckedModeBanner: false,
      home: LaunchSurface(client: _client),
    );
  }
}
