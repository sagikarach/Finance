import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';

import '../services/action_history_service.dart';
import '../services/bootstrap_service.dart';
import '../services/savings_service.dart';
import '../services/session_service.dart';
import '../widgets/select_field.dart';

class SavingsScreen extends StatefulWidget {
  final String workspaceId;

  const SavingsScreen({super.key, required this.workspaceId});

  @override
  State<SavingsScreen> createState() => _SavingsScreenState();
}

class _SavingsScreenState extends State<SavingsScreen> {
  bool _syncing = false;
  bool _loading = true;
  String? _error;

  final SessionService _session = const SessionService();
  late final BootstrapService _bootstrap;
  late final SavingsService _savings;
  late final ActionHistoryService _actions;

  List<Map<String, dynamic>> _accounts = <Map<String, dynamic>>[];
  String? _pickedLabel;
  String? _pickedAccount;
  String? _pickedSaving;
  final TextEditingController _amountCtrl = TextEditingController();
  DateTime? _pickedDate;

  @override
  void initState() {
    super.initState();
    _bootstrap = BootstrapService(workspaceId: widget.workspaceId);
    _savings = SavingsService(workspaceId: widget.workspaceId);
    _actions = ActionHistoryService(workspaceId: widget.workspaceId);
    _pullFromServer(showToast: false);
  }

  @override
  void dispose() {
    _amountCtrl.dispose();
    super.dispose();
  }

