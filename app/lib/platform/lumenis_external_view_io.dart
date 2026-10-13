import 'dart:io';

/// Optional user-chosen "view original" jump in the system browser.
/// It only displays a public http(s) page; collection never runs here.
Future<bool> openLumenisExternalView(Uri url) async {
  if (url.scheme != 'https' && url.scheme != 'http') return false;
  final target = url.toString();
  try {
    final ProcessResult result;
    if (Platform.isWindows) {
      result = await Process.run('rundll32', [
        'url.dll,FileProtocolHandler',
        target,
      ]);
    } else if (Platform.isMacOS) {
      result = await Process.run('open', [target]);
    } else if (Platform.isLinux) {
      result = await Process.run('xdg-open', [target]);
    } else {
      return false;
    }
    return result.exitCode == 0;
  } on Object {
    return false;
  }
}
