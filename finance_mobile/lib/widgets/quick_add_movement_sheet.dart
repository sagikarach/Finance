import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../models/movement.dart';
import '../services/accounts_meta_service.dart';
import '../services/action_history_service.dart';
import '../services/bootstrap_service.dart';
import '../services/categories_service.dart';
import '../services/movements_service.dart';
import '../services/session_service.dart';
import 'category_picker.dart';
import 'select_field.dart';

class QuickAddMovementSheet extends StatefulWidget {
  final String workspaceId;

  const QuickAddMovementSheet({super.key, required this.workspaceId});

  static Future<bool?> show(BuildContext context, {required String workspaceId}) {
    return showModalBottomSheet<bool>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (_) => QuickAddMovementSheet(workspaceId: workspaceId),
    );
  }

  @override
  State<QuickAddMovementSheet> createState() => _QuickAddMovementSheetState();
}

class _QuickAddMovementSheetState extends State<QuickAddMovementSheet> {
  final _formKey = GlobalKey<FormState>();
  final _amountCtrl = TextEditingController();

  bool _isIncome = false;
  DateTime _date = DateTime.now();
  String _accountName = '';
  List<String> _activeAccounts = <String>[];
  String _category = '';

  bool _saving = false;
  String? _error;

  final SessionService _session = const SessionService();
  late final BootstrapService _bootstrap;
  late final AccountsMetaService _accountsMeta;
  late final CategoriesService _categories;
  late final MovementsService _movements;
  late final ActionHistoryService _actions;

  @override
  void initState() {
    super.initState();
    _bootstrap = BootstrapService(workspaceId: widget.workspaceId);
    _accountsMeta = AccountsMetaService(workspaceId: widget.workspaceId);
    _categories = CategoriesService(workspaceId: widget.workspaceId);
    _movements = MovementsService(workspaceId: widget.workspaceId);
    _actions = ActionHistoryService(workspaceId: widget.workspaceId);
    _bootstrap.ensureWorkspaceMeta();
    _loadActiveAccounts();
  }

  @override
  void dispose() {
    _amountCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadActiveAccounts() async {
    try {
      final list = await _accountsMeta.fetchActiveBankAccountNames(
        source: Source.server,
      );
      if (!mounted) return;
      setState(() {
        _activeAccounts = list;
        if (_accountName.isEmpty && _activeAccounts.isNotEmpty) {
          _accountName = _activeAccounts.first;
        }
      });
    } catch (_) {}
  }

  String _isoDate(DateTime d) {
    final mm = d.month.toString().padLeft(2, '0');
    final dd = d.day.toString().padLeft(2, '0');
    return '${d.year}-$mm-$dd';
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    if (picked != null) setState(() => _date = picked);
  }

  Future<void> _save() async {
    if (!_session.isLoggedIn) {
      setState(() => _error = 'לא מחובר');
      return;
    }
    if (!_formKey.currentState!.validate()) return;
    if (_accountName.trim().isEmpty) {
      setState(() => _error = 'אין חשבונות פעילים. הפעל חשבון בדסקטופ ואז סנכרן.');
      return;
    }
    if (_category.trim().isEmpty) {
      setState(() => _error = 'בחר קטגוריה או הוסף חדשה');
      return;
    }

    setState(() {
      _saving = true;
      _error = null;
    });

    try {
      final row = await _accountsMeta.fetchBankAccountRow(name: _accountName);
      final isActive = (row?['active'] as bool?) ?? false;
      if (!isActive) {
        if (mounted) {
          setState(
            () => _error = 'החשבון שנבחר אינו פעיל. הפעל אותו בהגדרות ואז נסה שוב.',
          );
        }
        return;
      }

      final kind = (row?['kind'] as String?)?.trim() ?? '';
      final amount = double.parse(_amountCtrl.text.trim());
      if (kind == 'budget') {
        if (_isIncome) {
          if (mounted) setState(() => _error = 'לא ניתן להוסיף הכנסה לחשבון תקציב');
          return;
        }
        final balance = (row?['total_amount'] as num?)?.toDouble() ?? 0.0;
        if (amount.abs() > balance + 1e-9) {
          if (mounted) setState(() => _error = 'אין מספיק תקציב בחשבון שנבחר');
          return;
        }
      }

      final signedAmount = _isIncome ? amount.abs() : -amount.abs();
      final id = const Uuid().v4();
      final movement = Movement(
        id: id,
        amount: signedAmount,
        date: _isoDate(_date),
        accountName: _accountName,
        category: _category,
        type: 'ONE_TIME',
        description: null,
        eventId: null,
        deleted: false,
      );

      await _movements.upsert(movement);
      await _actions.logAddMovement(movementId: id, isIncome: signedAmount > 0);

      if (!mounted) return;
      Navigator.of(context).pop(true);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(16, 8, 16, 16 + bottomInset),
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'הוספה מהירה',
                style: Theme.of(context)
                    .textTheme
                    .titleMedium
                    ?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 12),
              SegmentedButton<bool>(
                segments: const [
                  ButtonSegment(value: false, label: Text('הוצאה')),
                  ButtonSegment(value: true, label: Text('הכנסה')),
                ],
                selected: {_isIncome},
                onSelectionChanged: (v) => setState(() => _isIncome = v.first),
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _amountCtrl,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'סכום (חיובי)'),
                validator: (v) {
                  final s = (v ?? '').trim();
                  if (s.isEmpty) return 'חובה';
                  final n = double.tryParse(s);
                  if (n == null) return 'מספר לא תקין';
                  if (n <= 0) return 'חייב להיות גדול מ-0';
                  return null;
                },
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(child: Text('תאריך: ${_isoDate(_date)}')),
                  TextButton(onPressed: _pickDate, child: const Text('בחר')),
                ],
              ),
              const SizedBox(height: 12),
              SelectField(
                label: 'חשבון',
                value: _accountName.isNotEmpty ? _accountName : null,
                placeholder: 'בחר חשבון',
                enabled: !_saving,
                onTap: () async {
                  if (_activeAccounts.isEmpty) {
                    if (!mounted) return;
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content:
                            Text('אין חשבונות פעילים. הפעל חשבון בדסקטופ ואז סנכרן.'),
                      ),
                    );
                    return;
                  }
                  final picked = await showStringPickerBottomSheet(
                    context: context,
                    title: 'בחירת חשבון',
                    items: _activeAccounts,
                    selected:
                        _accountName.isNotEmpty ? _accountName : _activeAccounts.first,
                  );
                  if (picked != null && mounted) {
                    setState(() => _accountName = picked);
                  }
                },
              ),
              const SizedBox(height: 12),
              CategoryPicker(
                isIncome: _isIncome,
                selected: _category,
                onSelected: (c) => setState(() => _category = c),
                service: _categories,
              ),
              if (_error != null) ...[
                const SizedBox(height: 8),
                Text(_error!, style: const TextStyle(color: Colors.red)),
              ],
              const SizedBox(height: 12),
              ElevatedButton(
                onPressed: _saving ? null : _save,
                child: Text(_saving ? '...' : 'שמור'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}