  Future<void> _pullFromServer({required bool showToast}) async {
    if (!_session.isLoggedIn) return;
    setState(() {
      _syncing = true;
      _loading = true;
      _error = null;
    });
    try {
      await _bootstrap.ensureWorkspaceMeta();
      final accounts = await _savings.fetchSavingsAccountsRaw(source: Source.server);
      if (!mounted) return;
      setState(() {
        _accounts = accounts;
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

  List<_SavingPick> _buildPicks() {
    final out = <_SavingPick>[];
    for (final acc in _accounts) {
      final accName = (acc['name'] as String?)?.trim() ?? '';
      if (accName.isEmpty) continue;
      final rawSavings = acc['savings'];
      if (rawSavings is! List) continue;
      for (final it in rawSavings) {
        if (it is! Map) continue;
        final m = it.map((k, v) => MapEntry('$k', v));
        final sName = (m['name'] as String?)?.trim() ?? '';
        if (sName.isEmpty) continue;
        final amount = (m['amount'] is num) ? (m['amount'] as num).toDouble() : 0.0;
        out.add(_SavingPick(
          accountName: accName,
          savingName: sName,
          label: '$accName - $sName',
          amount: amount,
        ));
      }
    }
    out.sort((a, b) => a.label.compareTo(b.label));
    return out;
  }

  Future<void> _pickSaving() async {
    final picks = _buildPicks();
    if (picks.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('אין חסכונות לעדכון. צור חסכונות בדסקטופ וסנכרן.')),
      );
      return;
    }
    final labels = picks.map((p) => p.label).toList();
    final picked = await showStringPickerBottomSheet(
      context: context,
      title: 'בחר חסכון לעדכון',
      items: labels,
      selected: _pickedLabel,
    );
    if (picked == null) return;
    final p = picks.firstWhere((x) => x.label == picked);
    setState(() {
      _pickedLabel = p.label;
      _pickedAccount = p.accountName;
      _pickedSaving = p.savingName;
      _amountCtrl.text = p.amount.toStringAsFixed(2);
    });
  }

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final initial = _pickedDate ?? now;
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2000, 1, 1),
      lastDate: DateTime(now.year + 5, 12, 31),
    );
    if (picked == null) return;
    setState(() => _pickedDate = picked);
  }

  Future<void> _save() async {
    final accountName = (_pickedAccount ?? '').trim();
    final savingName = (_pickedSaving ?? '').trim();
    if (accountName.isEmpty || savingName.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('בחר חסכון לעדכון')),
      );
      return;
    }
    final amtText = _amountCtrl.text.replaceAll(',', '').trim();
    double newAmount;
    try {
      newAmount = double.parse(amtText);
    } catch (_) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('סכום לא חוקי')),
      );
      return;
    }

    final dateStr = (_pickedDate ?? DateTime.now()).toIso8601String().split('T').first;

    double oldAmount = 0.0;
    final picks = _buildPicks();
    for (final p in picks) {
      if (p.accountName == accountName && p.savingName == savingName) {
        oldAmount = p.amount;
        break;
      }
    }

    setState(() => _syncing = true);
    try {
      await _savings.editSaving(
        savingsAccountName: accountName,
        savingName: savingName,
        newAmount: newAmount,
        date: dateStr,
      );
      await _actions.logEditSaving(
        savingsAccountName: accountName,
        savingName: savingName,
        oldAmount: oldAmount,
        newAmount: newAmount,
        date: dateStr,
      );
      await _pullFromServer(showToast: false);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('עודכן בהצלחה')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('שגיאה: $e')),
      );
    } finally {
      if (mounted) setState(() => _syncing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_session.isLoggedIn) {
      return const Scaffold(body: Center(child: Text('לא מחובר')));
    }

    final picks = _buildPicks();

    return Scaffold(
      appBar: AppBar(
        title: const Text('חסכונות'),
        actions: [
          IconButton(
            onPressed: _syncing ? null : () => _pullFromServer(showToast: true),
            icon: _syncing
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.sync),
            tooltip: 'סנכרן עכשיו',
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : (_error != null)
              ? Center(child: Text('שגיאה: $_error'))
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Text(
                              'עדכון חסכון',
                              style: Theme.of(context)
                                  .textTheme
                                  .titleMedium
                                  ?.copyWith(fontWeight: FontWeight.w800),
                            ),
                            const SizedBox(height: 12),
                            SelectField(
                              label: 'חסכון',
                              value: _pickedLabel,
                              placeholder: picks.isEmpty
                                  ? 'אין חסכונות'
                                  : 'בחר חסכון (חשבון חסכון - חסכון)',
                              enabled: picks.isNotEmpty && !_syncing,
                              onTap: _pickSaving,
                            ),
                            const SizedBox(height: 12),
                            TextField(
                              controller: _amountCtrl,
                              enabled: !_syncing,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                labelText: 'סכום חדש',
                                hintText: '0.00',
                              ),
                            ),
                            const SizedBox(height: 12),
                            SelectField(
                              label: 'תאריך',
                              value:
                                  _pickedDate?.toIso8601String().split('T').first,
                              placeholder: 'בחר תאריך',
                              enabled: !_syncing,
                              onTap: _pickDate,
                            ),
                            const SizedBox(height: 16),
                            ElevatedButton(
                              onPressed: _syncing ? null : _save,
                              child: const Text('שמור'),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    if (_accounts.isEmpty)
                      const Center(child: Text('אין חשבונות חסכון עדיין'))
                    else
                      ..._accounts.map((acc) {
                        final accName = (acc['name'] as String?)?.trim() ?? '';
                        final total = (acc['total_amount'] is num)
                            ? (acc['total_amount'] as num).toDouble()
                            : 0.0;
                        final rawSavings = acc['savings'];
                        final List<Map<String, dynamic>> savings = <Map<String, dynamic>>[];
                        if (rawSavings is List) {
                          for (final it in rawSavings) {
                            if (it is Map) {
                              savings.add(it.map((k, v) => MapEntry('$k', v)));
                            }
                          }
                        }
                        return Card(
                          child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                Text(
                                  accName.isEmpty ? 'חסכון' : accName,
                                  style: Theme.of(context)
                                      .textTheme
                                      .titleMedium
                                      ?.copyWith(fontWeight: FontWeight.w800),
                                ),
                                const SizedBox(height: 4),
                                Text('סה״כ: ${total.toStringAsFixed(2)}'),
                                const SizedBox(height: 12),
                                if (savings.isEmpty)
                                  const Text('אין חסכונות בחשבון הזה')
                                else
                                  ...savings.map((s) {
                                    final n = (s['name'] as String?)?.trim() ?? '';
                                    final a = (s['amount'] is num)
                                        ? (s['amount'] as num).toDouble()
                                        : 0.0;
                                    return Padding(
                                      padding: const EdgeInsets.symmetric(vertical: 6),
                                      child: Row(
                                        children: [
                                          Expanded(child: Text(n)),
                                          Text(a.toStringAsFixed(2)),
                                        ],
                                      ),
                                    );
                                  }),
                              ],
                            ),
                          ),
                        );
                      }),
                  ],
                ),
    );
  }
}

class _SavingPick {
  final String accountName;
  final String savingName;
  final String label;
  final double amount;

  _SavingPick({
    required this.accountName,
    required this.savingName,
    required this.label,
    required this.amount,
  });
}


