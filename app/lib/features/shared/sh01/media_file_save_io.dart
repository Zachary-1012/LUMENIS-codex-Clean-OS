import 'dart:io';

import 'package:file_selector/file_selector.dart';

import '../../../core/lumenis_core_client.dart';

Future<bool> save(ContentProjectFile file) async {
  final location = await getSaveLocation(suggestedName: file.filename);
  if (location == null) return false;
  final target = File(location.path);
  final directory = await target.parent.createTemp('.oevira-download-');
  final partial = File(
    '${directory.path}${Platform.pathSeparator}download.part',
  );
  final client = HttpClient()..connectionTimeout = const Duration(seconds: 20);
  IOSink? sink;
  try {
    final outgoing = await client.getUrl(file.streamUri!);
    outgoing.followRedirects = false;
    outgoing.headers.set(HttpHeaders.acceptHeader, file.mediaType);
    final response = await outgoing.close();
    if (response.statusCode != HttpStatus.ok ||
        response.headers.contentType?.mimeType != file.mediaType ||
        response.contentLength <= 0) {
      throw const FormatException('Download was not returned.');
    }
    sink = partial.openWrite();
    var written = 0;
    await for (final chunk in response.timeout(const Duration(minutes: 2))) {
      written += chunk.length;
      if (written > response.contentLength) {
        throw const FormatException('Download length changed.');
      }
      sink.add(chunk);
      await sink.flush();
    }
    await sink.close();
    sink = null;
    if (written != response.contentLength) {
      throw const FormatException('Download was interrupted.');
    }
    await partial.rename(target.path);
    return true;
  } finally {
    client.close(force: true);
    await sink?.close();
    if (await partial.exists()) await partial.delete();
    await directory.delete();
  }
}
