import 'dart:async';
import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart' as rendering;
import 'package:flutter/services.dart';

enum GeneratedResultMotionChoice { full, followSystem, off }

/// Adds a one-shot, geometry-driven reveal to a genuinely new result event.
///
/// The result stays mounted, readable, accessible, and interactive throughout.
/// Decorative paint never intercepts input or contributes semantics. This is a
/// Flutter adaptation of the measured dotted-wireframe sequence from
/// transitions.dev UI generation (upstream 9398105c07dafe877e43197b71c15a10a3b0e3f6);
/// see the existing third-party component register for attribution and license.
class GeneratedResultReveal extends StatefulWidget {
  const GeneratedResultReveal({
    required this.child,
    required this.resultVersion,
    required this.arrivalToken,
    required this.choice,
    required this.skipLabel,
    required this.accent,
    required this.foreground,
    this.onUserInteraction,
    super.key,
  });

  final Widget child;

  /// Includes the authenticated scope and immutable result identity/hash.
  final String resultVersion;

  /// Ephemeral token emitted only by the consumer after a new result is read back.
  /// Existing/opened results must pass null.
  final String? arrivalToken;
  final GeneratedResultMotionChoice choice;
  final String skipLabel;
  final Color accent;
  final Color foreground;
  final VoidCallback? onUserInteraction;

  @override
  State<GeneratedResultReveal> createState() => GeneratedResultRevealState();
}

