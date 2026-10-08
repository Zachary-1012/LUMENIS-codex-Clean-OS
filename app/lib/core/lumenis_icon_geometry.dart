// Generated from the M-reviewed icon-geometry.json manifest.
// Path objects are created once; this file has no runtime parser.
import 'dart:ui' show Canvas, Offset, Paint, Path, Radius, Rect, RRect;
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart' show IconData, Icons;

const int lumenisIconGeometryCount = 122;
const int lumenisIconSymbolCount = 164;

const Map<String, String> lumenisIconAliases = <String, String>{
  'account_tree_outlined': 'tree',
  'add': 'plus',
  'add_photo_alternate_outlined': 'imageAdd',
  'add_rounded': 'plus',
  'add_to_photos_outlined': 'photosAdd',
  'adjust_rounded': 'radioSelected',
  'alt_route_rounded': 'alternative',
  'apartment_rounded': 'building',
  'arrow_back': 'back',
  'arrow_back_rounded': 'back',
  'arrow_forward': 'forward',
  'arrow_forward_outlined': 'forward',
  'arrow_forward_rounded': 'forward',
  'arrow_outward_rounded': 'outward',
  'arrow_right_rounded': 'chevronRight',
  'article_outlined': 'article',
  'assignment_outlined': 'clipboard',
  'audio_file_outlined': 'audioFile',
  'audiotrack_rounded': 'music',
  'auto_awesome_outlined': 'intent',
  'auto_graph_rounded': 'timeline',
  'block_outlined': 'block',
  'blur_on': 'blur',
  'branding_watermark_outlined': 'brand',
  'calendar_month_rounded': 'calendar',
  'center_focus_strong': 'focus',
  'center_focus_strong_rounded': 'focus',
  'check': 'check',
  'check_circle_outline': 'checkCircle',
  'check_circle_outline_rounded': 'checkCircle',
  'check_rounded': 'check',
  'checklist_rounded': 'checklist',
  'chevron_left': 'chevronLeft',
  'chevron_right': 'chevronRight',
  'chevron_right_rounded': 'chevronRight',
  'circle': 'circle',
  'clear': 'close',
  'close': 'close',
  'close_rounded': 'close',
  'cloud_off_outlined': 'cloudOff',
  'color_lens_outlined': 'palette',
  'compare_arrows_outlined': 'compare',
  'compare_arrows_rounded': 'compare',
  'copy_outlined': 'copy',
  'dark_mode_outlined': 'moon',
  'data_exploration_outlined': 'query',
  'description_outlined': 'document',
  'desktop_windows_outlined': 'desktop',
  'download_outlined': 'download',
  'edit_note_rounded': 'edit',
  'event_busy_outlined': 'eventOff',
  'event_note_outlined': 'eventNote',
  'expand_less': 'chevronUp',
  'expand_more_rounded': 'chevronDown',
  'extension_outlined': 'extension',
  'fact_check_outlined': 'factCheck',
  'file_download_outlined': 'download',
  'filter_alt_off_outlined': 'filterOff',
  'filter_alt_outlined': 'filter',
  'flag_outlined': 'flag',
  'folder_open_outlined': 'folderOpen',
  'folder_outlined': 'folder',
  'forum_outlined': 'forum',
  'grid_view_rounded': 'layout',
  'help_outline': 'help',
  'history': 'history',
  'history_rounded': 'history',
  'hourglass_empty_rounded': 'hourglass',
  'hub_outlined': 'hub',
  'image_not_supported_outlined': 'imageOff',
  'image_outlined': 'image',
  'inbox_outlined': 'inbox',
  'info_outline': 'info',
  'info_outline_rounded': 'info',
  'insert_drive_file_outlined': 'file',
  'insights_outlined': 'insights',
  'inventory_2_outlined': 'archive',
  'ios_share_rounded': 'share',
  'keyboard_arrow_down_rounded': 'chevronDown',
  'keyboard_arrow_up_rounded': 'chevronUp',
  'language_rounded': 'language',
  'library_books_outlined': 'source',
  'light_mode_outlined': 'sun',
  'lightbulb_outline_rounded': 'lightbulb',
  'link': 'link',
  'link_rounded': 'link',
  'local_offer_outlined': 'tag',
  'lock_outline': 'lock',
  'lock_outline_rounded': 'lock',
  'menu_rounded': 'menu',
  'mic_none_rounded': 'microphone',
  'monitor_heart_outlined': 'monitor',
  'mood_rounded': 'mood',
  'more_horiz_rounded': 'more',
  'movie_creation_outlined': 'movie',
  'movie_outlined': 'movie',
  'music_note_outlined': 'music',
  'notifications_none_rounded': 'notification',
  'open_in_full_rounded': 'expand',
  'open_in_new_rounded': 'open',
  'outbox_outlined': 'outbox',
  'palette_outlined': 'palette',
  'pause_circle_outline_rounded': 'pauseCircle',
  'pause_rounded': 'pause',
  'picture_as_pdf_outlined': 'pdf',
  'place_outlined': 'place',
  'play_arrow_rounded': 'play',
  'play_circle_outline': 'playCircle',
  'play_circle_outline_rounded': 'playCircle',
  'policy_outlined': 'shield',
  'public_rounded': 'globe',
  'query_stats_outlined': 'query',
  'query_stats_rounded': 'query',
  'radar_rounded': 'radar',
  'radio_button_checked': 'radioSelected',
  'radio_button_checked_rounded': 'radioSelected',
  'radio_button_off': 'radio',
  'radio_button_unchecked': 'radio',
  'radio_button_unchecked_rounded': 'radio',
  'rate_review_outlined': 'review',
  'refresh': 'refresh',
  'refresh_rounded': 'refresh',
  'remove_circle_outline': 'removeCircle',
  'remove_rounded': 'minus',
  'replay_rounded': 'replay',
  'restart_alt_rounded': 'replay',
  'route_outlined': 'route',
  'save_alt_outlined': 'download',
  'schedule_outlined': 'clock',
  'schedule_rounded': 'clock',
  'school_outlined': 'school',
  'search': 'search',
  'search_rounded': 'search',
  'sell_outlined': 'tag',
  'shield_moon_outlined': 'shieldNight',
  'shield_outlined': 'shield',
  'slideshow_outlined': 'slideshow',
  'source_outlined': 'source',
  'space_dashboard_outlined': 'layout',
  'stop_circle_outlined': 'stopCircle',
  'storefront_outlined': 'store',
  'straighten_rounded': 'ruler',
  'sync_problem': 'unavailable',
  'sync_problem_outlined': 'unavailable',
  'table_chart_outlined': 'table',
  'timeline_rounded': 'timeline',
  'trending_down_rounded': 'trendDown',
  'trending_flat_rounded': 'trendFlat',
  'trending_up_rounded': 'trendUp',
  'tune_rounded': 'tune',
  'undo': 'undo',
  'undo_rounded': 'undo',
  'verified_outlined': 'verified',
  'video_collection_outlined': 'videoLibrary',
  'video_library_outlined': 'videoLibrary',
  'view_list_outlined': 'list',
  'view_list_rounded': 'list',
  'view_timeline_outlined': 'tracks',
  'visibility_off_outlined': 'eyeOff',
  'visibility_outlined': 'eye',
  'volume_off_rounded': 'volumeOff',
  'volume_up_rounded': 'volume',
  'warning_amber_rounded': 'warning',
  'zoom_in_rounded': 'zoom',
};

