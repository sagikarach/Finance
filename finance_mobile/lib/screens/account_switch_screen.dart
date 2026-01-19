import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../services/account_profiles_store.dart';
import '../services/app_lock_store.dart';
import '../services/workspace_facade.dart';
import 'dashboard_screen.dart';

class AccountSwitchScreen extends StatefulWidget {
  const AccountSwitchScreen({super.key});

  @override
  State<AccountSwitchScreen> createState() => _AccountSwitchScreenState();
}

class _AccountSwitchScreenState extends State<AccountSwitchScreen> {
  final _store = AccountProfilesStore();
  final _appLock = AppLockStore();
  final _workspaces = WorkspaceFacade();
  bool _loading = true;
  String? _error;
  List<AccountProfile> _profiles = const <AccountProfile>[];
  String? _currentWorkspaceId;
  bool _appLockEnabled = false;
  bool _bioEnabled = false;
  bool _bioAvailable = false;

  String get _currentEmail =>
      (FirebaseAuth.instance.currentUser?.email ?? '').trim();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final items = await _store.list();
      setState(() => _profiles = items);
      try {
        final wid = await _workspaces.getActiveWorkspaceId();
        setState(() => _currentWorkspaceId = wid);
      } catch (_) {
        setState(() => _currentWorkspaceId = null);
      }
      try {
        final en = await _appLock.isEnabled();
        final bio = await _appLock.isBiometricsEnabled();
        final canBio = await _appLock.canUseBiometrics();
        if (!mounted) return;
        setState(() {
          _appLockEnabled = en;
          _bioEnabled = bio;
          _bioAvailable = canBio;
        });
      } catch (_) {}
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<String?> _promptAppPassword({required String title}) async {
    final c1 = TextEditingController();
    return showDialog<String?>(
      context: context,
      builder: (_) => AlertDialog(
        scrollable: true,
        title: Text(title),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: c1,
                obscureText: true,
                keyboardType: TextInputType.visiblePassword,
                decoration: const InputDecoration(labelText: 'סיסמת חשבון Firebase'),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(null),
            child: const Text('ביטול'),
          ),
          FilledButton(
            onPressed: () {
              final p1 = c1.text.trim();
              if (p1.isEmpty) return;
              Navigator.of(context).pop(p1);
            },
            child: const Text('שמור'),
          ),
        ],
      ),
    );
  }

  Future<void> _toggleAppLock(bool v) async {
    if (v) {
      final email = (FirebaseAuth.instance.currentUser?.email ?? '').trim();
      if (email.isEmpty) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('יש להתחבר קודם לחשבון Firebase')),
        );
        return;
      }

      final pw = await _promptAppPassword(title: 'הפעל נעילת אפליקציה');
      if (pw == null || pw.trim().isEmpty) return;

      // Verify the password matches the current Firebase user (prevents lock-out).
      try {
        final cred = EmailAuthProvider.credential(email: email, password: pw);
        await FirebaseAuth.instance.currentUser?.reauthenticateWithCredential(cred);
      } on FirebaseAuthException catch (_) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('סיסמה שגויה')),
        );
        return;
      } catch (_) {}

      await _appLock.setPin(pw);
      await _appLock.setEnabled(true);
      final canBio = await _appLock.canUseBiometrics();
      if (!mounted) return;
      setState(() {
        _appLockEnabled = true;
        _bioAvailable = canBio;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('נעילת אפליקציה הופעלה')),
      );
    } else {
      await _appLock.setEnabled(false);
      if (!mounted) return;
      setState(() {
        _appLockEnabled = false;
        _bioEnabled = false;
      });
    }
  }

  Future<void> _toggleBiometrics(bool v) async {
    if (!_appLockEnabled) return;
    final can = await _appLock.canUseBiometrics();
    if (!can) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('אין תמיכה בזיהוי ביומטרי במכשיר')),
      );
      return;
    }
    if (v) {
      // Require a successful biometric auth to enable.
      final ok = await _appLock.authenticateWithBiometrics();
      if (!mounted) return;
      if (!ok) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('אימות ביומטרי נכשל או בוטל')),
        );
        return;
      }
    }
    await _appLock.setBiometricsEnabled(v);
    if (!mounted) return;
    setState(() {
      _bioEnabled = v;
      _bioAvailable = can;
    });
  }

  Future<bool> _requireAppLockForAccountSwitch() async {
    // App lock is global (not per account). If enabled, require confirmation
    // when switching accounts.
    try {
      final enabled = await _appLock.isEnabled();
      final hasPin = await _appLock.hasPin();
      if (!enabled || !hasPin) return true;
    } catch (_) {
      // If we can't read lock state, don't block account switching.
      return true;
    }

    if (!mounted) return false;
    final canBio = await _appLock.canUseBiometrics();
    final bioEnabled = await _appLock.isBiometricsEnabled();

    final ctrl = TextEditingController();
    if (!mounted) return false;
    return showDialog<bool>(
          context: context,
          builder: (_) => AlertDialog(
            scrollable: true,
            title: const Text('אימות לפני החלפת חשבון'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text('הזן קוד כדי להמשיך',
                      style: TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 12),
                  TextField(
                    controller: ctrl,
                    obscureText: true,
                    keyboardType: TextInputType.visiblePassword,
                    decoration:
                        const InputDecoration(labelText: 'סיסמת חשבון Firebase'),
                  ),
                  const SizedBox(height: 12),
                  if (bioEnabled && canBio)
                    OutlinedButton(
                      onPressed: () async {
                        final ok = await _appLock.authenticateWithBiometrics();
                        if (!mounted) return;
                        Navigator.of(context).pop(ok);
                      },
                      child: const Text('השתמש בזיהוי ביומטרי'),
                    ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(false),
                child: const Text('ביטול'),
              ),
              FilledButton(
                onPressed: () async {
                  final pin = ctrl.text.trim();
                  if (pin.isEmpty) return;
                  final ok = await _appLock.verifyPin(pin);
                  if (!mounted) return;
                  Navigator.of(context).pop(ok);
                },
                child: const Text('אישור'),
              ),
            ],
          ),
        ).then((v) => v ?? false);
  }

  Future<String?> _promptPassword({
    required String title,
    required String subtitle,
  }) async {
    final ctrl = TextEditingController();
    bool remember = true;
    return showDialog<String?>(
      context: context,
      builder: (_) => AlertDialog(
        scrollable: true,
        title: Text(title),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(subtitle,
                  style: const TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 12),
              TextField(
                controller: ctrl,
                obscureText: true,
                decoration: const InputDecoration(labelText: 'סיסמה'),
              ),
              const SizedBox(height: 8),
              StatefulBuilder(
                builder: (context, setState) => CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  value: remember,
                  onChanged: (v) => setState(() => remember = v ?? true),
                  title: const Text('זכור סיסמה במכשיר'),
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(null),
            child: const Text('ביטול'),
          ),
          FilledButton(
            onPressed: () async {
              final pw = ctrl.text;
              if (pw.trim().isEmpty) return;
              Navigator.of(context).pop('${remember ? '1' : '0'}::$pw');
            },
            child: const Text('התחבר'),
          ),
        ],
      ),
    ).then((v) {
      if (v == null) return null;
      final parts = v.split('::');
      if (parts.length != 2) return null;
      return v;
    });
  }

  Future<void> _switchTo(AccountProfile profile) async {
    final allowed = await _requireAppLockForAccountSwitch();
    if (!allowed) return;

    final e = profile.email.trim();
    final wid = profile.workspaceId.trim();
    final label = (profile.name.trim().isNotEmpty ? profile.name.trim() : e);
    if (e.isEmpty) return;
    if (wid.isEmpty) {
      setState(() => _error = 'חובה להגדיר קוד שיתוף (Workspace ID) לחשבון');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      String? pw = await _store.getPassword(email: e, workspaceId: wid);
      bool remember = true;
      if (pw == null) {
        final packed = await _promptPassword(
          title: 'התחברות לחשבון',
          subtitle: '$label\n$wid',
        );
        if (packed == null) {
          if (mounted) setState(() => _loading = false);
          return;
        }
        final parts = packed.split('::');
        remember = parts.first == '1';
        pw = parts.last;
      }

      // Switch account: sign out + sign in.
      await FirebaseAuth.instance.signOut();
      await FirebaseAuth.instance
          .signInWithEmailAndPassword(email: e, password: pw);

      await _workspaces.joinByCode(code: wid, role: 'editor');

      await _store.upsert(
        name: profile.name,
        email: e,
        workspaceId: wid,
        rememberPassword: remember,
      );
      if (remember) {
        await _store.setPassword(email: e, workspaceId: wid, password: pw);
      } else {
        await _store.deletePassword(email: e, workspaceId: wid);
      }

      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => DashboardScreen(workspaceId: wid)),
        (r) => false,
      );
    } on FirebaseAuthException catch (e) {
      setState(() => _error = e.message ?? e.code);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _addAccount() async {
    final allowed = await _requireAppLockForAccountSwitch();
    if (!allowed) return;

    final nameCtrl = TextEditingController();
    final emailCtrl = TextEditingController();
    final widCtrl = TextEditingController();
    final pwCtrl = TextEditingController();
    bool remember = true;
    if (!mounted) return;
    final packed = await showDialog<String?>(
      context: context,
      builder: (_) => AlertDialog(
        scrollable: true,
        title: const Text('הוסף חשבון'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameCtrl,
                decoration: const InputDecoration(labelText: 'שם חשבון'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: emailCtrl,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(labelText: 'אימייל'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: widCtrl,
                decoration: const InputDecoration(
                  labelText: 'קוד שיתוף (Workspace ID)',
                  hintText: 'AAAA-BBBB-CCCC',
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: pwCtrl,
                obscureText: true,
                decoration: const InputDecoration(labelText: 'סיסמה'),
              ),
              const SizedBox(height: 8),
              StatefulBuilder(
                builder: (context, setState) => CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  value: remember,
                  onChanged: (v) => setState(() => remember = v ?? true),
                  title: const Text('זכור סיסמה במכשיר'),
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(null),
            child: const Text('ביטול'),
          ),
          FilledButton(
            onPressed: () {
              final n = nameCtrl.text.trim();
              final e = emailCtrl.text.trim();
              final w = widCtrl.text.trim();
              final p = pwCtrl.text;
              if (e.isEmpty || w.isEmpty || p.isEmpty) return;
              Navigator.of(context)
                  .pop('${remember ? '1' : '0'}::$n::$e::$w::$p');
            },
            child: const Text('התחבר'),
          ),
        ],
      ),
    );
    if (packed == null) return;
    final parts = packed.split('::');
    if (parts.length != 5) return;
    final rememberFlag = parts[0] == '1';
    final name = parts[1];
    final email = parts[2];
    final wid = parts[3];
    final pw = parts[4];

    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await FirebaseAuth.instance.signOut();
      await FirebaseAuth.instance
          .signInWithEmailAndPassword(email: email, password: pw);

      await _workspaces.joinByCode(code: wid, role: 'editor');

      await _store.upsert(
        name: name,
        email: email,
        workspaceId: wid,
        rememberPassword: rememberFlag,
      );
      if (rememberFlag) {
        await _store.setPassword(email: email, workspaceId: wid, password: pw);
      } else {
        await _store.deletePassword(email: email, workspaceId: wid);
      }
      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => DashboardScreen(workspaceId: wid)),
        (r) => false,
      );
    } on FirebaseAuthException catch (e) {
      setState(() => _error = e.message ?? e.code);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _signOut() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await FirebaseAuth.instance.signOut();
      if (!mounted) return;
      Navigator.of(context).popUntil((r) => r.isFirst);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('חשבונות'),
        actions: [
          IconButton(
            tooltip: 'רענן',
            onPressed: _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(12),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text('אבטחה',
                        style: TextStyle(fontWeight: FontWeight.w800)),
                    const SizedBox(height: 8),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      value: _appLockEnabled,
                      onChanged: (v) => _toggleAppLock(v),
                      title: const Text('נעילת אפליקציה (סיסמת חשבון Firebase)'),
                    ),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      value: _bioEnabled,
                      onChanged: (_appLockEnabled && _bioAvailable)
                          ? (v) => _toggleBiometrics(v)
                          : null,
                      title: const Text('זיהוי ביומטרי (טביעת אצבע / Face ID)'),
                    ),
                  ],
                ),
              ),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.all(8),
                child: Text(_error!, style: const TextStyle(color: Colors.red)),
              ),
            const SizedBox(height: 8),
            Card(
              child: Column(
                children: [
                  for (final p in _profiles)
                    ListTile(
                      leading: Icon(
                        p.email.toLowerCase() == _currentEmail.toLowerCase() &&
                                p.workspaceId.trim() ==
                                    (_currentWorkspaceId ?? '').trim()
                            ? Icons.check_circle
                            : Icons.account_circle,
                      ),
                      title: Text(
                          p.name.trim().isNotEmpty ? p.name.trim() : p.email),
                      subtitle: Text(
                        [
                          p.email,
                          if (p.workspaceId.trim().isNotEmpty)
                            'Workspace: ${p.workspaceId.trim()}'
                          else
                            'חסר Workspace ID',
                          p.rememberPassword
                              ? 'סיסמה שמורה'
                              : 'נדרש להזין סיסמה',
                        ].join('\n'),
                      ),
                      onTap: () => _switchTo(p),
                      trailing: IconButton(
                        tooltip: 'מחק',
                        onPressed: () async {
                          await _store.delete(
                            email: p.email,
                            workspaceId: p.workspaceId,
                          );
                          await _load();
                        },
                        icon: const Icon(Icons.delete_outline),
                      ),
                    ),
                  if (_profiles.isEmpty)
                    const Padding(
                      padding: EdgeInsets.all(16),
                      child: Text('אין חשבונות שמורים. לחץ על "הוסף חשבון".'),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: _addAccount,
              icon: const Icon(Icons.add),
              label: const Text('הוסף חשבון'),
            ),
            const SizedBox(height: 8),
            OutlinedButton(
              onPressed: _signOut,
              child: const Text('התנתק'),
            ),
            const SizedBox(height: 16),
            const Text(
              'החלפת חשבון דורשת התחברות מחדש. לאחר ההחלפה האפליקציה תטען את ה-Workspace הפעיל של החשבון החדש.',
              style: TextStyle(color: Colors.black54),
            ),
          ],
        ),
      ),
    );
  }
}
