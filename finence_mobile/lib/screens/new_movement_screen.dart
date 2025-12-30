import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../models/movement.dart';
import '../constants/accounts.dart';
import '../services/categories_service.dart';
import '../services/accounts_meta_service.dart';
import '../services/bootstrap_service.dart';
import '../services/movements_service.dart';
import '../services/action_history_service.dart';
import '../services/session_service.dart';
import '../widgets/select_field.dart';
import '../widgets/category_picker.dart';

class NewMovementScreen extends StatefulWidget {
  final String workspaceId;

  const NewMovementScreen({super.key, required this.workspaceId});

  @override
  State<NewMovementScreen> createState() => _NewMovementScreenState();
}

class _NewMovementScreenState extends State<NewMovementScreen> {
  final _formKey = GlobalKey<FormState>();
  final _amountCtrl = TextEditingController();
  final _descCtrl = TextEditingController();

  DateTime _date = DateTime.now();
  bool _isIncome = false;
  String _type = 'ONE_TIME';
  String _accountName = '';
  List<String> _activeAccounts = <String>[];
  String _category = '';
  bool _loading = false;
  String? _error;
  late final CategoriesService _categoriesService;
  late final AccountsMetaService _accountsMeta;
  late final BootstrapService _bootstrap;
  late final MovementsService _movements;
  late final ActionHistoryService _actions;
  final SessionService _session = const SessionService();

  @override
  void initState() {
    super.initState();
    _categoriesService = CategoriesService(workspaceId: widget.workspaceId);
    _accountsMeta = AccountsMetaService(workspaceId: widget.workspaceId);
    _bootstrap = BootstrapService(workspaceId: widget.workspaceId);
    _bootstrap.ensureWorkspaceMeta();
    _movements = MovementsService(workspaceId: widget.workspaceId);
    _actions = ActionHistoryService(workspaceId: widget.workspaceId);
    _loadActiveAccounts();
  }

  @override
  void dispose() {
    _amountCtrl.dispose();
    _descCtrl.dispose();
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
    } catch (_) {
    }
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

  String _isoDate(DateTime d) {
    final mm = d.month.toString().padLeft(2, '0');
    final dd = d.day.toString().padLeft(2, '0');
    return '${d.year}-$mm-$dd';
  }

  Future<void> _save() async {
    if (!_session.isLoggedIn) {
      setState(() => _error = 'לא מחובר');
      return;
    }
    if (!_formKey.currentState!.validate()) return;
    if (_accountName.trim().isEmpty) {
      setState(() => _error = 'אין חשבונות פעילים. הפעל חשבון בהגדרות בדסקטופ ואז סנכרן.');
      return;
    }
    if (_category.trim().isEmpty) {
      setState(() => _error = 'בחר קטגוריה או הוסף חדשה');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final row = await _accountsMeta.fetchBankAccountRow(name: _accountName);
      final isActive = (row?['active'] as bool?) ?? false;
      if (!isActive) {
        if (mounted) {
          setState(() => _error = 'החשבון שנבחר אינו פעיל. הפעל אותו בהגדרות ואז נסה שוב.');
        }
        return;
      }

      final kind = (row?['kind'] as String?)?.trim() ?? '';
      final amount = double.parse(_amountCtrl.text.trim());
      if (kind == 'budget') {
        if (_isIncome) {
          if (mounted) {
            setState(() => _error = 'לא ניתן להוסיף הכנסה לחשבון תקציב');
          }
          return;
        }
        final balance = (row?['total_amount'] as num?)?.toDouble() ?? 0.0;
        if (amount.abs() > balance + 1e-9) {
          if (mounted) {
            setState(() => _error = 'אין מספיק תקציב בחשבון שנבחר');
          }
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
        type: _type,
        description: _descCtrl.text.trim().isEmpty ? null : _descCtrl.text.trim(),
        eventId: null,
        deleted: false,
      );

      await _movements.upsert(movement);
      await _actions.logAddMovement(movementId: id, isIncome: signedAmount > 0);

      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('הוספת תנועה')),
      resizeToAvoidBottomInset: true,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 120),
          child: Form(
            key: _formKey,
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    SegmentedButton<bool>(
                      segments: const [
                        ButtonSegment(value: false, label: Text('הוצאה')),
                        ButtonSegment(value: true, label: Text('הכנסה')),
                      ],
                      selected: {_isIncome},
                      onSelectionChanged: (v) {
                        setState(() {
                          _isIncome = v.first;
                        });
                      },
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _amountCtrl,
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
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
                      value: _accountName.isNotEmpty ? _accountName : Accounts.fixedAccounts.first,
                      placeholder: 'בחר חשבון',
                      onTap: () async {
                        if (_activeAccounts.isEmpty) {
                          if (!mounted) return;
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('אין חשבונות פעילים. הפעל חשבון בדסקטופ ואז סנכרן.'),
                            ),
                          );
                          return;
                        }
                        final picked = await showStringPickerBottomSheet(
                          context: context,
                          title: 'בחירת חשבון',
                          items: _activeAccounts,
                          selected: _accountName.isNotEmpty ? _accountName : _activeAccounts.first,
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
                      service: _categoriesService,
                    ),
                    const SizedBox(height: 12),
                    SelectField(
                      label: 'סוג',
                      value: switch (_type) {
                        'MONTHLY' => 'חודשי',
                        'YEARLY' => 'שנתי',
                        _ => 'חד פעמי',
                      },
                      placeholder: 'בחר סוג',
                      onTap: () async {
                        const items = <String>[
                          'ONE_TIME',
                          'MONTHLY',
                          'YEARLY',
                        ];
                        const labels = <String, String>{
                          'ONE_TIME': 'חד פעמי',
                          'MONTHLY': 'חודשי',
                          'YEARLY': 'שנתי',
                        };
                        final picked = await showStringPickerBottomSheet(
                          context: context,
                          title: 'בחירת סוג',
                          items: items.map((x) => labels[x] ?? x).toList(),
                          selected: labels[_type] ?? _type,
                        );
                        if (picked == null || !mounted) return;
                        final reverse = labels.entries
                            .firstWhere((e) => e.value == picked,
                                orElse: () => const MapEntry('ONE_TIME', 'חד פעמי'))
                            .key;
                        setState(() => _type = reverse);
                      },
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _descCtrl,
                      decoration: const InputDecoration(labelText: 'תיאור (אופציונלי)'),
                    ),
                    if (_error != null) ...[
                      const SizedBox(height: 12),
                      Text(_error!, style: const TextStyle(color: Colors.red)),
                    ],
                  ],
                ),
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
            onPressed: _loading ? null : _save,
            child: Text(_loading ? '...' : 'שמור'),
          ),
        ),
      ),
    );
  }
}