const Map<String, IconData> lumenisIconData = <String, IconData>{
  'account_tree_outlined': Icons.account_tree_outlined,
  'add': Icons.add,
  'add_photo_alternate_outlined': Icons.add_photo_alternate_outlined,
  'add_rounded': Icons.add_rounded,
  'add_to_photos_outlined': Icons.add_to_photos_outlined,
  'adjust_rounded': Icons.adjust_rounded,
  'alt_route_rounded': Icons.alt_route_rounded,
  'apartment_rounded': Icons.apartment_rounded,
  'arrow_back': Icons.arrow_back,
  'arrow_back_rounded': Icons.arrow_back_rounded,
  'arrow_forward': Icons.arrow_forward,
  'arrow_forward_outlined': Icons.arrow_forward_outlined,
  'arrow_forward_rounded': Icons.arrow_forward_rounded,
  'arrow_outward_rounded': Icons.arrow_outward_rounded,
  'arrow_right_rounded': Icons.arrow_right_rounded,
  'article_outlined': Icons.article_outlined,
  'assignment_outlined': Icons.assignment_outlined,
  'audio_file_outlined': Icons.audio_file_outlined,
  'audiotrack_rounded': Icons.audiotrack_rounded,
  'auto_awesome_outlined': Icons.auto_awesome_outlined,
  'auto_graph_rounded': Icons.auto_graph_rounded,
  'block_outlined': Icons.block_outlined,
  'blur_on': Icons.blur_on,
  'branding_watermark_outlined': Icons.branding_watermark_outlined,
  'calendar_month_rounded': Icons.calendar_month_rounded,
  'center_focus_strong': Icons.center_focus_strong,
  'center_focus_strong_rounded': Icons.center_focus_strong_rounded,
  'check': Icons.check,
  'check_circle_outline': Icons.check_circle_outline,
  'check_circle_outline_rounded': Icons.check_circle_outline_rounded,
  'check_rounded': Icons.check_rounded,
  'checklist_rounded': Icons.checklist_rounded,
  'chevron_left': Icons.chevron_left,
  'chevron_right': Icons.chevron_right,
  'chevron_right_rounded': Icons.chevron_right_rounded,
  'circle': Icons.circle,
  'clear': Icons.clear,
  'close': Icons.close,
  'close_rounded': Icons.close_rounded,
  'cloud_off_outlined': Icons.cloud_off_outlined,
  'color_lens_outlined': Icons.color_lens_outlined,
  'compare_arrows_outlined': Icons.compare_arrows_outlined,
  'compare_arrows_rounded': Icons.compare_arrows_rounded,
  'copy_outlined': Icons.copy_outlined,
  'dark_mode_outlined': Icons.dark_mode_outlined,
  'data_exploration_outlined': Icons.data_exploration_outlined,
  'description_outlined': Icons.description_outlined,
  'desktop_windows_outlined': Icons.desktop_windows_outlined,
  'download_outlined': Icons.download_outlined,
  'edit_note_rounded': Icons.edit_note_rounded,
  'event_busy_outlined': Icons.event_busy_outlined,
  'event_note_outlined': Icons.event_note_outlined,
  'expand_less': Icons.expand_less,
  'expand_more_rounded': Icons.expand_more_rounded,
  'extension_outlined': Icons.extension_outlined,
  'fact_check_outlined': Icons.fact_check_outlined,
  'file_download_outlined': Icons.file_download_outlined,
  'filter_alt_off_outlined': Icons.filter_alt_off_outlined,
  'filter_alt_outlined': Icons.filter_alt_outlined,
  'flag_outlined': Icons.flag_outlined,
  'folder_open_outlined': Icons.folder_open_outlined,
  'folder_outlined': Icons.folder_outlined,
  'forum_outlined': Icons.forum_outlined,
  'grid_view_rounded': Icons.grid_view_rounded,
  'help_outline': Icons.help_outline,
  'history': Icons.history,
  'history_rounded': Icons.history_rounded,
  'hourglass_empty_rounded': Icons.hourglass_empty_rounded,
  'hub_outlined': Icons.hub_outlined,
  'image_not_supported_outlined': Icons.image_not_supported_outlined,
  'image_outlined': Icons.image_outlined,
  'inbox_outlined': Icons.inbox_outlined,
  'info_outline': Icons.info_outline,
  'info_outline_rounded': Icons.info_outline_rounded,
  'insert_drive_file_outlined': Icons.insert_drive_file_outlined,
  'insights_outlined': Icons.insights_outlined,
  'inventory_2_outlined': Icons.inventory_2_outlined,
  'ios_share_rounded': Icons.ios_share_rounded,
  'keyboard_arrow_down_rounded': Icons.keyboard_arrow_down_rounded,
  'keyboard_arrow_up_rounded': Icons.keyboard_arrow_up_rounded,
  'language_rounded': Icons.language_rounded,
  'library_books_outlined': Icons.library_books_outlined,
  'light_mode_outlined': Icons.light_mode_outlined,
  'lightbulb_outline_rounded': Icons.lightbulb_outline_rounded,
  'link': Icons.link,
  'link_rounded': Icons.link_rounded,
  'local_offer_outlined': Icons.local_offer_outlined,
  'lock_outline': Icons.lock_outline,
  'lock_outline_rounded': Icons.lock_outline_rounded,
  'menu_rounded': Icons.menu_rounded,
  'mic_none_rounded': Icons.mic_none_rounded,
  'monitor_heart_outlined': Icons.monitor_heart_outlined,
  'mood_rounded': Icons.mood_rounded,
  'more_horiz_rounded': Icons.more_horiz_rounded,
  'movie_creation_outlined': Icons.movie_creation_outlined,
  'movie_outlined': Icons.movie_outlined,
  'music_note_outlined': Icons.music_note_outlined,
  'notifications_none_rounded': Icons.notifications_none_rounded,
  'open_in_full_rounded': Icons.open_in_full_rounded,
  'open_in_new_rounded': Icons.open_in_new_rounded,
  'outbox_outlined': Icons.outbox_outlined,
  'palette_outlined': Icons.palette_outlined,
  'pause_circle_outline_rounded': Icons.pause_circle_outline_rounded,
  'pause_rounded': Icons.pause_rounded,
  'picture_as_pdf_outlined': Icons.picture_as_pdf_outlined,
  'place_outlined': Icons.place_outlined,
  'play_arrow_rounded': Icons.play_arrow_rounded,
  'play_circle_outline': Icons.play_circle_outline,
  'play_circle_outline_rounded': Icons.play_circle_outline_rounded,
  'policy_outlined': Icons.policy_outlined,
  'public_rounded': Icons.public_rounded,
  'query_stats_outlined': Icons.query_stats_outlined,
  'query_stats_rounded': Icons.query_stats_rounded,
  'radar_rounded': Icons.radar_rounded,
  'radio_button_checked': Icons.radio_button_checked,
  'radio_button_checked_rounded': Icons.radio_button_checked_rounded,
  'radio_button_off': Icons.radio_button_off,
  'radio_button_unchecked': Icons.radio_button_unchecked,
  'radio_button_unchecked_rounded': Icons.radio_button_unchecked_rounded,
  'rate_review_outlined': Icons.rate_review_outlined,
  'refresh': Icons.refresh,
  'refresh_rounded': Icons.refresh_rounded,
  'remove_circle_outline': Icons.remove_circle_outline,
  'remove_rounded': Icons.remove_rounded,
  'replay_rounded': Icons.replay_rounded,
  'restart_alt_rounded': Icons.restart_alt_rounded,
  'route_outlined': Icons.route_outlined,
  'save_alt_outlined': Icons.save_alt_outlined,
  'schedule_outlined': Icons.schedule_outlined,
  'schedule_rounded': Icons.schedule_rounded,
  'school_outlined': Icons.school_outlined,
  'search': Icons.search,
  'search_rounded': Icons.search_rounded,
  'sell_outlined': Icons.sell_outlined,
  'shield_moon_outlined': Icons.shield_moon_outlined,
  'shield_outlined': Icons.shield_outlined,
  'slideshow_outlined': Icons.slideshow_outlined,
  'source_outlined': Icons.source_outlined,
  'space_dashboard_outlined': Icons.space_dashboard_outlined,
  'stop_circle_outlined': Icons.stop_circle_outlined,
  'storefront_outlined': Icons.storefront_outlined,
  'straighten_rounded': Icons.straighten_rounded,
  'sync_problem': Icons.sync_problem,
  'sync_problem_outlined': Icons.sync_problem_outlined,
  'table_chart_outlined': Icons.table_chart_outlined,
  'timeline_rounded': Icons.timeline_rounded,
  'trending_down_rounded': Icons.trending_down_rounded,
  'trending_flat_rounded': Icons.trending_flat_rounded,
  'trending_up_rounded': Icons.trending_up_rounded,
  'tune_rounded': Icons.tune_rounded,
  'undo': Icons.undo,
  'undo_rounded': Icons.undo_rounded,
  'verified_outlined': Icons.verified_outlined,
  'video_collection_outlined': Icons.video_collection_outlined,
  'video_library_outlined': Icons.video_library_outlined,
  'view_list_outlined': Icons.view_list_outlined,
  'view_list_rounded': Icons.view_list_rounded,
  'view_timeline_outlined': Icons.view_timeline_outlined,
  'visibility_off_outlined': Icons.visibility_off_outlined,
  'visibility_outlined': Icons.visibility_outlined,
  'volume_off_rounded': Icons.volume_off_rounded,
  'volume_up_rounded': Icons.volume_up_rounded,
  'warning_amber_rounded': Icons.warning_amber_rounded,
  'zoom_in_rounded': Icons.zoom_in_rounded,
};

