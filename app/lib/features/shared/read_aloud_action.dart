import 'dart:async';

import 'package:flutter/material.dart';

import '../../l10n/lumenis_localizations.dart';
import 'read_aloud_contract.dart';
import 'read_aloud_service.dart';

enum ReadAloudPurpose { sourceBrief, podcastScript, videoCaption, savedPreview }

/// A transient local-system-voice preview for text already visible to the user.
/// No text or generated audio is sent to a service or persisted by this action.
class ReadAloudAction extends StatefulWidget {
  const ReadAloudAction({
    required this.sessionId,
    required this.scopeVersion,
    required this.text,
    required this.purpose,
    this.service,
    this.onUserInteraction,
    super.key,
  });

  final String sessionId;
  final String scopeVersion;
  final String text;
  final ReadAloudPurpose purpose;
  final ReadAloudService? service;
  final VoidCallback? onUserInteraction;

  @override
  State<ReadAloudAction> createState() => _ReadAloudActionState();
}

class _ReadAloudActionState extends State<ReadAloudAction>
    with WidgetsBindingObserver {
  late ReadAloudService _service;
  late ReadAloudLocale _locale;
  ReadAloudRate _rate = ReadAloudRate.normal;
  String? _languageCode;
  ModalRoute<dynamic>? _observedRoute;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _service = widget.service ?? ReadAloudService.instance;
    _locale = ReadAloudLocale.zhCn;
    _service.addListener(_refresh);
    unawaited(_service.refreshAvailability());
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final route = ModalRoute.of(context);
    if (route != _observedRoute) {
      _observedRoute?.secondaryAnimation?.removeStatusListener(
        _onRouteAnimationStatus,
      );
      _observedRoute = route;
      route?.secondaryAnimation?.addStatusListener(_onRouteAnimationStatus);
    }
    final languageCode = LumenisLocalizations.of(context).locale.languageCode;
    if (_languageCode == languageCode) return;
    final isInitial = _languageCode == null;
    _languageCode = languageCode;
    final locale = _localeForLanguage(languageCode);
    if (_locale == locale) return;
    if (!isInitial) {
      unawaited(
        _service.stopSession(
          sessionId: widget.sessionId,
          scopeVersion: widget.scopeVersion,
        ),
      );
    }
    _locale = locale;
  }

  void _onRouteAnimationStatus(AnimationStatus status) {
    if (status == AnimationStatus.forward) {
      unawaited(
        _service.stopSession(
          sessionId: widget.sessionId,
          scopeVersion: widget.scopeVersion,
        ),
      );
    }
  }

  @override
  void didUpdateWidget(covariant ReadAloudAction oldWidget) {
    super.didUpdateWidget(oldWidget);
    final identityChanged =
        oldWidget.sessionId != widget.sessionId ||
        oldWidget.scopeVersion != widget.scopeVersion ||
        oldWidget.text != widget.text;
    if (identityChanged) {
      unawaited(
        _service.stopSession(
          sessionId: oldWidget.sessionId,
          scopeVersion: oldWidget.scopeVersion,
        ),
      );
    }
    if (!identical(oldWidget.service, widget.service) &&
        widget.service != null) {
      _service.removeListener(_refresh);
      unawaited(
        _service.stopSession(
          sessionId: oldWidget.sessionId,
          scopeVersion: oldWidget.scopeVersion,
        ),
      );
      _service = widget.service!;
      _service.addListener(_refresh);
      unawaited(_service.refreshAvailability());
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) {
      unawaited(
        _service.stopSession(
          sessionId: widget.sessionId,
          scopeVersion: widget.scopeVersion,
        ),
      );
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _observedRoute?.secondaryAnimation?.removeStatusListener(
      _onRouteAnimationStatus,
    );
    _service.removeListener(_refresh);
    unawaited(
      _service.stopSession(
        sessionId: widget.sessionId,
        scopeVersion: widget.scopeVersion,
      ),
    );
    super.dispose();
  }

  void _refresh() {
    if (mounted) setState(() {});
  }

  Future<void> _startOrStop() async {
    widget.onUserInteraction?.call();
    final state = _service.stateFor(
      sessionId: widget.sessionId,
      scopeVersion: widget.scopeVersion,
    );
    if (state.status == ReadAloudStatus.starting ||
        state.status == ReadAloudStatus.playing ||
        state.status == ReadAloudStatus.paused) {
      await _service.stopSession(
        sessionId: widget.sessionId,
        scopeVersion: widget.scopeVersion,
      );
      return;
    }
    await _service.start(
      ReadAloudRequest(
        sessionId: widget.sessionId,
        scopeVersion: widget.scopeVersion,
        text: widget.text,
        locale: _locale,
        rate: _rate,
      ),
    );
  }

  Future<void> _selectLocale(ReadAloudLocale value) async {
    widget.onUserInteraction?.call();
    await _service.stopSession(
      sessionId: widget.sessionId,
      scopeVersion: widget.scopeVersion,
    );
    if (mounted) setState(() => _locale = value);
  }

  Future<void> _selectRate(ReadAloudRate value) async {
    widget.onUserInteraction?.call();
    await _service.stopSession(
      sessionId: widget.sessionId,
      scopeVersion: widget.scopeVersion,
    );
    if (mounted) setState(() => _rate = value);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = LumenisLocalizations.of(context);
    final availability = _service.availability;
    final state = _service.stateFor(
      sessionId: widget.sessionId,
      scopeVersion: widget.scopeVersion,
    );
    final active =
        state.status == ReadAloudStatus.starting ||
        state.status == ReadAloudStatus.playing ||
        state.status == ReadAloudStatus.paused;
    final platformSupported = availability?.supported == true;
    final localeAvailable =
        platformSupported && availability!.localLocales.contains(_locale.tag);
    final labels = _labels(l10n);
    if (widget.text.trim().isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 10,
            runSpacing: 8,
            children: [
              Text(labels['title']!),
              Text(labels['locale']!),
              SizedBox(
                width: 220,
                child: DropdownButton<ReadAloudLocale>(
                  key: const ValueKey('read-aloud/locale'),
                  isExpanded: true,
                  itemHeight: null,
                  value: _locale,
                  selectedItemBuilder: (_) => ReadAloudLocale.values
                      .map(
                        (locale) => Text(
                          labels['locale.${locale.name}']!,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      )
                      .toList(growable: false),
                  onChanged: (value) {
                    if (value != null) unawaited(_selectLocale(value));
                  },
                  items: ReadAloudLocale.values
                      .map(
                        (locale) => DropdownMenuItem(
                          value: locale,
                          child: Text(labels['locale.${locale.name}']!),
                        ),
                      )
                      .toList(growable: false),
                ),
              ),
              Text(labels['rate']!),
              SizedBox(
                width: 140,
                child: DropdownButton<ReadAloudRate>(
                  key: const ValueKey('read-aloud/rate'),
                  isExpanded: true,
                  itemHeight: null,
                  value: _rate,
                  selectedItemBuilder: (_) => ReadAloudRate.values
                      .map(
                        (rate) => Text(
                          labels['rate.${rate.name}']!,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      )
                      .toList(growable: false),
                  onChanged: (value) {
                    if (value != null) unawaited(_selectRate(value));
                  },
                  items: ReadAloudRate.values
                      .map(
                        (rate) => DropdownMenuItem(
                          value: rate,
                          child: Text(labels['rate.${rate.name}']!),
                        ),
                      )
                      .toList(growable: false),
                ),
              ),
              TextButton.icon(
                key: const ValueKey('read-aloud/toggle'),
                onPressed: active || platformSupported
                    ? () => unawaited(_startOrStop())
                    : null,
                icon: Icon(active ? Icons.stop_rounded : Icons.volume_up),
                label: Text(active ? labels['stop']! : labels['play']!),
              ),
            ],
          ),
          Semantics(
            liveRegion: true,
            child: Text(
              _statusLabel(labels, state, localeAvailable, availability),
              key: const ValueKey('read-aloud/status'),
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
          Text(
            labels['purpose.${widget.purpose.name}']!,
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  String _statusLabel(
    Map<String, String> labels,
    ReadAloudState state,
    bool localeAvailable,
    ReadAloudAvailability? availability,
  ) {
    if (availability == null) return labels['status.checking']!;
    if (!availability.supported) return labels['status.unavailable']!;
    if (!localeAvailable) return labels['status.noLocalVoice']!;
    return switch (state.status) {
      ReadAloudStatus.starting => labels['status.starting']!,
      ReadAloudStatus.playing => labels['status.playing']!,
      ReadAloudStatus.paused => labels['status.paused']!,
      ReadAloudStatus.completed => labels['status.completed']!,
      ReadAloudStatus.failed => labels['status.failed']!,
      _ => labels['status.ready']!,
    };
  }

  ReadAloudLocale _localeForLanguage(String language) => switch (language) {
    'en' => ReadAloudLocale.enUs,
    'ko' => ReadAloudLocale.koKr,
    _ => ReadAloudLocale.zhCn,
  };

  Map<String, String> _labels(LumenisLocalizations l10n) => {
    for (final key in const [
      'title',
      'locale',
      'rate',
      'play',
      'stop',
      'status.checking',
      'status.unavailable',
      'status.noLocalVoice',
      'status.starting',
      'status.playing',
      'status.paused',
      'status.completed',
      'status.failed',
      'status.ready',
      'locale.zhCn',
      'locale.enUs',
      'locale.koKr',
      'rate.slow',
      'rate.normal',
      'rate.fast',
      'purpose.sourceBrief',
      'purpose.podcastScript',
      'purpose.videoCaption',
      'purpose.savedPreview',
    ])
      key: l10n.text('shared.read_aloud.$key'),
  };
}
