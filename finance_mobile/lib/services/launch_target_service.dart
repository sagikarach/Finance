import 'dart:async';

import 'package:flutter/services.dart';

class LaunchTargetService {
  static const MethodChannel _ch = MethodChannel('finance/launch');
  static final LaunchTargetService instance = LaunchTargetService._();

  LaunchTargetService._();

  final StreamController<String> _targets = StreamController<String>.broadcast();
  String? _pending;

  Stream<String> get targets => _targets.stream;

  Future<void> init() async {
    _ch.setMethodCallHandler((call) async {
      if (call.method == 'onTarget') {
        final t = (call.arguments as String?)?.trim() ?? '';
        if (t.isNotEmpty) {
          _pending = t;
          _targets.add(t);
        }
      }
      return null;
    });

    try {
      final t = (await _ch.invokeMethod<String>('getInitialTarget'))?.trim() ?? '';
      if (t.isNotEmpty) {
        _pending = t;
      }
    } catch (_) {}
  }

  String? consumePending() {
    final t = _pending;
    _pending = null;
    return t;
  }
}