@immutable
class LumenisIconGeometry {
  LumenisIconGeometry._({
    required List<Path> paths,
    required List<_LumenisCircle> circles,
    required List<_LumenisRoundedRect> rects,
    required List<_LumenisCircle> dots,
    required List<Path> fills,
  }) : _paths = List<Path>.unmodifiable(paths),
       _circles = List<_LumenisCircle>.unmodifiable(circles),
       _rects = List<_LumenisRoundedRect>.unmodifiable(rects),
       _dots = List<_LumenisCircle>.unmodifiable(dots),
       _fills = List<Path>.unmodifiable(fills);

  final List<Path> _paths;
  final List<_LumenisCircle> _circles;
  final List<_LumenisRoundedRect> _rects;
  final List<_LumenisCircle> _dots;
  final List<Path> _fills;

  bool get isNotEmpty =>
      _paths.isNotEmpty ||
      _circles.isNotEmpty ||
      _rects.isNotEmpty ||
      _dots.isNotEmpty ||
      _fills.isNotEmpty;

  void paint(Canvas canvas, Paint strokePaint, Paint fillPaint) {
    for (final path in _paths) {
      canvas.drawPath(path, strokePaint);
    }
    for (final circle in _circles) {
      canvas.drawCircle(circle.center, circle.radius, strokePaint);
    }
    for (final rect in _rects) {
      canvas.drawRRect(rect.shape, strokePaint);
    }
    for (final dot in _dots) {
      canvas.drawCircle(dot.center, dot.radius, fillPaint);
    }
    for (final path in _fills) {
      canvas.drawPath(path, fillPaint);
    }
  }
}

class _LumenisCircle {
  _LumenisCircle(double x, double y, this.radius) : center = Offset(x, y);

  final Offset center;
  final double radius;
}

class _LumenisRoundedRect {
  _LumenisRoundedRect(
    double x,
    double y,
    double width,
    double height,
    double radius,
  ) : shape = _makeShape(x, y, width, height, radius);

  static RRect _makeShape(
    double x,
    double y,
    double width,
    double height,
    double radius,
  ) => RRect.fromRectAndRadius(
    Rect.fromLTWH(x, y, width, height),
    Radius.circular(radius),
  );

  final RRect shape;
}

