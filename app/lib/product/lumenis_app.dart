import 'package:flutter/widgets.dart';

import '../core/lumenis_core_client.dart';
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
    return WidgetsApp(
      color: const Color(0xFF0D0E10),
      debugShowCheckedModeBanner: false,
      textStyle: const TextStyle(
        color: Color(0xFFF2F3F4),
        fontSize: 15,
        height: 1.4,
      ),
      builder: (context, _) => LaunchSurface(client: _client),
    );
  }
}
