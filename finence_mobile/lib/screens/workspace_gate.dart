import 'package:flutter/material.dart';

import '../services/workspace_facade.dart';
import 'movements_screen.dart';

class WorkspaceGate extends StatefulWidget {
  const WorkspaceGate({super.key});

  @override
  State<WorkspaceGate> createState() => _WorkspaceGateState();
}

class _WorkspaceGateState extends State<WorkspaceGate> {
  final _workspaces = WorkspaceFacade();
  bool _loading = true;
  String? _workspaceId;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (!_workspaces.isLoggedIn) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final wid = await _workspaces.getActiveWorkspaceId();
      setState(() => _workspaceId = wid);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _joinByCode(String code) async {
    if (!_workspaces.isLoggedIn) return;
    final wid = code.trim();
    if (wid.isEmpty) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await _workspaces.joinByCode(code: wid, role: 'editor');
      setState(() => _workspaceId = wid);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _createWorkspace() async {
    if (!_workspaces.isLoggedIn) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final wid = await _workspaces.createWorkspace();
      setState(() => _workspaceId = wid);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('נוצר קוד שיתוף: $wid')),
      );
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

    if (_workspaceId != null && _workspaceId!.trim().isNotEmpty) {
      return MovementsScreen(workspaceId: _workspaceId!);
    }

    final codeCtrl = TextEditingController();
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
                  const Text(
                    'כדי לעבוד על אותו מידע בכמה מכשירים, הצטרף לשיתוף באמצעות קוד.',
                    style: TextStyle(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: codeCtrl,
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
                    onPressed: () => _joinByCode(codeCtrl.text),
                    child: const Text('הצטרף כשׁותף (Editor)'),
                  ),
                  const SizedBox(height: 8),
                  TextButton(
                    onPressed: _createWorkspace,
                    child: const Text('צור שיתוף חדש'),
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
            onPressed: () => _joinByCode(codeCtrl.text),
            child: const Text('הצטרף'),
          ),
        ),
      ),
    );
  }
}


