import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../screens/app_lock_screen.dart';
import '../services/app_lock_store.dart';

class AppLockGate extends StatefulWidget {
  final Widget child;
  const AppLockGate({super.key, required this.child});

  @override
  State<AppLockGate> createState() => _AppLockGateState();
}

class _AppLockGateState extends State<AppLockGate> with WidgetsBindingObserver {
  final _store = AppLockStore();
  bool _loading = true;
  bool _enabled = false;
  bool _hasPin = false;
  bool _unlocked = false;
  bool _showingLockScreen = false;
  int _lastSeenMs = 0;
  StreamSubscription<User?>? _authSub;
  static const _kInactivityMs = 60 * 1000; // 1 minute

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _authSub = FirebaseAuth.instance.authStateChanges().listen((_) {
      // On account switch / logout, force re-lock.
      _unlocked = false;
      _lastSeenMs = DateTime.now().millisecondsSinceEpoch;
      _refresh();
    });
    _refresh();
  }

  @override
  void dispose() {
    _authSub?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // Important: the biometric prompt itself can trigger lifecycle transitions.
    // If we relock during those transitions, the lock screen gets recreated and
    // biometrics will loop forever.
    if (_showingLockScreen) return;

    // When app leaves foreground, require unlock again next time.
    if (state == AppLifecycleState.inactive || state == AppLifecycleState.paused) {
      _lastSeenMs = DateTime.now().millisecondsSinceEpoch;
      return;
    }

    if (state == AppLifecycleState.resumed) {
      _refresh();
    }
  }

  Future<void> _refresh() async {
    if (!mounted) return;
    setState(() => _loading = true);
    final enabled = await _store.isEnabled();
    final hasPin = await _store.hasPin();
    final now = DateTime.now().millisecondsSinceEpoch;
    if (_lastSeenMs > 0 && (now - _lastSeenMs) > _kInactivityMs) {
      _unlocked = false;
    }
    _lastSeenMs = now;
    if (!mounted) return;
    setState(() {
      _enabled = enabled;
      _hasPin = hasPin;
      _loading = false;
    });
  }

  bool _shouldLock() {
    // Only lock when logged in (otherwise it blocks login UX unnecessarily).
    final loggedIn = FirebaseAuth.instance.currentUser != null;
    return loggedIn && _enabled && _hasPin && !_unlocked;
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return widget.child;
    final shouldLock = _shouldLock();
    _showingLockScreen = shouldLock;
    if (shouldLock) {
      return AppLockScreen(
        onUnlocked: () {
          setState(() => _unlocked = true);
        },
      );
    }
    return widget.child;
  }
}


