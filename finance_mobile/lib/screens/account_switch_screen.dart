import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../services/account_profiles_store.dart';
import '../services/workspace_facade.dart';
import 'dashboard_screen.dart';

class AccountSwitchScreen extends StatefulWidget {
  const AccountSwitchScreen({super.key});

  @override
  State<AccountSwitchScreen> createState() => _AccountSwitchScreenState();
}

class _AccountSwitchScreenState extends State<AccountSwitchScreen> {
  final _store = AccountProfilesStore();
  final _workspaces = WorkspaceFacade();
  bool _loading = true;
  String? _error;
  List<AccountProfile> _profiles = const <AccountProfile>[];
  String? _currentWorkspaceId;

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
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
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
    final nameCtrl = TextEditingController();
    final emailCtrl = TextEditingController();
    final widCtrl = TextEditingController();
    final pwCtrl = TextEditingController();
    bool remember = true;
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
