import 'dart:convert';
import 'dart:io';

Future<void> main(List<String> args) async {
  if (!Platform.isWindows ||
      args.length != 3 ||
      args[0] != '--hold-lease' ||
      !RegExp(r'^[0-9a-f]+-[0-9a-f]+$').hasMatch(args[2])) {
    stderr.writeln('Invalid isolated lease-helper request.');
    exitCode = 64;
    return;
  }

  try {
    final root = Directory(args[1]).absolute;
    if (await FileSystemEntity.type(root.path, followLinks: false) !=
        FileSystemEntityType.directory) {
      stderr.writeln('The isolated lease root is not a directory.');
      exitCode = 65;
      return;
    }
    final canonicalRoot = await root.resolveSymbolicLinks();
    if (!_samePath(canonicalRoot, root.path)) {
      stderr.writeln('The isolated lease root did not resolve canonically.');
      exitCode = 66;
      return;
    }

    final directory = Directory(
      '${root.path}${Platform.pathSeparator}lease-${args[2]}',
    );
    if (!_samePath(FileSystemEntity.parentOf(directory.path), canonicalRoot) ||
        await FileSystemEntity.type(directory.path, followLinks: false) !=
            FileSystemEntityType.notFound) {
      stderr.writeln('The isolated lease child path was not available.');
      exitCode = 67;
      return;
    }
    await directory.create(recursive: false);
    final canonicalDirectory = await directory.resolveSymbolicLinks();
    if (!_samePath(canonicalDirectory, directory.path) ||
        !_samePath(
          FileSystemEntity.parentOf(canonicalDirectory),
          canonicalRoot,
        )) {
      stderr.writeln('The isolated lease child path failed verification.');
      exitCode = 68;
      return;
    }

    const markerName = 'lease-v1.json';
    const mediaName = 'preview.mp4';
    const markerContents =
        '{"version":1,"files":["lease-v1.json","preview.mp4"]}';
    final marker = File(
      '${directory.path}${Platform.pathSeparator}$markerName',
    );
    final handle = await marker.open(mode: FileMode.append);
    await handle.lock(FileLock.exclusive, 0, 1);
    final markerBytes = utf8.encode(markerContents);
    await handle.setPosition(0);
    await handle.writeFrom(markerBytes);
    await handle.truncate(markerBytes.length);
    await handle.flush();

    final media = File('${directory.path}${Platform.pathSeparator}$mediaName');
    await media.writeAsBytes(<int>[11, 22, 33, 44], flush: true);
    stdout.writeln(
      jsonEncode(<String, Object>{
        'state': 'locked',
        'nonce': args[2],
        'directory': canonicalDirectory,
      }),
    );
    await stdout.flush();

    final command = await stdin
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .first
        .timeout(const Duration(seconds: 60));
    if (command != 'exit-with-73') {
      stderr.writeln('Unexpected isolated lease-helper command.');
      exitCode = 69;
      return;
    }

    // This is the crash-recovery fixture: exit immediately without unlocking,
    // closing, deleting, or running a cleanup handler.
    exit(73);
  } catch (_) {
    stderr.writeln('The isolated lease helper failed.');
    exitCode = 70;
  }
}

bool _samePath(String left, String right) {
  final normalizedLeft = left.replaceAll('/', Platform.pathSeparator);
  final normalizedRight = right.replaceAll('/', Platform.pathSeparator);
  return normalizedLeft.toLowerCase() == normalizedRight.toLowerCase();
}
