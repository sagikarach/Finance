import 'package:flutter/material.dart';

import '../services/app_lock_store.dart';

class AppLockScreen extends StatefulWidget {
  final VoidCallback onUnlocked;
  const AppLockScreen({super.key, required this.onUnlocked});

  @override
  State<AppLockScreen> createState() => _AppLockScreenState();
}

class _AppLockScreenState extends State<AppLockScreen> {
  final _store = AppLockStore();
  final _pinCtrl = TextEditingController();
  bool _loading = true;
  bool _bioEnabled = false;
  bool _bioAvailable = false;
  bool _autoBioAttempted = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _pinCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    if (!mounted) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    final bioEnabled = await _store.isBiometricsEnabled();
    final bioAvailable = await _store.canUseBiometrics();
    if (!mounted) return;
    setState(() {
      _bioEnabled = bioEnabled;
      _bioAvailable = bioAvailable;
      _loading = false;
    });

    // Auto-attempt biometrics at most once per screen. If the user cancels,
    // we keep them on the password field (no infinite reopen).
    if (!_autoBioAttempted && bioEnabled && bioAvailable) {
      _autoBioAttempted = true;
      await _tryBiometric();
    }
  }

  Future<void> _tryBiometric() async {
    setState(() => _error = null);
    final ok = await _store.authenticateWithBiometrics();
    if (!mounted) return;
    if (ok) {
      widget.onUnlocked();
    } else {
      setState(() => _error = 'אימות ביומטרי נכשל או בוטל');
    }
  }

  Future<void> _unlockWithPin() async {
    setState(() => _error = null);
    final pin = _pinCtrl.text.trim();
    if (pin.isEmpty) return;
    final ok = await _store.verifyPin(pin);
    if (!mounted) return;
    if (!ok) {
      setState(() => _error = 'קוד שגוי');
      return;
    }
    widget.onUnlocked();
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const Text(
                        'נעילת אפליקציה',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
                      ),
                      const SizedBox(height: 12),
                      const Text(
                        'הזן סיסמה כדי להמשיך',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _pinCtrl,
                        decoration: const InputDecoration(labelText: 'קוד / סיסמה'),
                        obscureText: true,
                        keyboardType: TextInputType.visiblePassword,
                        textInputAction: TextInputAction.done,
                        onSubmitted: (_) => _unlockWithPin(),
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: 8),
                        Text(_error!, style: const TextStyle(color: Colors.red)),
                      ],
                      const SizedBox(height: 12),
                      FilledButton(
                        onPressed: _unlockWithPin,
                        child: const Text('אישור'),
                      ),
                      if (_bioEnabled && _bioAvailable) ...[
                        const SizedBox(height: 8),
                        OutlinedButton(
                          onPressed: _tryBiometric,
                          child: const Text('השתמש בזיהוי ביומטרי'),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}


