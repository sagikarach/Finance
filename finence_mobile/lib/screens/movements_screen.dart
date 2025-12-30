import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../models/movement.dart';
import '../services/accounts_meta_service.dart';
import '../services/categories_service.dart';
import 'new_movement_screen.dart';
import 'workspace_screen.dart';

class MovementsScreen extends StatefulWidget {
  final String workspaceId;

  const MovementsScreen({super.key, required this.workspaceId});

  @override
  State<MovementsScreen> createState() => _MovementsScreenState();
}

class _MovementsScreenState extends State<MovementsScreen> {
  bool _syncing = false;
  bool _loading = true;
  String? _error;
  List<Movement> _items = <Movement>[];

  CollectionReference<Map<String, dynamic>> _ref() {
    return FirebaseFirestore.instance
        .collection('workspaces')
        .doc(widget.workspaceId)
        .collection('movements');
  }

  Future<void> _deleteMovement(Movement m) async {
    try {
      await _ref().doc(m.id).set(<String, Object?>{
        'id': m.id,
        'deleted': true,
      }, SetOptions(merge: true));

      // Log action to shared workspace history (so desktop can pull it).
      final actionId = const Uuid().v4();
      final today = DateTime.now().toIso8601String().split('T').first;
      await FirebaseFirestore.instance
          .collection('workspaces')
          .doc(widget.workspaceId)
          .collection('actions')
          .doc(actionId)
          .set(<String, Object?>{
        'id': actionId,
        'timestamp': today,
        'action': <String, Object?>{
          'action_name': 'delete_movement',
          'movement_id': m.id,
          'account_name': m.accountName,
          'amount': m.amount,
          'date': m.date,
        },
      }, SetOptions(merge: true));
      if (!mounted) return;
      setState(() => _items = _items.where((x) => x.id != m.id).toList());
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('התנועה נמחקה')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('שגיאת מחיקה: $e')),
      );
    }
  }

  @override
  void initState() {
    super.initState();
    _pullFromServer(showToast: false);
  }

  Future<void> _pullFromServer({required bool showToast}) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;

    setState(() {
      _syncing = true;
      _loading = true;
      _error = null;
    });
    try {
      // Ensure meta docs exist and force a network read (so we can show errors clearly).
      await CategoriesService(workspaceId: widget.workspaceId).ensureDoc();
      await AccountsMetaService(workspaceId: widget.workspaceId).ensureDoc();
      final snap = await _ref()
          .orderBy('date', descending: true)
          .get(const GetOptions(source: Source.server));

      final items = snap.docs
          .map((d) => Movement.fromFirestore(d.data()))
          .where((m) => m.id.isNotEmpty && !m.deleted)
          .toList();

      if (!mounted) return;
      setState(() {
        _items = items;
        _loading = false;
      });
      if (showToast) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('סונכרן בהצלחה')),
        );
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loading = false;
      });
      if (showToast) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('שגיאת סנכרון: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _syncing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      return const Scaffold(body: Center(child: Text('לא מחובר')));
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('תנועות'),
        actions: [
          IconButton(
            tooltip: 'שיתוף',
            onPressed: () async {
              final picked = await Navigator.of(context).push<String?>(
                MaterialPageRoute(builder: (_) => const WorkspaceScreen()),
              );
              if (picked == null) return;
              if (!context.mounted) return;
              Navigator.of(context).pushReplacement(
                MaterialPageRoute(
                  builder: (_) => MovementsScreen(workspaceId: picked),
                ),
              );
            },
            icon: const Icon(Icons.group),
          ),
          IconButton(
            onPressed: _syncing
                ? null
                : () => _pullFromServer(showToast: true),
            icon: _syncing
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.sync),
            tooltip: 'סנכרן עכשיו',
          ),
          IconButton(
            onPressed: () => FirebaseAuth.instance.signOut(),
            icon: const Icon(Icons.logout),
            tooltip: 'התנתק',
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => NewMovementScreen(workspaceId: widget.workspaceId),
          ),
        ),
        child: const Icon(Icons.add),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : (_error != null)
              ? Center(child: Text('שגיאה: $_error'))
              : (_items.isEmpty)
                  ? const Center(child: Text('אין תנועות עדיין'))
                  : ListView.separated(
                      padding: const EdgeInsets.all(16),
                      itemCount: _items.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 10),
                      itemBuilder: (context, idx) {
                        final m = _items[idx];
                        final isIncome = m.amount > 0;
                        final amountAbs = m.amount.abs().toStringAsFixed(2);
                        final typeLabel = switch (m.type) {
                          'MONTHLY' => 'חודשי',
                          'YEARLY' => 'שנתי',
                          _ => 'חד פעמי',
                        };
                        return Dismissible(
                          key: ValueKey<String>(m.id),
                          direction: DismissDirection.endToStart,
                          confirmDismiss: (_) async {
                            return await showDialog<bool>(
                                  context: context,
                                  builder: (ctx) => AlertDialog(
                                    title: const Text('מחיקת תנועה'),
                                    content: const Text('האם למחוק את התנועה הזו?'),
                                    actions: [
                                      TextButton(
                                        onPressed: () => Navigator.of(ctx).pop(false),
                                        child: const Text('ביטול'),
                                      ),
                                      ElevatedButton(
                                        onPressed: () => Navigator.of(ctx).pop(true),
                                        child: const Text('מחק'),
                                      ),
                                    ],
                                  ),
                                ) ??
                                false;
                          },
                          onDismissed: (_) => _deleteMovement(m),
                          background: Container(
                            alignment: Alignment.centerRight,
                            padding: const EdgeInsets.symmetric(horizontal: 16),
                            color: Colors.red.withValues(alpha: 0.12),
                            child: const Icon(Icons.delete_outline, color: Colors.red),
                          ),
                          child: Card(
                            child: ListTile(
                              title: Text('${m.category} • ${m.accountName}'),
                              subtitle: Text('${m.date} • $typeLabel'),
                              trailing: Text(
                                '${isIncome ? '+' : '-'}$amountAbs',
                                style: TextStyle(
                                  color: isIncome ? Colors.green : Colors.red,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                            ),
                          ),
                        );
                      },
                    ),
    );
  }
}


