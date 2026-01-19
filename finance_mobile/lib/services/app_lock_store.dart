import 'dart:convert';
import 'dart:math';

import 'package:crypto/crypto.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:local_auth/local_auth.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AppLockStore {
  static const _kEnabled = 'app_lock_enabled_v1';
  static const _kBioEnabled = 'app_lock_bio_enabled_v1';

  static const _kPinSalt = 'app_lock_pin_salt_v1';
  static const _kPinHash = 'app_lock_pin_hash_v1';

  final FlutterSecureStorage _sec;
  final LocalAuthentication _auth;

  AppLockStore({
    FlutterSecureStorage? sec,
    LocalAuthentication? auth,
  })  : _sec = sec ?? const FlutterSecureStorage(),
        _auth = auth ?? LocalAuthentication();

  Future<bool> isEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_kEnabled) ?? false;
  }

  Future<void> setEnabled(bool v) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kEnabled, v);
    if (!v) {
      // Keep PIN stored (so re-enabling is easy), but disable biometrics.
      await prefs.setBool(_kBioEnabled, false);
    }
  }

  Future<bool> isBiometricsEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_kBioEnabled) ?? false;
  }

  Future<void> setBiometricsEnabled(bool v) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kBioEnabled, v);
  }

  Future<bool> hasPin() async {
    final salt = await _sec.read(key: _kPinSalt);
    final hash = await _sec.read(key: _kPinHash);
    return (salt ?? '').trim().isNotEmpty && (hash ?? '').trim().isNotEmpty;
  }

  Future<void> clearPin() async {
    await _sec.delete(key: _kPinSalt);
    await _sec.delete(key: _kPinHash);
  }

  Future<void> setPin(String pin) async {
    final p = pin.trim();
    if (p.isEmpty) return;
    final saltBytes = List<int>.generate(16, (_) => Random.secure().nextInt(256));
    final salt = base64UrlEncode(saltBytes);
    final hash = _hashPin(pin: p, salt: salt);
    await _sec.write(key: _kPinSalt, value: salt);
    await _sec.write(key: _kPinHash, value: hash);
  }

  Future<bool> verifyPin(String pin) async {
    final p = pin.trim();
    if (p.isEmpty) return false;
    final salt = (await _sec.read(key: _kPinSalt)) ?? '';
    final expected = (await _sec.read(key: _kPinHash)) ?? '';
    if (salt.trim().isEmpty || expected.trim().isEmpty) return false;
    final got = _hashPin(pin: p, salt: salt);
    return got == expected;
  }

  String _hashPin({required String pin, required String salt}) {
    final bytes = utf8.encode('$salt::$pin');
    return sha256.convert(bytes).toString();
  }

  Future<bool> canUseBiometrics() async {
    try {
      final supported = await _auth.isDeviceSupported();
      if (!supported) return false;
      final canCheck = await _auth.canCheckBiometrics;
      if (!canCheck) return false;
      final types = await _auth.getAvailableBiometrics();
      return types.isNotEmpty;
    } catch (_) {
      return false;
    }
  }

  Future<bool> authenticateWithBiometrics() async {
    try {
      return await _auth.authenticate(
        localizedReason: 'אימות באמצעות טביעת אצבע / Face ID',
        options: const AuthenticationOptions(
          biometricOnly: true,
          // Avoid re-opening the prompt automatically on lifecycle transitions.
          stickyAuth: false,
        ),
      );
    } catch (_) {
      return false;
    }
  }
}


