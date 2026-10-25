import 'package:web/web.dart' as web;

import '../../../core/lumenis_core_client.dart';

Future<bool> save(ContentProjectFile file) async {
  final uri = file.streamUri!;
  if (!{'http', 'https'}.contains(uri.scheme) || uri.userInfo.isNotEmpty) {
    throw const FormatException('Invalid download location.');
  }
  final link = web.HTMLAnchorElement()
    ..href = uri.toString()
    ..download = file.filename
    ..rel = 'noopener'
    ..referrerPolicy = 'no-referrer';
  web.document.body!.appendChild(link);
  try {
    link.click();
  } finally {
    link.remove();
  }
  return true;
}
