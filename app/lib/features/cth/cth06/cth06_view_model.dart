import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'cth06_repository.dart';

enum Cth06LoadPhase { loading, ready, unavailable }

enum Cth06FailureKind {
  contextUnavailable,
  pageNotBound,
  focusNotBound,
  authentication,
  permissionDenied,
  offline,
  server,
}

class Cth06ViewModel extends ChangeNotifier {
  Cth06ViewModel({required this._repository});

  final Cth06Repository _repository;

  Cth06LoadPhase phase = Cth06LoadPhase.loading;
  Cth06FailureKind? failureKind;
  Cth06ScreenData? data;
  Cth06Category? selectedCategory;
  int? selectedItemIndex;
  bool _disposed = false;

  Future<void> refresh() async {
    phase = Cth06LoadPhase.loading;
    failureKind = null;
    data = null;
    selectedCategory = null;
    selectedItemIndex = null;
    _notify();
    try {
      data = await _repository.load();
      phase = Cth06LoadPhase.ready;
    } on Cth06ContextUnavailable catch (error) {
      failureKind = switch (error.reason) {
        Cth06BlockReason.contextUnavailable =>
          Cth06FailureKind.contextUnavailable,
        Cth06BlockReason.pageNotBound => Cth06FailureKind.pageNotBound,
        Cth06BlockReason.focusNotBound => Cth06FailureKind.focusNotBound,
      };
      phase = Cth06LoadPhase.unavailable;
    } on LumenisCoreException catch (error) {
      failureKind = _classify(error);
      phase = Cth06LoadPhase.unavailable;
    } on FormatException {
      failureKind = Cth06FailureKind.server;
      phase = Cth06LoadPhase.unavailable;
    } catch (_) {
      failureKind = Cth06FailureKind.server;
      phase = Cth06LoadPhase.unavailable;
    }
    _notify();
  }

  void chooseCategory(Cth06Category? category) {
    selectedCategory = category;
    selectedItemIndex = null;
    _notify();
  }

  void selectItem(int index) {
    final items = visibleItems();
    if (index < 0 || index >= items.length) return;
    selectedItemIndex = index;
    _notify();
  }

  List<Cth06Feedback> visibleItems() {
    final items = data?.items ?? const <Cth06Feedback>[];
    if (selectedCategory == null) return items;
    return items
        .where((item) => item.category == selectedCategory)
        .toList(growable: false);
  }

  Cth06Feedback? get selectedItem {
    final items = visibleItems();
    final index = selectedItemIndex;
    return index == null || index < 0 || index >= items.length
        ? null
        : items[index];
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  static Cth06FailureKind _classify(LumenisCoreException error) =>
      switch (error.statusCode) {
        401 => Cth06FailureKind.authentication,
        403 => Cth06FailureKind.permissionDenied,
        null => Cth06FailureKind.offline,
        _ => Cth06FailureKind.server,
      };

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
