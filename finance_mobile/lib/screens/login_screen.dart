import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../services/workspace_facade.dart';

String _authErrorHe(FirebaseAuthException e) {
  switch (e.code) {
    case 'email-already-in-use':
      return 'כבר קיים חשבון עם האימייל הזה. נסה להתחבר.';
    case 'invalid-email':
      return 'כתובת האימייל לא תקינה.';
    case 'weak-password':
      return 'הסיסמה חלשה מדי (לפחות 6 תווים).';
    case 'user-not-found':
    case 'wrong-password':
    case 'invalid-credential':
      return 'האימייל או הסיסמה שגויים.';
    case 'too-many-requests':
      return 'יותר מדי ניסיונות. נסה שוב בעוד כמה דקות.';
    case 'network-request-failed':
      return 'אין חיבור לאינטרנט.';
    default:
      return e.message ?? e.code;
  }
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _codeCtrl = TextEditingController();
  bool _showCode = false;
  bool _isRegister = false;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _emailCtrl.dispose();
    _passwordCtrl.dispose();
    _codeCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final email = _emailCtrl.text.trim();
    final password = _passwordCtrl.text;
    if (email.isEmpty || password.isEmpty) {
      setState(() => _error = 'חובה למלא אימייל וסיסמה');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    // Picked up by WorkspaceGate after sign-in; with no code the gate opens
    // (or creates) the account's own budget automatically.
    WorkspaceFacade.pendingShareCode = _showCode ? _codeCtrl.text.trim() : '';
    try {
      if (_isRegister) {
        await FirebaseAuth.instance.createUserWithEmailAndPassword(
          email: email,
          password: password,
        );
      } else {
        await FirebaseAuth.instance.signInWithEmailAndPassword(
          email: email,
          password: password,
        );
      }
    } on FirebaseAuthException catch (e) {
      setState(() => _error = _authErrorHe(e));
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _forgotPassword() async {
    final email = _emailCtrl.text.trim();
    if (email.isEmpty) {
      setState(() => _error = 'הזן את האימייל שלך כדי לאפס סיסמה');
      return;
    }
    try {
      await FirebaseAuth.instance.sendPasswordResetEmail(email: email);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('שלחנו קישור לאיפוס סיסמה אל $email')),
      );
    } on FirebaseAuthException catch (e) {
      setState(() => _error = _authErrorHe(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final title = _isRegister ? 'הרשמה' : 'התחברות';
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 120),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  TextField(
                    controller: _emailCtrl,
                    keyboardType: TextInputType.emailAddress,
                    decoration: const InputDecoration(labelText: 'אימייל'),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _passwordCtrl,
                    obscureText: true,
                    decoration: const InputDecoration(labelText: 'סיסמה'),
                  ),
                  const SizedBox(height: 6),
                  if (_showCode)
                    TextField(
                      controller: _codeCtrl,
                      textCapitalization: TextCapitalization.characters,
                      decoration: const InputDecoration(
                        labelText: 'קוד שיתוף (לא חובה)',
                        hintText: 'AB12-CD34-EF56',
                      ),
                    )
                  else
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton(
                        onPressed: () => setState(() => _showCode = true),
                        child: const Text('יש לי קוד שיתוף מבן/בת הזוג'),
                      ),
                    ),
                  if (_error != null) ...[
                    const SizedBox(height: 12),
                    Text(_error!, style: const TextStyle(color: Colors.red)),
                  ],
                  const SizedBox(height: 6),
                  if (!_isRegister)
                    Align(
                      alignment: Alignment.centerLeft,
                      child: TextButton(
                        onPressed: _loading ? null : _forgotPassword,
                        child: const Text('שכחתי סיסמה'),
                      ),
                    ),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton(
                      onPressed: _loading
                          ? null
                          : () => setState(() => _isRegister = !_isRegister),
                      child: Text(
                        _isRegister
                            ? 'כבר יש לך משתמש? התחברות'
                            : 'אין לך משתמש? הרשמה',
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
      bottomNavigationBar: SafeArea(
        top: false,
        child: Container(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
          decoration: BoxDecoration(
            color: Theme.of(context).scaffoldBackgroundColor,
            border: Border(
              top: BorderSide(color: Colors.black.withValues(alpha: 0.06)),
            ),
          ),
          child: ElevatedButton(
            onPressed: _loading ? null : _submit,
            child: Text(_loading ? '...' : title),
          ),
        ),
      ),
    );
  }
}