final Map<String, LumenisIconGeometry> lumenisIconGeometry =
    Map<String, LumenisIconGeometry>.unmodifiable(<String, LumenisIconGeometry>{
      'back': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(20, 12)
            ..lineTo(4, 12)
            ..lineTo(10, 6),
          Path()
            ..moveTo(4, 12)
            ..lineTo(10, 18),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'forward': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(4, 12)
            ..lineTo(20, 12)
            ..lineTo(14, 6),
          Path()
            ..moveTo(20, 12)
            ..lineTo(14, 18),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'outward': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(6, 18)
            ..lineTo(18, 6)
            ..lineTo(8, 6),
          Path()
            ..moveTo(18, 6)
            ..lineTo(18, 16),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'chevronLeft': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(14, 6)
            ..lineTo(8, 12)
            ..lineTo(14, 18),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'chevronRight': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(10, 6)
            ..lineTo(16, 12)
            ..lineTo(10, 18),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'chevronUp': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(6, 15)
            ..lineTo(12, 9)
            ..lineTo(18, 15),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'chevronDown': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(6, 9)
            ..lineTo(12, 15)
            ..lineTo(18, 9),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'plus': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(12, 5)
            ..lineTo(12, 19),
          Path()
            ..moveTo(5, 12)
            ..lineTo(19, 12),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'minus': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(5, 12)
            ..lineTo(19, 12),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'close': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(6, 6)
            ..lineTo(18, 18),
          Path()
            ..moveTo(18, 6)
            ..lineTo(6, 18),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'check': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(4.5, 12)
            ..lineTo(9.5, 17)
            ..lineTo(19.5, 6.5),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'checkCircle': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(7, 12)
            ..lineTo(10.5, 15.5)
            ..lineTo(17, 9),
        ],
        circles: <_LumenisCircle>[_LumenisCircle(12, 12, 9)],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'radio': LumenisIconGeometry._(
        paths: <Path>[],
        circles: <_LumenisCircle>[_LumenisCircle(12, 12, 8)],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'radioSelected': LumenisIconGeometry._(
        paths: <Path>[],
        circles: <_LumenisCircle>[_LumenisCircle(12, 12, 8)],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[_LumenisCircle(12, 12, 3.6)],
        fills: <Path>[],
      ),
      'circle': LumenisIconGeometry._(
        paths: <Path>[],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[_LumenisCircle(12, 12, 8)],
        fills: <Path>[],
      ),
      'removeCircle': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(8, 12)
            ..lineTo(16, 12),
        ],
        circles: <_LumenisCircle>[_LumenisCircle(12, 12, 9)],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'block': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(6, 18)
            ..lineTo(18, 6),
        ],
        circles: <_LumenisCircle>[_LumenisCircle(12, 12, 8.5)],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'menu': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(4, 6)
            ..lineTo(20, 6),
          Path()
            ..moveTo(4, 12)
            ..lineTo(16, 12),
          Path()
            ..moveTo(4, 18)
            ..lineTo(20, 18),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'more': LumenisIconGeometry._(
        paths: <Path>[],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[
          _LumenisCircle(5, 12, 1.2),
          _LumenisCircle(12, 12, 1.2),
          _LumenisCircle(19, 12, 1.2),
        ],
        fills: <Path>[],
      ),
      'search': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(15.5, 15.5)
            ..lineTo(21, 21),
        ],
        circles: <_LumenisCircle>[_LumenisCircle(10.5, 10.5, 6.5)],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'zoom': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(15.5, 15.5)
            ..lineTo(21, 21),
          Path()
            ..moveTo(7.5, 10.5)
            ..lineTo(13.5, 10.5),
          Path()
            ..moveTo(10.5, 7.5)
            ..lineTo(10.5, 13.5),
        ],
        circles: <_LumenisCircle>[_LumenisCircle(10.5, 10.5, 6.5)],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'info': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(12, 11)
            ..lineTo(12, 17),
        ],
        circles: <_LumenisCircle>[_LumenisCircle(12, 12, 9)],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[_LumenisCircle(12, 7.4, 0.9)],
        fills: <Path>[],
      ),
      'help': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(9, 9)
            ..cubicTo(9, 5.5, 15.5, 5.5, 15.5, 9)
            ..cubicTo(15.5, 11.5, 12, 11, 12, 14),
        ],
        circles: <_LumenisCircle>[_LumenisCircle(12, 12, 9)],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[_LumenisCircle(12, 17, 0.9)],
        fills: <Path>[],
      ),
      'warning': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(10.5, 4)
            ..quadraticBezierTo(12, 1.5, 13.5, 4)
            ..lineTo(21, 18)
            ..quadraticBezierTo(22.2, 20, 19.8, 20)
            ..lineTo(4.2, 20)
            ..quadraticBezierTo(1.8, 20, 3, 18)
            ..close(),
          Path()
            ..moveTo(12, 8)
            ..lineTo(12, 13),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[_LumenisCircle(12, 16.5, 0.9)],
        fills: <Path>[],
      ),
      'lock': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(7.5, 10)
            ..lineTo(7.5, 7.5)
            ..cubicTo(7.5, 1.5, 16.5, 1.5, 16.5, 7.5)
            ..lineTo(16.5, 10),
          Path()
            ..moveTo(12, 14)
            ..lineTo(12, 17),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[_LumenisRoundedRect(4, 10, 16, 11, 2)],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'shield': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(12, 3)
            ..lineTo(20, 6)
            ..lineTo(20, 12)
            ..cubicTo(20, 16, 16, 19.5, 12, 21)
            ..cubicTo(8, 19.5, 4, 16, 4, 12)
            ..lineTo(4, 6)
            ..close(),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'verified': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(12, 3)
            ..lineTo(20, 6)
            ..lineTo(20, 12)
            ..cubicTo(20, 16, 16, 19.5, 12, 21)
            ..cubicTo(8, 19.5, 4, 16, 4, 12)
            ..lineTo(4, 6)
            ..close(),
          Path()
            ..moveTo(8, 12)
            ..lineTo(11, 15)
            ..lineTo(16, 9),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'shieldNight': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(12, 3)
            ..lineTo(20, 6)
            ..lineTo(20, 12)
            ..cubicTo(20, 16, 16, 19.5, 12, 21)
            ..cubicTo(8, 19.5, 4, 16, 4, 12)
            ..lineTo(4, 6)
            ..close(),
          Path()
            ..moveTo(13.5, 7.5)
            ..cubicTo(8, 8, 8, 15.5, 14, 15.5)
            ..cubicTo(16, 15.5, 17, 14, 17, 13)
            ..cubicTo(12, 14, 11, 10, 13.5, 7.5)
            ..close(),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'history': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(4, 8)
            ..cubicTo(7, 1, 18, 2, 20, 9)
            ..cubicTo(23, 19, 9, 25, 4, 17),
          Path()
            ..moveTo(3, 4)
            ..lineTo(3, 9)
            ..lineTo(8, 9),
          Path()
            ..moveTo(12, 7)
            ..lineTo(12, 12)
            ..lineTo(16, 14),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'refresh': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(4, 9)
            ..cubicTo(6, 2, 16, 1, 20, 8),
          Path()
            ..moveTo(20, 3)
            ..lineTo(20, 8)
            ..lineTo(15, 8),
          Path()
            ..moveTo(20, 15)
            ..cubicTo(18, 22, 8, 23, 4, 16),
          Path()
            ..moveTo(4, 21)
            ..lineTo(4, 16)
            ..lineTo(9, 16),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'undo': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(8, 5)
            ..lineTo(3, 10)
            ..lineTo(8, 15),
          Path()
            ..moveTo(3, 10)
            ..lineTo(14, 10)
            ..cubicTo(21, 10, 23, 20, 14, 20),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'replay': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(7, 3)
            ..lineTo(3, 7)
            ..lineTo(7, 11),
          Path()
            ..moveTo(3, 7)
            ..lineTo(13, 7)
            ..cubicTo(23, 7, 23, 21, 13, 21)
            ..cubicTo(9, 21, 6, 19, 5, 16),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'clock': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(12, 6)
            ..lineTo(12, 12)
            ..lineTo(16, 14),
        ],
        circles: <_LumenisCircle>[_LumenisCircle(12, 12, 9)],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'hourglass': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(6, 3)
            ..lineTo(18, 3),
          Path()
            ..moveTo(6, 21)
            ..lineTo(18, 21),
          Path()
            ..moveTo(7, 3)
            ..lineTo(7, 7)
            ..lineTo(17, 17)
            ..lineTo(17, 21),
          Path()
            ..moveTo(17, 3)
            ..lineTo(17, 7)
            ..lineTo(7, 17)
            ..lineTo(7, 21),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'unavailable': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 7)
            ..cubicTo(7, 1, 16, 1, 20, 7),
          Path()
            ..moveTo(20, 3)
            ..lineTo(20, 7)
            ..lineTo(16, 7),
          Path()
            ..moveTo(21, 17)
            ..cubicTo(17, 23, 8, 23, 4, 17),
          Path()
            ..moveTo(4, 21)
            ..lineTo(4, 17)
            ..lineTo(8, 17),
          Path()
            ..moveTo(12, 8)
            ..lineTo(12, 12),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[_LumenisCircle(12, 15.5, 0.9)],
        fills: <Path>[],
      ),
      'download': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(12, 3)
            ..lineTo(12, 16)
            ..lineTo(7, 11),
          Path()
            ..moveTo(12, 16)
            ..lineTo(17, 11),
          Path()
            ..moveTo(4, 15)
            ..lineTo(4, 21)
            ..lineTo(20, 21)
            ..lineTo(20, 15),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'share': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(12, 16)
            ..lineTo(12, 3)
            ..lineTo(7, 8),
          Path()
            ..moveTo(12, 3)
            ..lineTo(17, 8),
          Path()
            ..moveTo(7, 11)
            ..lineTo(4, 11)
            ..lineTo(4, 21)
            ..lineTo(20, 21)
            ..lineTo(20, 11)
            ..lineTo(17, 11),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'open': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(15, 3)
            ..lineTo(21, 3)
            ..lineTo(21, 9),
          Path()
            ..moveTo(21, 3)
            ..lineTo(11, 13),
          Path()
            ..moveTo(11, 4)
            ..lineTo(4, 4)
            ..lineTo(4, 20)
            ..lineTo(20, 20)
            ..lineTo(20, 13),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'expand': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(4, 10)
            ..lineTo(4, 4)
            ..lineTo(10, 4),
          Path()
            ..moveTo(4, 4)
            ..lineTo(10, 10),
          Path()
            ..moveTo(20, 14)
            ..lineTo(20, 20)
            ..lineTo(14, 20),
          Path()
            ..moveTo(20, 20)
            ..lineTo(14, 14),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'copy': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(8, 5)
            ..lineTo(8, 3)
            ..lineTo(21, 3)
            ..lineTo(21, 16)
            ..lineTo(19, 16),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[_LumenisRoundedRect(3, 8, 13, 13, 1.5)],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'folder': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 6)
            ..quadraticBezierTo(3, 4, 5, 4)
            ..lineTo(10, 4)
            ..lineTo(12, 7)
            ..lineTo(19, 7)
            ..quadraticBezierTo(21, 7, 21, 9)
            ..lineTo(21, 19)
            ..quadraticBezierTo(21, 20, 20, 20)
            ..lineTo(4, 20)
            ..quadraticBezierTo(3, 20, 3, 19)
            ..close(),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'folderOpen': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 10)
            ..lineTo(3, 6)
            ..quadraticBezierTo(3, 4, 5, 4)
            ..lineTo(9, 4)
            ..lineTo(12, 7)
            ..lineTo(19, 7)
            ..lineTo(19, 10),
          Path()
            ..moveTo(3, 10)
            ..lineTo(22, 10)
            ..lineTo(19, 20)
            ..lineTo(4, 20)
            ..lineTo(3, 10)
            ..close(),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'file': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(6, 3)
            ..lineTo(14, 3)
            ..lineTo(20, 9)
            ..lineTo(20, 21)
            ..lineTo(6, 21)
            ..close(),
          Path()
            ..moveTo(14, 3)
            ..lineTo(14, 9)
            ..lineTo(20, 9),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'document': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(6, 3)
            ..lineTo(14, 3)
            ..lineTo(20, 9)
            ..lineTo(20, 21)
            ..lineTo(6, 21)
            ..close(),
          Path()
            ..moveTo(14, 3)
            ..lineTo(14, 9)
            ..lineTo(20, 9),
          Path()
            ..moveTo(9, 13)
            ..lineTo(16, 13),
          Path()
            ..moveTo(9, 17)
            ..lineTo(16, 17),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'article': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(7, 8)
            ..lineTo(11, 8)
            ..lineTo(11, 12)
            ..lineTo(7, 12)
            ..close(),
          Path()
            ..moveTo(15, 8)
            ..lineTo(18, 8),
          Path()
            ..moveTo(15, 12)
            ..lineTo(18, 12),
          Path()
            ..moveTo(7, 16)
            ..lineTo(18, 16),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[_LumenisRoundedRect(3, 3, 19, 18, 1.5)],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'clipboard': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(9, 4)
            ..lineTo(5, 4)
            ..lineTo(5, 21)
            ..lineTo(20, 21)
            ..lineTo(20, 4)
            ..lineTo(16, 4),
          Path()
            ..moveTo(9, 3)
            ..lineTo(16, 3)
            ..lineTo(16, 7)
            ..lineTo(9, 7)
            ..close(),
          Path()
            ..moveTo(9, 12)
            ..lineTo(16, 12),
          Path()
            ..moveTo(9, 16)
            ..lineTo(16, 16),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'checklist': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 6)
            ..lineTo(5, 8)
            ..lineTo(8, 4),
          Path()
            ..moveTo(12, 6)
            ..lineTo(21, 6),
          Path()
            ..moveTo(3, 13)
            ..lineTo(5, 15)
            ..lineTo(8, 11),
          Path()
            ..moveTo(12, 13)
            ..lineTo(21, 13),
          Path()
            ..moveTo(12, 20)
            ..lineTo(21, 20),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'factCheck': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(6, 8)
            ..lineTo(8, 10)
            ..lineTo(12, 6),
          Path()
            ..moveTo(15, 8)
            ..lineTo(18, 8),
          Path()
            ..moveTo(6, 16)
            ..lineTo(8, 18)
            ..lineTo(12, 14),
          Path()
            ..moveTo(15, 16)
            ..lineTo(18, 16),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[_LumenisRoundedRect(2, 2, 20, 20, 2)],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'table': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 9)
            ..lineTo(21, 9),
          Path()
            ..moveTo(3, 15)
            ..lineTo(21, 15),
          Path()
            ..moveTo(9, 3)
            ..lineTo(9, 21),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[_LumenisRoundedRect(3, 3, 18, 18, 1.5)],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'list': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(8, 5)
            ..lineTo(21, 5),
          Path()
            ..moveTo(8, 12)
            ..lineTo(21, 12),
          Path()
            ..moveTo(8, 19)
            ..lineTo(21, 19),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[
          _LumenisCircle(3, 5, 1),
          _LumenisCircle(3, 12, 1),
          _LumenisCircle(3, 19, 1),
        ],
        fills: <Path>[],
      ),
      'edit': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 5)
            ..lineTo(12, 5),
          Path()
            ..moveTo(3, 10)
            ..lineTo(10, 10),
          Path()
            ..moveTo(3, 15)
            ..lineTo(8, 15),
          Path()
            ..moveTo(11, 16)
            ..lineTo(18, 9)
            ..lineTo(21, 12)
            ..lineTo(14, 19)
            ..lineTo(10, 20)
            ..close(),
          Path()
            ..moveTo(17, 10)
            ..lineTo(20, 13),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'review': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(5, 3)
            ..lineTo(20, 3)
            ..lineTo(20, 17)
            ..lineTo(10, 17)
            ..lineTo(5, 21)
            ..close(),
          Path()
            ..moveTo(9, 13)
            ..lineTo(15, 7)
            ..lineTo(17, 9)
            ..lineTo(11, 15)
            ..lineTo(8, 16)
            ..close(),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'inbox': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 14)
            ..lineTo(6, 4)
            ..lineTo(18, 4)
            ..lineTo(21, 14)
            ..lineTo(21, 20)
            ..lineTo(3, 20)
            ..close(),
          Path()
            ..moveTo(3, 14)
            ..lineTo(8, 14)
            ..lineTo(10, 17)
            ..lineTo(14, 17)
            ..lineTo(16, 14)
            ..lineTo(21, 14),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'outbox': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 14)
            ..lineTo(3, 21)
            ..lineTo(21, 21)
            ..lineTo(21, 14),
          Path()
            ..moveTo(12, 16)
            ..lineTo(12, 3)
            ..lineTo(7, 8),
          Path()
            ..moveTo(12, 3)
            ..lineTo(17, 8),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'archive': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(5, 8)
            ..lineTo(5, 21)
            ..lineTo(19, 21)
            ..lineTo(19, 8),
          Path()
            ..moveTo(2, 3)
            ..lineTo(22, 3)
            ..lineTo(22, 8)
            ..lineTo(2, 8)
            ..close(),
          Path()
            ..moveTo(9, 12)
            ..lineTo(15, 12),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'source': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 6)
            ..quadraticBezierTo(3, 4, 5, 4)
            ..lineTo(10, 4)
            ..lineTo(12, 7)
            ..lineTo(21, 7)
            ..lineTo(21, 20)
            ..lineTo(3, 20)
            ..close(),
          Path()
            ..moveTo(7, 12)
            ..lineTo(17, 12),
          Path()
            ..moveTo(7, 16)
            ..lineTo(14, 16),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'pdf': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(5, 3)
            ..lineTo(14, 3)
            ..lineTo(20, 9)
            ..lineTo(20, 21)
            ..lineTo(5, 21)
            ..close(),
          Path()
            ..moveTo(14, 3)
            ..lineTo(14, 9)
            ..lineTo(20, 9),
          Path()
            ..moveTo(9, 18)
            ..lineTo(9, 12)
            ..lineTo(12, 12)
            ..cubicTo(16, 12, 16, 16, 12, 16)
            ..lineTo(9, 16),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'calendar': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(4, 8)
            ..lineTo(20, 8),
          Path()
            ..moveTo(8, 2)
            ..lineTo(8, 6),
          Path()
            ..moveTo(16, 2)
            ..lineTo(16, 6),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[_LumenisRoundedRect(4, 4, 16, 18, 1.5)],
        dots: <_LumenisCircle>[
          _LumenisCircle(8, 12, 0.8),
          _LumenisCircle(12, 12, 0.8),
          _LumenisCircle(16, 12, 0.8),
          _LumenisCircle(8, 17, 0.8),
          _LumenisCircle(12, 17, 0.8),
        ],
        fills: <Path>[],
      ),
      'eventNote': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(4, 8)
            ..lineTo(20, 8),
          Path()
            ..moveTo(8, 2)
            ..lineTo(8, 6),
          Path()
            ..moveTo(16, 2)
            ..lineTo(16, 6),
          Path()
            ..moveTo(8, 12)
            ..lineTo(16, 12),
          Path()
            ..moveTo(8, 17)
            ..lineTo(13, 17),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[_LumenisRoundedRect(4, 4, 16, 18, 1.5)],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'eventOff': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(4, 8)
            ..lineTo(20, 8),
          Path()
            ..moveTo(8, 2)
            ..lineTo(8, 6),
          Path()
            ..moveTo(16, 2)
            ..lineTo(16, 6),
          Path()
            ..moveTo(9, 12)
            ..lineTo(15, 18),
          Path()
            ..moveTo(15, 12)
            ..lineTo(9, 18),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[_LumenisRoundedRect(4, 4, 16, 18, 1.5)],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'flag': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(5, 22)
            ..lineTo(5, 3),
          Path()
            ..moveTo(5, 4)
            ..cubicTo(10, 0, 14, 8, 21, 4)
            ..lineTo(21, 15)
            ..cubicTo(14, 19, 10, 11, 5, 15),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'tag': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 3)
            ..lineTo(12, 3)
            ..lineTo(22, 13)
            ..lineTo(13, 22)
            ..lineTo(3, 12)
            ..close(),
        ],
        circles: <_LumenisCircle>[_LumenisCircle(8, 8, 1.2)],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'link': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(8, 15)
            ..lineTo(15, 8),
          Path()
            ..moveTo(7, 10)
            ..lineTo(4, 13)
            ..cubicTo(0, 17, 7, 24, 11, 20)
            ..lineTo(14, 17),
          Path()
            ..moveTo(10, 7)
            ..lineTo(13, 4)
            ..cubicTo(17, 0, 24, 7, 20, 11)
            ..lineTo(17, 14),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'compare': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 7)
            ..lineTo(21, 7)
            ..lineTo(17, 3),
          Path()
            ..moveTo(21, 7)
            ..lineTo(17, 11),
          Path()
            ..moveTo(21, 17)
            ..lineTo(3, 17)
            ..lineTo(7, 13),
          Path()
            ..moveTo(3, 17)
            ..lineTo(7, 21),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'filter': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 4)
            ..lineTo(21, 4)
            ..lineTo(14, 12)
            ..lineTo(14, 20)
            ..lineTo(10, 18)
            ..lineTo(10, 12)
            ..close(),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'filterOff': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(9, 4)
            ..lineTo(21, 4)
            ..lineTo(16, 10),
          Path()
            ..moveTo(3, 4)
            ..lineTo(10, 12)
            ..lineTo(10, 18)
            ..lineTo(14, 20)
            ..lineTo(14, 15),
          Path()
            ..moveTo(3, 3)
            ..lineTo(21, 21),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'tune': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 6)
            ..lineTo(8, 6),
          Path()
            ..moveTo(12, 6)
            ..lineTo(21, 6),
          Path()
            ..moveTo(3, 12)
            ..lineTo(14, 12),
          Path()
            ..moveTo(18, 12)
            ..lineTo(21, 12),
          Path()
            ..moveTo(3, 18)
            ..lineTo(5, 18),
          Path()
            ..moveTo(9, 18)
            ..lineTo(21, 18),
        ],
        circles: <_LumenisCircle>[
          _LumenisCircle(10, 6, 2),
          _LumenisCircle(16, 12, 2),
          _LumenisCircle(7, 18, 2),
        ],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'focus': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 9)
            ..lineTo(3, 3)
            ..lineTo(9, 3),
          Path()
            ..moveTo(15, 3)
            ..lineTo(21, 3)
            ..lineTo(21, 9),
          Path()
            ..moveTo(21, 15)
            ..lineTo(21, 21)
            ..lineTo(15, 21),
          Path()
            ..moveTo(9, 21)
            ..lineTo(3, 21)
            ..lineTo(3, 15),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[_LumenisCircle(12, 12, 1.6)],
        fills: <Path>[],
      ),
      'intent': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(4, 10)
            ..lineTo(4, 4)
            ..lineTo(10, 4),
          Path()
            ..moveTo(14, 4)
            ..lineTo(20, 4)
            ..lineTo(20, 10),
          Path()
            ..moveTo(20, 14)
            ..lineTo(20, 20)
            ..lineTo(14, 20),
          Path()
            ..moveTo(10, 20)
            ..lineTo(4, 20)
            ..lineTo(4, 14),
          Path()
            ..moveTo(8, 14)
            ..lineTo(12, 10)
            ..lineTo(16, 12),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[_LumenisCircle(12, 10, 1.2)],
        fills: <Path>[],
      ),
      'hub': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(12, 6)
            ..lineTo(12, 10),
          Path()
            ..moveTo(6, 17)
            ..lineTo(10, 13),
          Path()
            ..moveTo(18, 17)
            ..lineTo(14, 13),
        ],
        circles: <_LumenisCircle>[
          _LumenisCircle(12, 3.5, 2.5),
          _LumenisCircle(12, 12, 2.5),
          _LumenisCircle(4.5, 19, 2.5),
          _LumenisCircle(19.5, 19, 2.5),
        ],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'tree': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(12, 7)
            ..lineTo(12, 11)
            ..lineTo(5, 11)
            ..lineTo(5, 16),
          Path()
            ..moveTo(12, 11)
            ..lineTo(19, 11)
            ..lineTo(19, 16),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[
          _LumenisRoundedRect(9, 2, 6, 5, 1),
          _LumenisRoundedRect(2, 16, 6, 5, 1),
          _LumenisRoundedRect(16, 16, 6, 5, 1),
        ],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'route': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(6, 6)
            ..lineTo(17, 6)
            ..cubicTo(22, 6, 22, 12, 17, 12)
            ..lineTo(7, 12)
            ..cubicTo(2, 12, 2, 18, 7, 18)
            ..lineTo(18, 18),
        ],
        circles: <_LumenisCircle>[
          _LumenisCircle(4, 6, 2),
          _LumenisCircle(20, 18, 2),
        ],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'alternative': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(6, 21)
            ..lineTo(6, 14)
            ..lineTo(18, 3),
          Path()
            ..moveTo(13, 3)
            ..lineTo(18, 3)
            ..lineTo(18, 8),
          Path()
            ..moveTo(6, 14)
            ..lineTo(6, 3),
          Path()
            ..moveTo(3, 6)
            ..lineTo(6, 3)
            ..lineTo(9, 6),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'trendUp': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 18)
            ..lineTo(9, 12)
            ..lineTo(13, 15)
            ..lineTo(21, 6),
          Path()
            ..moveTo(15, 6)
            ..lineTo(21, 6)
            ..lineTo(21, 12),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'trendDown': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 6)
            ..lineTo(9, 12)
            ..lineTo(13, 9)
            ..lineTo(21, 18),
          Path()
            ..moveTo(15, 18)
            ..lineTo(21, 18)
            ..lineTo(21, 12),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'trendFlat': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 12)
            ..lineTo(21, 12)
            ..lineTo(16, 7),
          Path()
            ..moveTo(21, 12)
            ..lineTo(16, 17),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'timeline': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 18)
            ..lineTo(8, 9)
            ..lineTo(14, 13)
            ..lineTo(21, 4),
        ],
        circles: <_LumenisCircle>[
          _LumenisCircle(3, 18, 1.3),
          _LumenisCircle(8, 9, 1.3),
          _LumenisCircle(14, 13, 1.3),
          _LumenisCircle(21, 4, 1.3),
        ],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'insights': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 20)
            ..lineTo(21, 20),
          Path()
            ..moveTo(6, 16)
            ..lineTo(6, 11),
          Path()
            ..moveTo(11, 16)
            ..lineTo(11, 7),
          Path()
            ..moveTo(16, 16)
            ..lineTo(16, 3),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'query': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 18)
            ..lineTo(3, 12),
          Path()
            ..moveTo(7, 18)
            ..lineTo(7, 8),
          Path()
            ..moveTo(11, 18)
            ..lineTo(11, 4),
          Path()
            ..moveTo(19, 17)
            ..lineTo(22, 20),
        ],
        circles: <_LumenisCircle>[_LumenisCircle(17, 14, 4)],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'radar': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(12, 12)
            ..lineTo(19, 5),
          Path()
            ..moveTo(12, 3)
            ..lineTo(12, 5),
          Path()
            ..moveTo(21, 12)
            ..lineTo(19, 12),
          Path()
            ..moveTo(12, 21)
            ..lineTo(12, 19),
          Path()
            ..moveTo(3, 12)
            ..lineTo(5, 12),
        ],
        circles: <_LumenisCircle>[
          _LumenisCircle(12, 12, 9),
          _LumenisCircle(12, 12, 5),
        ],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[_LumenisCircle(12, 12, 1)],
        fills: <Path>[],
      ),
      'store': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(4, 10)
            ..lineTo(4, 21)
            ..lineTo(20, 21)
            ..lineTo(20, 10),
          Path()
            ..moveTo(3, 10)
            ..lineTo(5, 3)
            ..lineTo(19, 3)
            ..lineTo(21, 10),
          Path()
            ..moveTo(3, 10)
            ..quadraticBezierTo(6, 13, 9, 10)
            ..quadraticBezierTo(12, 13, 15, 10)
            ..quadraticBezierTo(18, 13, 21, 10),
          Path()
            ..moveTo(9, 21)
            ..lineTo(9, 15)
            ..lineTo(15, 15)
            ..lineTo(15, 21),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'building': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(4, 21)
            ..lineTo(4, 3)
            ..lineTo(15, 3)
            ..lineTo(15, 21),
          Path()
            ..moveTo(15, 10)
            ..lineTo(21, 10)
            ..lineTo(21, 21),
          Path()
            ..moveTo(8, 7)
            ..lineTo(11, 7),
          Path()
            ..moveTo(8, 11)
            ..lineTo(11, 11),
          Path()
            ..moveTo(8, 15)
            ..lineTo(11, 15),
          Path()
            ..moveTo(3, 21)
            ..lineTo(22, 21),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'place': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(12, 22)
            ..cubicTo(9, 18, 4, 13, 4, 9)
            ..cubicTo(4, -1, 20, -1, 20, 9)
            ..cubicTo(20, 13, 15, 18, 12, 22)
            ..close(),
        ],
        circles: <_LumenisCircle>[_LumenisCircle(12, 9, 2.6)],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'globe': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 12)
            ..lineTo(21, 12),
          Path()
            ..moveTo(12, 3)
            ..cubicTo(5, 8, 5, 16, 12, 21)
            ..cubicTo(19, 16, 19, 8, 12, 3)
            ..close(),
        ],
        circles: <_LumenisCircle>[_LumenisCircle(12, 12, 9)],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'language': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 5)
            ..lineTo(15, 5),
          Path()
            ..moveTo(9, 2)
            ..lineTo(9, 5),
          Path()
            ..moveTo(12, 5)
            ..cubicTo(11, 11, 7, 14, 3, 16),
          Path()
            ..moveTo(5, 8)
            ..cubicTo(7, 12, 10, 15, 14, 16),
          Path()
            ..moveTo(14, 21)
            ..lineTo(18, 11)
            ..lineTo(22, 21),
          Path()
            ..moveTo(15.5, 17.5)
            ..lineTo(20.5, 17.5),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'layout': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(10, 3)
            ..lineTo(10, 21),
          Path()
            ..moveTo(10, 11)
            ..lineTo(21, 11),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[_LumenisRoundedRect(3, 3, 18, 18, 2)],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'desktop': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(12, 17)
            ..lineTo(12, 21),
          Path()
            ..moveTo(7, 21)
            ..lineTo(17, 21),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[_LumenisRoundedRect(2, 3, 20, 14, 1.5)],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'brand': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 6)
            ..lineTo(21, 6)
            ..lineTo(21, 20)
            ..lineTo(3, 20)
            ..close(),
          Path()
            ..moveTo(14, 14)
            ..lineTo(21, 14),
          Path()
            ..moveTo(14, 14)
            ..lineTo(14, 20),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[_LumenisCircle(7, 10, 1)],
        fills: <Path>[],
      ),
      'extension': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 3)
            ..lineTo(8, 3)
            ..cubicTo(8, 8, 15, 8, 15, 3)
            ..lineTo(21, 3)
            ..lineTo(21, 9)
            ..cubicTo(16, 9, 16, 16, 21, 16)
            ..lineTo(21, 21)
            ..lineTo(15, 21)
            ..cubicTo(15, 16, 8, 16, 8, 21)
            ..lineTo(3, 21)
            ..lineTo(3, 16)
            ..cubicTo(8, 16, 8, 9, 3, 9)
            ..close(),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'forum': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 3)
            ..lineTo(18, 3)
            ..lineTo(18, 13)
            ..lineTo(8, 13)
            ..lineTo(3, 17)
            ..close(),
          Path()
            ..moveTo(9, 17)
            ..lineTo(16, 17)
            ..lineTo(21, 21)
            ..lineTo(21, 7),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'notification': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(4, 17)
            ..lineTo(20, 17)
            ..lineTo(18, 14)
            ..lineTo(18, 9)
            ..cubicTo(18, 1, 6, 1, 6, 9)
            ..lineTo(6, 14)
            ..close(),
          Path()
            ..moveTo(9, 21)
            ..lineTo(15, 21),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'lightbulb': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(9, 18)
            ..cubicTo(9, 14, 5, 14, 5, 9)
            ..cubicTo(5, 0, 19, 0, 19, 9)
            ..cubicTo(19, 14, 15, 14, 15, 18)
            ..close(),
          Path()
            ..moveTo(10, 21)
            ..lineTo(14, 21),
          Path()
            ..moveTo(12, 18)
            ..lineTo(12, 10),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'school': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(2, 8)
            ..lineTo(12, 3)
            ..lineTo(22, 8)
            ..lineTo(12, 13)
            ..close(),
          Path()
            ..moveTo(6, 10)
            ..lineTo(6, 17)
            ..quadraticBezierTo(12, 22, 18, 17)
            ..lineTo(18, 10),
          Path()
            ..moveTo(22, 8)
            ..lineTo(22, 17),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'mood': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(7, 14)
            ..quadraticBezierTo(12, 20, 17, 14),
        ],
        circles: <_LumenisCircle>[_LumenisCircle(12, 12, 9)],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[
          _LumenisCircle(8, 9, 1),
          _LumenisCircle(16, 9, 1),
        ],
        fills: <Path>[],
      ),
      'sun': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(12, 1)
            ..lineTo(12, 3),
          Path()
            ..moveTo(12, 21)
            ..lineTo(12, 23),
          Path()
            ..moveTo(1, 12)
            ..lineTo(3, 12),
          Path()
            ..moveTo(21, 12)
            ..lineTo(23, 12),
          Path()
            ..moveTo(4, 4)
            ..lineTo(5.5, 5.5),
          Path()
            ..moveTo(18.5, 18.5)
            ..lineTo(20, 20),
          Path()
            ..moveTo(4, 20)
            ..lineTo(5.5, 18.5),
          Path()
            ..moveTo(18.5, 5.5)
            ..lineTo(20, 4),
        ],
        circles: <_LumenisCircle>[_LumenisCircle(12, 12, 5.5)],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'moon': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(19, 16)
            ..cubicTo(7, 20, 4, 7, 10, 3)
            ..cubicTo(0, 5, 0, 20, 11, 21)
            ..cubicTo(16, 21, 19, 18, 19, 16)
            ..close(),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'palette': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(12, 3)
            ..cubicTo(0, 3, 0, 21, 11, 21)
            ..cubicTo(16, 21, 10, 15, 16, 15)
            ..lineTo(19, 15)
            ..cubicTo(24, 15, 23, 3, 12, 3)
            ..close(),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[
          _LumenisCircle(7, 8, 1),
          _LumenisCircle(12, 6, 1),
          _LumenisCircle(17, 8, 1),
          _LumenisCircle(6, 13, 1),
        ],
        fills: <Path>[],
      ),
      'blur': LumenisIconGeometry._(
        paths: <Path>[],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[
          _LumenisCircle(12, 12, 1.8),
          _LumenisCircle(12, 5, 1.1),
          _LumenisCircle(5, 12, 1.1),
          _LumenisCircle(19, 12, 1.1),
          _LumenisCircle(12, 19, 1.1),
          _LumenisCircle(5, 5, 0.65),
          _LumenisCircle(19, 5, 0.65),
          _LumenisCircle(5, 19, 0.65),
          _LumenisCircle(19, 19, 0.65),
        ],
        fills: <Path>[],
      ),
      'image': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 17)
            ..lineTo(8, 12)
            ..lineTo(13, 17)
            ..lineTo(17, 13)
            ..lineTo(21, 17),
        ],
        circles: <_LumenisCircle>[_LumenisCircle(15.5, 7.5, 1.5)],
        rects: <_LumenisRoundedRect>[_LumenisRoundedRect(3, 3, 18, 18, 1.5)],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'imageAdd': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 9)
            ..lineTo(3, 21)
            ..lineTo(21, 21)
            ..lineTo(21, 12),
          Path()
            ..moveTo(3, 17)
            ..lineTo(8, 12)
            ..lineTo(16, 20),
          Path()
            ..moveTo(17, 2)
            ..lineTo(17, 10),
          Path()
            ..moveTo(13, 6)
            ..lineTo(21, 6),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'imageOff': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 9)
            ..lineTo(3, 21)
            ..lineTo(21, 21)
            ..lineTo(21, 18),
          Path()
            ..moveTo(9, 3)
            ..lineTo(21, 3)
            ..lineTo(21, 15),
          Path()
            ..moveTo(3, 17)
            ..lineTo(8, 12)
            ..lineTo(13, 17),
          Path()
            ..moveTo(2, 2)
            ..lineTo(22, 22),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'photos': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 8)
            ..lineTo(3, 22)
            ..lineTo(17, 22),
          Path()
            ..moveTo(7, 15)
            ..lineTo(12, 10)
            ..lineTo(20, 18),
        ],
        circles: <_LumenisCircle>[_LumenisCircle(17, 6.5, 1.2)],
        rects: <_LumenisRoundedRect>[_LumenisRoundedRect(7, 2, 15, 16, 1.5)],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'photosAdd': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 8)
            ..lineTo(3, 22)
            ..lineTo(17, 22),
          Path()
            ..moveTo(11, 10)
            ..lineTo(19, 10),
          Path()
            ..moveTo(15, 6)
            ..lineTo(15, 14),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[_LumenisRoundedRect(7, 2, 15, 16, 1.5)],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'movie': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 9)
            ..lineTo(21, 9),
          Path()
            ..moveTo(3, 4)
            ..lineTo(7, 9),
          Path()
            ..moveTo(10, 4)
            ..lineTo(14, 9),
          Path()
            ..moveTo(17, 4)
            ..lineTo(21, 9),
          Path()
            ..moveTo(10, 13)
            ..lineTo(16, 16)
            ..lineTo(10, 19)
            ..close(),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[_LumenisRoundedRect(3, 4, 18, 17, 1.5)],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'videoLibrary': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 8)
            ..lineTo(3, 22)
            ..lineTo(18, 22),
          Path()
            ..moveTo(12, 7)
            ..lineTo(18, 10)
            ..lineTo(12, 13)
            ..close(),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[_LumenisRoundedRect(7, 2, 15, 16, 1.5)],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'slideshow': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(10, 7)
            ..lineTo(16, 11)
            ..lineTo(10, 15)
            ..close(),
          Path()
            ..moveTo(12, 18)
            ..lineTo(12, 22),
          Path()
            ..moveTo(7, 22)
            ..lineTo(17, 22),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[_LumenisRoundedRect(2, 2, 20, 16, 1.5)],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'audioFile': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(5, 3)
            ..lineTo(14, 3)
            ..lineTo(20, 9)
            ..lineTo(20, 21)
            ..lineTo(5, 21)
            ..close(),
          Path()
            ..moveTo(14, 3)
            ..lineTo(14, 9)
            ..lineTo(20, 9),
          Path()
            ..moveTo(9, 15)
            ..lineTo(9, 17),
          Path()
            ..moveTo(12, 12)
            ..lineTo(12, 18),
          Path()
            ..moveTo(15, 14)
            ..lineTo(15, 17),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'music': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(10, 17)
            ..lineTo(10, 5)
            ..lineTo(20, 3)
            ..lineTo(20, 15),
          Path()
            ..moveTo(10, 9)
            ..lineTo(20, 7),
        ],
        circles: <_LumenisCircle>[
          _LumenisCircle(7, 18, 3),
          _LumenisCircle(17, 16, 3),
        ],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'microphone': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(5, 10)
            ..lineTo(5, 12)
            ..cubicTo(5, 21, 19, 21, 19, 12)
            ..lineTo(19, 10),
          Path()
            ..moveTo(12, 19)
            ..lineTo(12, 23),
          Path()
            ..moveTo(8, 23)
            ..lineTo(16, 23),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[_LumenisRoundedRect(9, 1, 6, 15, 3)],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'volume': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 9)
            ..lineTo(7, 9)
            ..lineTo(12, 4)
            ..lineTo(12, 20)
            ..lineTo(7, 15)
            ..lineTo(3, 15)
            ..close(),
          Path()
            ..moveTo(16, 8)
            ..cubicTo(20, 11, 20, 13, 16, 16),
          Path()
            ..moveTo(18, 4)
            ..cubicTo(24, 9, 24, 15, 18, 20),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'volumeOff': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 9)
            ..lineTo(7, 9)
            ..lineTo(12, 4)
            ..lineTo(12, 20)
            ..lineTo(7, 15)
            ..lineTo(3, 15)
            ..close(),
          Path()
            ..moveTo(16, 9)
            ..lineTo(22, 15),
          Path()
            ..moveTo(22, 9)
            ..lineTo(16, 15),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'play': LumenisIconGeometry._(
        paths: <Path>[],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[
          Path()
            ..moveTo(7, 3)
            ..lineTo(21, 12)
            ..lineTo(7, 21)
            ..close(),
        ],
      ),
      'playCircle': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(10, 7)
            ..lineTo(17, 12)
            ..lineTo(10, 17)
            ..close(),
        ],
        circles: <_LumenisCircle>[_LumenisCircle(12, 12, 9)],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'pause': LumenisIconGeometry._(
        paths: <Path>[],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[
          _LumenisRoundedRect(6, 4, 3, 16, 0.7),
          _LumenisRoundedRect(15, 4, 3, 16, 0.7),
        ],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'pauseCircle': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(9, 8)
            ..lineTo(9, 16),
          Path()
            ..moveTo(15, 8)
            ..lineTo(15, 16),
        ],
        circles: <_LumenisCircle>[_LumenisCircle(12, 12, 9)],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'stopCircle': LumenisIconGeometry._(
        paths: <Path>[],
        circles: <_LumenisCircle>[_LumenisCircle(12, 12, 9)],
        rects: <_LumenisRoundedRect>[_LumenisRoundedRect(8, 8, 8, 8, 1)],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'tracks': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 7)
            ..lineTo(6, 7),
          Path()
            ..moveTo(14, 7)
            ..lineTo(21, 7),
          Path()
            ..moveTo(3, 16)
            ..lineTo(11, 16),
          Path()
            ..moveTo(19, 16)
            ..lineTo(21, 16),
          Path()
            ..moveTo(9, 2)
            ..lineTo(9, 22),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[
          _LumenisRoundedRect(6, 5, 8, 4, 0.6),
          _LumenisRoundedRect(11, 14, 8, 4, 0.6),
        ],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'ruler': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(6, 9)
            ..lineTo(6, 12),
          Path()
            ..moveTo(10, 9)
            ..lineTo(10, 14),
          Path()
            ..moveTo(14, 9)
            ..lineTo(14, 12),
          Path()
            ..moveTo(18, 9)
            ..lineTo(18, 14),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[_LumenisRoundedRect(2, 7, 20, 10, 1)],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'eye': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(1, 12)
            ..quadraticBezierTo(12, -2, 23, 12)
            ..quadraticBezierTo(12, 26, 1, 12)
            ..close(),
        ],
        circles: <_LumenisCircle>[_LumenisCircle(12, 12, 3.2)],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'eyeOff': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 3)
            ..lineTo(21, 21),
          Path()
            ..moveTo(2, 12)
            ..quadraticBezierTo(6, 6, 10, 5),
          Path()
            ..moveTo(14, 5)
            ..quadraticBezierTo(19, 7, 22, 12)
            ..quadraticBezierTo(19, 17, 16, 18),
          Path()
            ..moveTo(12, 19)
            ..quadraticBezierTo(6, 18, 2, 12),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'monitor': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 12)
            ..lineTo(7, 12)
            ..lineTo(10, 7)
            ..lineTo(14, 17)
            ..lineTo(17, 12)
            ..lineTo(21, 12),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[_LumenisRoundedRect(2, 3, 20, 18, 2)],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
      'cloudOff': LumenisIconGeometry._(
        paths: <Path>[
          Path()
            ..moveTo(3, 3)
            ..lineTo(21, 21),
          Path()
            ..moveTo(5, 17)
            ..cubicTo(0, 17, 1, 9, 7, 9),
          Path()
            ..moveTo(8, 6)
            ..cubicTo(13, -1, 19, 5, 18, 10)
            ..cubicTo(24, 10, 24, 17, 19, 17),
        ],
        circles: <_LumenisCircle>[],
        rects: <_LumenisRoundedRect>[],
        dots: <_LumenisCircle>[],
        fills: <Path>[],
      ),
    });
