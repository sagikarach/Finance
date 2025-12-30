import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../services/workspace_service.dart';

class WorkspaceScreen extends StatefulWidget {
  const WorkspaceScreen({super.key});

  @override
  State<WorkspaceScreen> createState() => _WorkspaceScreenState();
}

class _WorkspaceScreenState extends State<WorkspaceScreen> {
  final _service = WorkspaceService();
  final _codeCtrl = TextEditingController();
  bool _loading = true;
  String? _currentWid;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _codeCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final wid = await _service.getActiveWorkspaceId(user.uid);
      setState(() => _currentWid = wid);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _joinByCode() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;
    final wid = _codeCtrl.text.trim();
    if (wid.isEmpty) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await _service.validateWorkspaceExists(wid);
      await _service.ensureMembership(uid: user.uid, wid: wid, role: 'editor');
      await _service.setActiveWorkspaceId(user.uid, wid);
      if (!mounted) return;
      Navigator.of(context).pop(wid);
    } catch (e) {
      setState(() => _error = e.toString());
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _createWorkspace() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final wid = _service.generateWorkspaceCode();
      await _service.ensureMembership(uid: user.uid, wid: wid, role: 'owner');
      await _service.setActiveWorkspaceId(user.uid, wid);
      if (!mounted) return;
      await Clipboard.setData(ClipboardData(text: wid));
      if (!mounted) return;
      Navigator.of(context).pop(wid);
    } catch (e) {
      setState(() => _error = e.toString());
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _disconnect() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await _service.setActiveWorkspaceId(user.uid, '');
      if (!mounted) return;
      Navigator.of(context).pop(null);
    } catch (e) {
      setState(() => _error = e.toString());
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    return Scaffold(
      appBar: AppBar(title: const Text('שיתוף נתונים')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 120),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if ((_currentWid ?? '').trim().isNotEmpty) ...[
                    Text(
                      'קוד שיתוף נוכחי:',
                      style: Theme.of(context)
                          .textTheme
                          .titleSmall
                          ?.copyWith(fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        Expanded(
                          child: SelectableText(
                            _currentWid!,
                            style: const TextStyle(fontWeight: FontWeight.w700),
                          ),
                        ),
                        IconButton(
                          tooltip: 'העתק',
                          onPressed: () async {
                            await Clipboard.setData(
                              ClipboardData(text: _currentWid!),
                            );
                            if (!context.mounted) return;
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('הקוד הועתק')),
                            );
                          },
                          icon: const Icon(Icons.copy),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    TextButton(
                      onPressed: _disconnect,
                      child: const Text('נתק שיתוף'),
                    ),
                    const Divider(height: 24),
                  ],
                  const Text(
                    'הצטרפות לשיתוף באמצעות קוד:',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _codeCtrl,
                    decoration: const InputDecoration(
                      labelText: 'קוד שיתוף',
                      hintText: 'AAAA-BBBB-CCCC',
                    ),
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 12),
                    Text(_error!, style: const TextStyle(color: Colors.red)),
                  ],
                  const SizedBox(height: 12),
                  ElevatedButton(
                    onPressed: _joinByCode,
                    child: const Text('הצטרף כשׁותף (Editor)'),
                  ),
                  const SizedBox(height: 8),
                  TextButton(
                    onPressed: _createWorkspace,
                    child: const Text('צור שיתוף חדש (הקוד יועתק)'),
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
            onPressed: _joinByCode,
            child: const Text('הצטרף'),
          ),
        ),
      ),
    );
  }
}