class GeneratedResultRevealState extends State<GeneratedResultReveal>
    with SingleTickerProviderStateMixin, WidgetsBindingObserver {
  static const _upstreamDrawingDuration = Duration(milliseconds: 2400);
  static const _runEnd = 1.09;
  static const _maxNodes = 1600;
  static const _maxTextLines = 240;
  static const _maxControls = 64;
  static const _bundledFontFamilies = <String>{
    'LumenisSansSC',
    'LumenisSansKR',
    'LumenisEmoji',
    'MaterialIcons',
    'packages/cupertino_icons/CupertinoIcons',
  };

  final GlobalKey _measuredChild = GlobalKey();
  late final AnimationController _controller = AnimationController(
    vsync: this,
    animationBehavior: AnimationBehavior.preserve,
    duration: Duration(
      microseconds: (_upstreamDrawingDuration.inMicroseconds * _runEnd).round(),
    ),
  )..addStatusListener(_onAnimationStatus);

  _MeasuredResult? _geometry;
  String? _consumedArrivalToken;
  String? _constraintSignature;
  String? _environmentSignature;
  int _preparationRevision = 0;
  bool _playing = false;

  bool get isPlaying => _playing;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    HardwareKeyboard.instance.addHandler(_onHardwareKeyEvent);
    PaintingBinding.instance.systemFonts.addListener(_onSystemFontsChanged);
    final token = widget.arrivalToken;
    if (token != null && token.isNotEmpty) {
      _schedulePreparation(token, widget.resultVersion);
    }
  }

  @override
  void didUpdateWidget(covariant GeneratedResultReveal oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.resultVersion != widget.resultVersion) {
      _cancelForUpdate();
    }
    if (oldWidget.choice != widget.choice) {
      _cancelForUpdate();
    }
    if (oldWidget.accent != widget.accent ||
        oldWidget.foreground != widget.foreground) {
      _cancelForUpdate();
    }
    if (widget.arrivalToken == null) {
      _cancelForUpdate();
    } else if (widget.arrivalToken != oldWidget.arrivalToken) {
      _schedulePreparation(widget.arrivalToken!, widget.resultVersion);
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final media = MediaQuery.maybeOf(context);
    final localeDirection = Directionality.maybeOf(context);
    final locale = Localizations.maybeLocaleOf(context);
    final inheritedStyle = DefaultTextStyle.of(context).style;
    final themeTextStyle = Theme.of(context).textTheme.bodyMedium;
    final signature = [
      media?.size,
      media?.devicePixelRatio,
      media?.textScaler,
      media?.disableAnimations,
      locale?.toLanguageTag(),
      localeDirection,
      inheritedStyle,
      themeTextStyle,
    ].join('|');
    final previous = _environmentSignature;
    _environmentSignature = signature;
    if (previous != null && previous != signature) {
      _cancelForUpdate();
    }
    if (_playing &&
        widget.choice == GeneratedResultMotionChoice.followSystem &&
        media?.disableAnimations == true) {
      _finishImmediately();
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) _finishImmediately();
  }

  void _onSystemFontsChanged() => _finishImmediately();

  bool _onHardwareKeyEvent(KeyEvent event) {
    if (event is KeyDownEvent && _focusIsWithinResult()) {
      _notifyUserInteraction();
    }
    return false;
  }

  bool _focusIsWithinResult() {
    final focusedContext = FocusManager.instance.primaryFocus?.context;
    final resultContext = _measuredChild.currentContext;
    if (focusedContext == null || resultContext == null) return false;
    var isWithinResult = false;
    focusedContext.visitAncestorElements((element) {
      if (element == resultContext) {
        isWithinResult = true;
        return false;
      }
      return true;
    });
    return isWithinResult;
  }

  void _notifyUserInteraction() {
    widget.onUserInteraction?.call();
    _finishImmediately();
  }

  void _schedulePreparation(String token, String version) {
    if (token.isEmpty || version.isEmpty || token == _consumedArrivalToken) {
      return;
    }
    _consumedArrivalToken = token;
    final revision = ++_preparationRevision;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || revision != _preparationRevision) return;
      unawaited(_prepareStableGeometry(revision, token, version));
    });
  }

  bool _choiceAllowsMotion() {
    if (widget.choice == GeneratedResultMotionChoice.off) return false;
    if (widget.choice == GeneratedResultMotionChoice.followSystem &&
        MediaQuery.maybeOf(context)?.disableAnimations == true) {
      return false;
    }
    return true;
  }

  Future<void> _prepareStableGeometry(
    int revision,
    String token,
    String version,
  ) async {
    if (!_choiceAllowsMotion()) return;
    _MeasuredResult? previous;
    // Font readiness is established by the running engine's registered,
    // bundled families plus completed RenderParagraph layout in
    // _measureResult. Repeated frames below check geometry stability only.
    for (var frame = 0; frame < 3; frame++) {
      if (!mounted || revision != _preparationRevision) return;
      // This preparation starts from a post-frame callback. Request the next
      // frame explicitly so endOfFrame cannot wait forever on an idle screen.
      WidgetsBinding.instance.scheduleFrame();
      await WidgetsBinding.instance.endOfFrame;
      if (!mounted ||
          revision != _preparationRevision ||
          token != widget.arrivalToken ||
          version != widget.resultVersion ||
          !_choiceAllowsMotion()) {
        return;
      }
      final measured = _measureResult();
      if (measured == null) return;
      if (previous != null && previous.signature == measured.signature) {
        setState(() {
          _geometry = measured;
          _playing = true;
        });
        _controller.forward(from: 0);
        return;
      }
      previous = measured;
    }
    // Unstable or oversized layout is a presentation-only failure. The real
    // result remains available and is never held behind a placeholder.
  }

  _MeasuredResult? _measureResult() {
    final object = _measuredChild.currentContext?.findRenderObject();
    if (object is! rendering.RenderBox || !object.attached || !object.hasSize) {
      return null;
    }
    if (!_usesRegisteredBundledFonts(
      DefaultTextStyle.of(context).style,
      requireFamily: true,
    )) {
      return null;
    }
    final size = object.size;
    if (!size.width.isFinite ||
        !size.height.isFinite ||
        size.width < 24 ||
        size.height < 24 ||
        size.width * size.height > 5_000_000) {
      return null;
    }

    final lineRects = <Rect>[];
    final controlRects = <Rect>[];
    final visited = <rendering.RenderObject>{};
    var overflow = false;
    var fontOrLayoutNotReady = false;

    Rect? localRect(rendering.RenderBox box, Rect rect) {
      final topLeft = box.localToGlobal(rect.topLeft, ancestor: object);
      final bottomRight = box.localToGlobal(rect.bottomRight, ancestor: object);
      if (!topLeft.dx.isFinite ||
          !topLeft.dy.isFinite ||
          !bottomRight.dx.isFinite ||
          !bottomRight.dy.isFinite) {
        return null;
      }
      final result = Rect.fromPoints(
        topLeft,
        bottomRight,
      ).intersect(Offset.zero & size);
      if (result.isEmpty || result.width < 1 || result.height < 1) return null;
      return result;
    }

    bool hasAction(rendering.SemanticsProperties properties) =>
        properties.button == true ||
        properties.link == true ||
        properties.textField == true ||
        properties.slider == true ||
        properties.onTap != null ||
        properties.onLongPress != null ||
        properties.onExpand != null ||
        properties.onCollapse != null ||
        properties.onIncrease != null ||
        properties.onDecrease != null ||
        properties.onCopy != null;

    void visit(rendering.RenderObject node) {
      if (overflow || !visited.add(node)) return;
      if (visited.length > _maxNodes) {
        overflow = true;
        return;
      }
      if (node is rendering.RenderParagraph) {
        final text = node.text.toPlainText();
        if (text.isNotEmpty) {
          if (!node.hasSize || !_spanUsesRegisteredBundledFonts(node.text)) {
            fontOrLayoutNotReady = true;
            return;
          }
          final strut = node.strutStyle;
          if (strut != null) {
            final strutFamilies = <String>[
              if (strut.fontFamily != null) strut.fontFamily!,
              ...?strut.fontFamilyFallback,
            ];
            if (strutFamilies.isEmpty ||
                !_fontFamiliesAreRegistered(strutFamilies)) {
              fontOrLayoutNotReady = true;
              return;
            }
          }
          final boxes = node.getBoxesForSelection(
            TextSelection(baseOffset: 0, extentOffset: text.length),
          );
          if (lineRects.length + boxes.length > _maxTextLines) {
            overflow = true;
            return;
          }
          for (final box in boxes) {
            final rect = localRect(node, box.toRect());
            if (rect != null) lineRects.add(rect);
          }
        }
      }
      if (node is rendering.RenderSemanticsAnnotations &&
          node.hasSize &&
          hasAction(node.properties)) {
        final rect = localRect(node, Offset.zero & node.size);
        if (rect != null) {
          if (controlRects.length >= _maxControls) {
            overflow = true;
            return;
          }
          controlRects.add(rect);
        }
      }
      node.visitChildren(visit);
    }

    visit(object);
    if (overflow || fontOrLayoutNotReady || lineRects.isEmpty) return null;

    final strokes = <_MeasuredStroke>[];
    final outline = Path()
      ..addRRect(
        RRect.fromRectAndRadius(Offset.zero & size, const Radius.circular(12)),
      );
    strokes.addAll(_measurePath(outline));
    for (final rect in controlRects) {
      final path = Path()
        ..addRRect(
          RRect.fromRectAndRadius(
            rect,
            Radius.circular(math.min(8, rect.height / 3)),
          ),
        );
      strokes.addAll(_measurePath(path));
    }
    for (final rect in lineRects) {
      final y = rect.top + rect.height * .56;
      final path = Path()
        ..moveTo(rect.left, y)
        ..lineTo(rect.right, y);
      strokes.addAll(_measurePath(path));
    }
    if (strokes.isEmpty) return null;
    final signature = [
      size.width.toStringAsFixed(2),
      size.height.toStringAsFixed(2),
      ...lineRects.map(_rectSignature),
      ...controlRects.map(_rectSignature),
    ].join('|');
    return _MeasuredResult(
      size: size,
      strokes: List.unmodifiable(strokes),
      signature: signature,
      constraintsSignature: _constraintSignature ?? '',
    );
  }

  List<_MeasuredStroke> _measurePath(Path path) => [
    for (final metric in path.computeMetrics())
      if (metric.length > 0) _MeasuredStroke(metric),
  ];

  bool _spanUsesRegisteredBundledFonts(InlineSpan span) {
    if (!_usesRegisteredBundledFonts(span.style)) return false;
    if (span is TextSpan) {
      for (final child in span.children ?? const <InlineSpan>[]) {
        if (!_spanUsesRegisteredBundledFonts(child)) return false;
      }
    }
    return true;
  }

  bool _usesRegisteredBundledFonts(
    TextStyle? style, {
    bool requireFamily = false,
  }) {
    if (style == null) return !requireFamily;
    final families = <String>[
      if (style.fontFamily != null) style.fontFamily!,
      ...?style.fontFamilyFallback,
    ];
    if (!_fontFamiliesAreRegistered(families)) return false;
    if (requireFamily && families.isEmpty) return false;
    if (!style.inherit && families.isEmpty) return false;
    return true;
  }

  bool _fontFamiliesAreRegistered(Iterable<String> families) =>
      families.every(_bundledFontFamilies.contains);

  String _rectSignature(Rect rect) =>
      '${rect.left.toStringAsFixed(2)},${rect.top.toStringAsFixed(2)},'
      '${rect.width.toStringAsFixed(2)},${rect.height.toStringAsFixed(2)}';

  void cancelForScrollOrInteraction() => _finishImmediately();

  void _onAnimationStatus(AnimationStatus status) {
    if (status == AnimationStatus.completed) _finishImmediately();
  }

  void _cancelForUpdate() {
    _preparationRevision++;
    _controller.stop();
    _playing = false;
    _geometry = null;
  }

  void _finishImmediately() {
    final hadVisiblePresentation = _playing || _geometry != null;
    _preparationRevision++;
    _controller.stop();
    if (!hadVisiblePresentation) return;
    if (mounted) {
      setState(() {
        _playing = false;
        _geometry = null;
      });
    } else {
      _playing = false;
      _geometry = null;
    }
  }

  @override
  Widget build(BuildContext context) => Column(
    mainAxisSize: MainAxisSize.min,
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Align(
        alignment: Alignment.centerRight,
        child: ExcludeFocus(
          key: const ValueKey('generated-result-reveal/skip-focus'),
          excluding: !_playing,
          child: ExcludeSemantics(
            key: const ValueKey('generated-result-reveal/skip-semantics'),
            excluding: !_playing,
            child: IgnorePointer(
              key: const ValueKey('generated-result-reveal/skip-pointer'),
              ignoring: !_playing,
              child: Opacity(
                key: const ValueKey('generated-result-reveal/skip-opacity'),
                opacity: _playing ? 1 : 0,
                child: TextButton(
                  key: const ValueKey('generated-result-reveal/skip'),
                  onPressed: _playing ? _finishImmediately : null,
                  child: Text(widget.skipLabel),
                ),
              ),
            ),
          ),
        ),
      ),
      LayoutBuilder(
        builder: (context, constraints) {
          final signature = [
            constraints.minWidth,
            constraints.maxWidth,
            constraints.minHeight,
            constraints.maxHeight,
          ].join('|');
          final previous = _constraintSignature;
          _constraintSignature = signature;
          if (previous != null && previous != signature && _playing) {
            WidgetsBinding.instance.addPostFrameCallback((_) {
              if (mounted) _finishImmediately();
            });
          }

          final geometry = _geometry;
          final geometryMatchesConstraints =
              geometry?.constraintsSignature == signature;
          return Stack(
            fit: StackFit.passthrough,
            clipBehavior: Clip.hardEdge,
            children: [
              Listener(
                behavior: HitTestBehavior.deferToChild,
                onPointerDown: (_) => _notifyUserInteraction(),
                child: KeyedSubtree(key: _measuredChild, child: widget.child),
              ),
              if (_playing && geometry != null && geometryMatchesConstraints)
                Positioned.fill(
                  child: AnimatedBuilder(
                    animation: _controller,
                    builder: (context, _) => IgnorePointer(
                      child: ExcludeSemantics(
                        child: CustomPaint(
                          key: const ValueKey('generated-result-reveal/paint'),
                          painter: _GeneratedResultPainter(
                            geometry: geometry,
                            progress: _controller.value * _runEnd,
                            accent: widget.accent,
                            foreground: widget.foreground,
                          ),
                          child: const SizedBox.expand(),
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    ],
  );

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    HardwareKeyboard.instance.removeHandler(_onHardwareKeyEvent);
    PaintingBinding.instance.systemFonts.removeListener(_onSystemFontsChanged);
    _controller
      ..removeStatusListener(_onAnimationStatus)
      ..dispose();
    super.dispose();
  }
}

class _MeasuredResult {
  const _MeasuredResult({
    required this.size,
    required this.strokes,
    required this.signature,
    required this.constraintsSignature,
  });

  final Size size;
  final List<_MeasuredStroke> strokes;
  final String signature;
  final String constraintsSignature;
}

class _MeasuredStroke {
  const _MeasuredStroke(this.metric);

  final ui.PathMetric metric;
}

class _GeneratedResultPainter extends CustomPainter {
  const _GeneratedResultPainter({
    required this.geometry,
    required this.progress,
    required this.accent,
    required this.foreground,
  });

  final _MeasuredResult geometry;
  final double progress;
  final Color accent;
  final Color foreground;

  static double _clamp(double value) => value.clamp(0.0, 1.0);

  static double _ease(double value) =>
      const Cubic(.16, 1, .3, 1).transform(_clamp(value));

  static double _revealEase(double value) =>
      const Cubic(.22, 1, .36, 1).transform(_clamp(value));

  @override
  void paint(Canvas canvas, Size size) {
    if (size.isEmpty || size != geometry.size) return;
    canvas.save();
    canvas.clipRect(Offset.zero & size);

    final p = progress.clamp(0.0, 1.09);
    final clean = 1 - _ease((p - .84) / (.1));
    _paintDotField(canvas, size, p, clean);
    _paintGuides(canvas, size, p);
    _paintWireframe(canvas, p, clean);
    _paintRevealScan(canvas, size, p);

    canvas.restore();
  }

  void _paintDotField(Canvas canvas, Size size, double p, double clean) {
    final area = size.width * size.height;
    final step = math.max(14.0, math.sqrt(area / 900));
    final center = Offset(size.width / 2, size.height / 2);
    final maximumDistance = center.distance + step;
    final expansion = _ease(p / .3) * (maximumDistance + 28);
    final rainStrength = _ease((p - .04) / .16) * (1 - _ease((p - .62) / .24));
    final dotPaint = Paint()..style = PaintingStyle.fill;

    for (var x = step / 2; x < size.width; x += step) {
      final column = (x / step).round();
      final phase = ((column * 0.61803398875) % 1) * (size.height + step);
      final streamY =
          ((p * size.height * 1.4 + phase) % (size.height + step)) - step / 2;
      for (var y = step / 2; y < size.height; y += step) {
        final distance = (Offset(x, y) - center).distance;
        final delta = expansion - distance;
        final wave = math.exp(-math.pow(delta / (step * .75), 2));
        final rain =
            rainStrength *
            math.max(0.0, 1 - (streamY - y).abs() / (step * 1.8));
        final opacity = (.1 + wave * .62 + rain * .34) * clean;
        if (opacity < .035) continue;
        dotPaint.color = accent.withValues(alpha: opacity.clamp(0.0, .7));
        canvas.drawCircle(
          Offset(x, y),
          1.1 + math.max(wave, rain) * .8,
          dotPaint,
        );
      }
    }
  }

  void _paintGuides(Canvas canvas, Size size, double p) {
    final amount = _ease((p - .04) / .26) * (1 - _ease((p - .3) / .2));
    if (amount <= 0) return;
    final paint = Paint()
      ..color = accent.withValues(alpha: .28 * amount)
      ..strokeWidth = 1
      ..style = PaintingStyle.stroke;
    final extent = math.min(18.0, math.min(size.width, size.height) / 5);
    for (final corner in <Offset>[
      Offset.zero,
      Offset(size.width, 0),
      Offset(size.width, size.height),
      Offset(0, size.height),
    ]) {
      final xDirection = corner.dx == 0 ? 1.0 : -1.0;
      final yDirection = corner.dy == 0 ? 1.0 : -1.0;
      canvas.drawLine(corner, corner.translate(extent * xDirection, 0), paint);
      canvas.drawLine(corner, corner.translate(0, extent * yDirection), paint);
    }
  }

  void _paintWireframe(Canvas canvas, double p, double clean) {
    final partsStart = .28;
    final partsSpan = .26;
    final partsDuration = .2;
    final partsTotal = geometry.strokes.length;
    final reveal = _revealEase((p - .74) / (.315));
    final wireFade = (1 - .6 * reveal) * clean;
    final paint = Paint()
      ..color = foreground.withValues(alpha: .72 * wireFade)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.25
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    final runnerPaint = Paint()
      ..color = accent.withValues(alpha: .95 * wireFade)
      ..style = PaintingStyle.fill;

    for (var index = 0; index < partsTotal; index++) {
      final start =
          partsStart +
          (partsTotal <= 1 ? 0 : partsSpan * index / (partsTotal - 1));
      final amount = _ease((p - start) / partsDuration);
      if (amount <= 0) continue;
      final metric = geometry.strokes[index].metric;
      final length = metric.length;
      if (length <= 0) continue;
      final end = length * amount;
      canvas.drawPath(metric.extractPath(0, end), paint);
      if (amount < 1) {
        final tangent = metric.getTangentForOffset(end);
        if (tangent != null) {
          canvas.drawCircle(tangent.position, 2.1, runnerPaint);
        }
      }
    }
  }

  void _paintRevealScan(Canvas canvas, Size size, double p) {
    final raw = _clamp((p - .74) / .315);
    if (raw <= 0 || raw >= 1.02) return;
    final eased = _revealEase(raw);
    final y = eased * (size.height + 6) - 3;
    final glowOpacity = (.11 * (1 - _ease((p - 1.0) / .055))).clamp(0.0, .11);
    if (glowOpacity > 0) {
      final glow = Paint()
        ..shader = ui.Gradient.linear(Offset(0, y - 24), Offset(0, y + 24), [
          accent.withValues(alpha: 0),
          accent.withValues(alpha: glowOpacity),
        ]);
      canvas.drawRect(Rect.fromLTWH(0, y - 24, size.width, 48), glow);
    }
    final line = Paint()
      ..color = accent.withValues(alpha: .72 * (1 - eased))
      ..strokeWidth = 1.2
      ..strokeCap = StrokeCap.round;
    canvas.drawLine(Offset(-8, y), Offset(size.width + 8, y), line);
    canvas.drawCircle(Offset(0, y), 2.4, line);
    canvas.drawCircle(Offset(size.width, y), 2.4, line);
  }

  @override
  bool shouldRepaint(covariant _GeneratedResultPainter oldDelegate) =>
      oldDelegate.geometry.signature != geometry.signature ||
      oldDelegate.progress != progress ||
      oldDelegate.accent != accent ||
      oldDelegate.foreground != foreground;
}
