import 'package:flutter/widgets.dart';

String sourceLabel(BuildContext context, String source) {
  final labels = switch (source.toLowerCase()) {
    'public_http' => ('网页', 'Web page', '웹페이지'),
    'web_rss' || 'rss' => ('订阅', 'RSS feed', 'RSS 구독'),
    'web_atom' || 'atom' => ('订阅', 'Atom feed', 'Atom 구독'),
    'sitemap' => ('网站目录', 'Site directory', '사이트 목록'),
    'google' || 'google_news' => ('Google', 'Google', 'Google'),
    'wechat' => ('微信公众号', 'WeChat', '위챗'),
    'xiaohongshu' || 'xhs' => ('小红书', 'RedNote', '샤오홍슈'),
    'douyin' => ('抖音', 'Douyin', '더우인'),
    'bilibili' => ('哔哩哔哩', 'Bilibili', '빌리빌리'),
    'kuaishou' => ('快手', 'Kuaishou', '콰이쇼우'),
    'channels' => ('视频号', 'WeChat Channels', '위챗 채널'),
    'zhihu' => ('知乎', 'Zhihu', '즈후'),
    'tieba' => ('百度贴吧', 'Baidu Tieba', '바이두 티에바'),
    'weibo' => ('微博', 'Weibo', '웨이보'),
    'instagram' => ('Instagram', 'Instagram', 'Instagram'),
    'facebook' => ('Facebook', 'Facebook', 'Facebook'),
    'x' || 'x_platform' || 'twitter' => ('X', 'X', 'X'),
    'youtube' => ('YouTube', 'YouTube', 'YouTube'),
    'tiktok' => ('TikTok', 'TikTok', 'TikTok'),
    'reddit' => ('Reddit', 'Reddit', 'Reddit'),
    'linkedin' => ('LinkedIn', 'LinkedIn', 'LinkedIn'),
    'github' => ('GitHub', 'GitHub', 'GitHub'),
    'naver' => ('Naver', 'Naver', '네이버'),
    'daum' => ('Daum', 'Daum', '다음'),
    _ => (source, source, source),
  };
  return switch (Localizations.localeOf(context).languageCode) {
    'en' => labels.$2,
    'ko' => labels.$3,
    _ => labels.$1,
  };
}
