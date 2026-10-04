import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../l10n/lumenis_localizations.dart';

class MediaPreview extends StatelessWidget {
  const MediaPreview({
    required this.file,
    this.onPositionChanged,
    this.seekPosition,
    this.seekRequest,
    super.key,
  });
  final ContentProjectFile file;
  final ValueChanged<Duration>? onPositionChanged;
  final Duration? seekPosition;
  final int? seekRequest;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(24),
    child: Text(context.lumenisL10n.text('sh01.media.native_preview')),
  );
}
