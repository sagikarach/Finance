import 'dart:async';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../models/category_lists.dart';
import '../models/movement.dart';
import '../models/movement_type.dart';
import '../services/categories_service.dart';
import '../services/category_suggester.dart';
import '../services/movements_cache_store.dart';
import '../services/accounts_meta_service.dart';
import '../services/bootstrap_service.dart';
import '../services/movements_service.dart';
import '../services/action_history_service.dart';
import '../services/session_service.dart';
import '../theme/app_colors.dart';
import '../widgets/category_picker.dart';
import '../widgets/select_field.dart';
import '../widgets/ui/cards.dart';

class NewMovementScreen extends StatefulWidget {
  final String workspaceId;

  const NewMovementScreen({super.key, required this.workspaceId});

  @override
  State<NewMovementScreen> createState() => _NewMovementScreenState();
}

class _NewMovementScreenState extends State<NewMovementScreen> {
  final _amountCtrl = TextEditingController();
  final _descCtrl = TextEditingController();

  DateTime _date = DateTime.now();
  bool _isIncome = false;
  String _type = 'ONE_TIME';
  String _accountName = '';
  List<String> _activeAccounts = <String>[];
  String _category = '';
  List<String> _income = <String>[];
  List<String> _outcome = <String>[];
  bool _loading = false;
  String? _error;

  // Category hierarchy + suggestions from past movements (on-device only).
  CategoryLists _lists = const CategoryLists(income: [], outcome: []);
  List<Movement> _history = const [];
  CategorySuggester? _suggester;
  bool? _suggesterIsIncome;
  Timer? _suggestTimer;
  bool _categoryUserSet = false; // a suggestion never overrides the user
  bool _typeUserSet = false;
  bool _categorySuggested = false;
  bool _typeSuggested = false;

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
    _loadCategories();
    _loadHistory();
  }

  @override
  void dispose() {
    _suggestTimer?.cancel();
    _amountCtrl.dispose();
    _descCtrl.dispose();
    super.dispose();
  }

  Color get _accent => _isIncome ? AppColors.green : AppColors.clay;
  Color get _tint => _isIncome ? const Color(0xFFDFF1E7) : const Color(0xFFFBE9E2);
  Color get _amountColor =>
      _isIncome ? const Color(0xFF1F7A4E) : const Color(0xFFB4462B);
  List<String> get _cats => _isIncome ? _income : _outcome;

  Future<void> _loadActiveAccounts() async {
    try {
      final list =
          await _accountsMeta.fetchActiveBankAccountNames(source: Source.server);
      if (!mounted) return;
      setState(() {
        _activeAccounts = list;
        if (_accountName.isEmpty && _activeAccounts.isNotEmpty) {
          _accountName = _activeAccounts.first;
        }
      });
    } catch (_) {}
  }

  Future<void> _loadCategories() async {
    try {
      final lists = await _categoriesService.fetch(source: Source.server);
      if (!mounted) return;
      setState(() {
        _lists = lists;
        _income = lists.income;
        _outcome = lists.outcome;
        if (_category.isEmpty && !_categoryUserSet) _category = _defaultCategory;
        _suggester = null; // categories changed → rebuild on next use
      });
    } catch (_) {}
  }

  /// Past movements already cached on the device (no network): the examples
  /// the category suggestion learns from.
  Future<void> _loadHistory() async {
    try {
      final items = await const MovementsCacheStore()
          .loadMovements(workspaceId: widget.workspaceId);
      if (!mounted) return;
      setState(() {
        _history = items;
        _suggester = null;
      });
    } catch (_) {}
  }

  /// An expense nobody categorized is "טרם סווג", never silently the first
  /// category in the list.
  String get _defaultCategory {
    if (!_isIncome && _lists.byName(CategoryLists.unclassified) != null) {
      return CategoryLists.unclassified;
    }
    return '';
  }

  void _scheduleSuggestion() {
    if (_categoryUserSet && _typeUserSet) return;
    _suggestTimer?.cancel();
    _suggestTimer = Timer(const Duration(milliseconds: 300), _applySuggestion);
  }

  void _applySuggestion() {
    if (!mounted) return;
    if (_suggester == null || _suggesterIsIncome != _isIncome) {
      _suggester = CategorySuggester.fromMovements(
        _history,
        isIncome: _isIncome,
        allowedCategories: _isIncome ? _income : _outcome,
      );
      _suggesterIsIncome = _isIncome;
    }
    final amount = double.tryParse(_amountCtrl.text.trim()) ?? 0;
    final s = _suggester!.suggest(_descCtrl.text, amount);
    setState(() {
      if (s == null) {
        // An earlier suggestion no longer applies: back to the defaults.
        if (_categorySuggested && !_categoryUserSet) _category = _defaultCategory;
        if (_typeSuggested && !_typeUserSet) _type = 'ONE_TIME';
        _categorySuggested = false;
        _typeSuggested = false;
        return;
      }
      if (!_categoryUserSet) {
        _category = s.category;
        _categorySuggested = true;
      }
      if (!_typeUserSet) {
        _type = s.type;
        _typeSuggested = true;
      }
    });
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

  Future<void> _pickAccount() async {
    if (_activeAccounts.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('אין חשבונות פעילים. הפעל חשבון בדסקטופ ואז סנכרן.')),
      );
      return;
    }
    final picked = await showStringPickerBottomSheet(
      context: context,
      title: 'בחירת חשבון',
      items: _activeAccounts,
      selected: _accountName.isNotEmpty ? _accountName : _activeAccounts.first,
    );
    if (picked != null && mounted) setState(() => _accountName = picked);
  }

  Future<void> _pickType() async {
    final picked = await showStringPickerBottomSheet(
      context: context,
      title: 'בחירת סוג',
      items: MovementType.labels.values.toList(),
      selected: MovementType.labels[_type] ?? _type,
    );
    if (picked == null || !mounted) return;
    _typeUserSet = true;
    _typeSuggested = false;
    final reverse = MovementType.labels.entries
        .firstWhere((e) => e.value == picked,
            orElse: () => const MapEntry(MovementType.oneTime, 'חד פעמי'))
        .key;
    setState(() => _type = reverse);
  }

  Future<void> _addCategory() async {
    final ctrl = TextEditingController();
    final name = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('הוספת קטגוריה'),
        content: TextField(
          controller: ctrl,
          autofocus: true,
          decoration: const InputDecoration(hintText: 'שם קטגוריה'),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(ctx).pop(null),
              child: const Text('ביטול')),
          ElevatedButton(
              onPressed: () => Navigator.of(ctx).pop(ctrl.text),
              child: const Text('הוסף')),
        ],
      ),
    );
    final n = (name ?? '').trim();
    if (n.isEmpty) return;
    await _categoriesService.addCategory(isIncome: _isIncome, name: n);
    if (!mounted) return;
    setState(() {
      if (_isIncome) {
        if (!_income.contains(n)) _income = <String>[..._income, n]..sort();
      } else {
        if (!_outcome.contains(n)) _outcome = <String>[..._outcome, n]..sort();
      }
      _category = n;
      _categoryUserSet = true;
      _categorySuggested = false;
    });
  }

  String _isoDate(DateTime d) {
    final mm = d.month.toString().padLeft(2, '0');
    final dd = d.day.toString().padLeft(2, '0');
    return '${d.year}-$mm-$dd';
  }

  static const _hebMonths = [
    'ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני',
    'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר',
  ];
  String _prettyDate(DateTime d) => '${d.day} ב${_hebMonths[d.month - 1]} ${d.year}';

  Future<void> _save() async {
    if (!_session.isLoggedIn) {
      setState(() => _error = 'לא מחובר');
      return;
    }
    final amount = double.tryParse(_amountCtrl.text.trim());
    if (amount == null || amount <= 0) {
      setState(() => _error = 'הזן סכום גדול מ-0');
      return;
    }
    if (_accountName.trim().isEmpty) {
      setState(() => _error =
          'אין חשבונות פעילים. הפעל חשבון בהגדרות בדסקטופ ואז סנכרן.');
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
          setState(() =>
              _error = 'החשבון שנבחר אינו פעיל. הפעל אותו בהגדרות ואז נסה שוב.');
        }
        return;
      }

      final kind = (row?['kind'] as String?)?.trim() ?? '';
      if (kind == 'budget') {
        if (_isIncome) {
          if (mounted) {
            setState(() => _error = 'לא ניתן להוסיף הכנסה לחשבון תקציב');
          }
          return;
        }
        final balance = (row?['total_amount'] as num?)?.toDouble() ?? 0.0;
        if (amount.abs() > balance + 1e-9) {
          if (mounted) setState(() => _error = 'אין מספיק תקציב בחשבון שנבחר');
          return;
        }
      }

      final signedAmount = _isIncome ? amount.abs() : -amount.abs();
      final movement = Movement(
        id: const Uuid().v4(),
        amount: signedAmount,
        date: _isoDate(_date),
        accountName: _accountName,
        category: _category,
        type: _type,
        description:
            _descCtrl.text.trim().isEmpty ? null : _descCtrl.text.trim(),
        eventId: null,
        deleted: false,
      );

      await _movements.upsert(movement);
      await _actions.logAddMovement(m: movement);

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
      backgroundColor: AppColors.screen,
      resizeToAvoidBottomInset: true,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            _topBar(),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(18, 6, 18, 24),
                children: [
                  _toggle(),
                  const SizedBox(height: 16),
                  // What was it? First: the category and type are suggested
                  // from it (and the amount).
                  const Text('תיאור',
                      style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w800,
                          color: AppColors.muted)),
                  const SizedBox(height: 10),
                  _descriptionField(),
                  const SizedBox(height: 16),
                  _amountHero(),
                  const SizedBox(height: 18),
                  _categoryHeader(),
                  const SizedBox(height: 10),
                  _categoryChips(),
                  const SizedBox(height: 18),
                  _fieldsCard(),
                  if (_error != null) ...[
                    const SizedBox(height: 14),
                    Text(_error!,
                        style: const TextStyle(
                            color: AppColors.clay, fontWeight: FontWeight.w600)),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: _saveBar(),
    );
  }

  Widget _topBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 6),
      child: Row(
        children: [
          GestureDetector(
            onTap: () => Navigator.of(context).maybePop(),
            child: Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: const Color(0xFFEFEDE4),
                borderRadius: BorderRadius.circular(13),
              ),
              child: const Icon(Icons.arrow_back_rounded,
                  size: 22, color: AppColors.ink),
            ),
          ),
          const Expanded(
            child: Text('הוספת תנועה',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          ),
          const SizedBox(width: 40),
        ],
      ),
    );
  }

  Widget _toggle() {
    return Container(
      padding: const EdgeInsets.all(5),
      decoration: BoxDecoration(
        color: const Color(0xFFEDEBE3),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          _toggleBtn('הוצאה', !_isIncome, false),
          const SizedBox(width: 5),
          _toggleBtn('הכנסה', _isIncome, true),
        ],
      ),
    );
  }

  Widget _toggleBtn(String label, bool active, bool income) {
    final color = income ? AppColors.green : AppColors.clay;
    return Expanded(
      child: GestureDetector(
        onTap: () {
          if (_isIncome == income) return;
          setState(() {
            _isIncome = income;
            // category lists differ per direction
            _categoryUserSet = false;
            _categorySuggested = false;
            _category = _defaultCategory;
          });
          _scheduleSuggestion();
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          padding: const EdgeInsets.symmetric(vertical: 11),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: active ? color : Colors.transparent,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(label,
              style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w800,
                  color: active ? Colors.white : AppColors.muted)),
        ),
      ),
    );
  }

  Widget _amountHero() {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 18, 20, 20),
      decoration:
          BoxDecoration(color: _tint, borderRadius: BorderRadius.circular(24)),
      child: Column(
        children: [
          const Text('סכום',
              style: TextStyle(
                  fontSize: 12.5,
                  fontWeight: FontWeight.w700,
                  color: AppColors.muted)),
          const SizedBox(height: 4),
          TextField(
            controller: _amountCtrl,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            textAlign: TextAlign.center,
            textDirection: TextDirection.ltr,
            onChanged: (_) {
              if (_error != null) setState(() => _error = null);
              _scheduleSuggestion();
            },
            cursorColor: _amountColor,
            style: TextStyle(
                fontSize: 40,
                fontWeight: FontWeight.w800,
                letterSpacing: -1,
                color: _amountColor),
            decoration: InputDecoration(
              isCollapsed: true,
              border: InputBorder.none,
              hintText: '₪0',
              hintStyle: TextStyle(
                  fontSize: 40,
                  fontWeight: FontWeight.w800,
                  color: _amountColor.withValues(alpha: 0.35)),
              prefixIcon: const SizedBox.shrink(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _fieldsCard() {
    return AppCard(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Column(
        children: [
          _fieldRow(Icons.event_rounded, 'תאריך', _prettyDate(_date), _pickDate),
          _divider(),
          _fieldRow(Icons.account_balance_rounded, 'חשבון',
              _accountName.isEmpty ? 'בחר חשבון' : _accountName, _pickAccount),
          _divider(),
          _fieldRow(Icons.repeat_rounded, 'סוג',
              MovementType.labels[_type] ?? _type, _pickType),
        ],
      ),
    );
  }

  Widget _fieldRow(IconData icon, String label, String value, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
        child: Row(
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                  color: const Color(0xFFF1EFE7),
                  borderRadius: BorderRadius.circular(11)),
              child: Icon(icon, size: 18, color: const Color(0xFF6B6F66)),
            ),
            const SizedBox(width: 12),
            Text(label,
                style: const TextStyle(
                    fontSize: 14.5, fontWeight: FontWeight.w700)),
            const Spacer(),
            Text(value,
                style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF3F423B))),
            const Icon(Icons.chevron_left_rounded,
                color: Color(0xFFC3C5BD), size: 22),
          ],
        ),
      ),
    );
  }

  Widget _divider() => const Divider(
      height: 1, thickness: 1, color: AppColors.line, indent: 12, endIndent: 12);

  Widget _categoryHeader() {
    final parent = _isIncome ? null : _lists.parentOf(_category);
    final chosen = _category.isEmpty
        ? ''
        : (parent != null ? '$parent › $_category' : _category);
    return Row(
      children: [
        const Text('קטגוריה',
            style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w800,
                color: AppColors.muted)),
        const SizedBox(width: 8),
        if (chosen.isNotEmpty)
          Flexible(
            child: Text(chosen,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                    fontSize: 13, fontWeight: FontWeight.w800, color: _accent)),
          ),
        if (_categorySuggested || _typeSuggested) ...[
          const SizedBox(width: 6),
          const Flexible(
            child: Text('✓ מולא לפי תנועות קודמות',
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 12, color: AppColors.muted)),
          ),
        ],
      ],
    );
  }

  void _chooseCategory(String name) {
    setState(() {
      _category = name;
      _categoryUserSet = true;
      _categorySuggested = false;
    });
  }

  Widget _categoryChips() {
    if (_isIncome || !_lists.hasTree) {
      return Wrap(
        spacing: 9,
        runSpacing: 9,
        children: [
          for (final c in _cats)
            _chip(c, selected: c == _category, onTap: () => _chooseCategory(c)),
          _chip('＋ חדש', selected: false, onTap: _addCategory, dashed: true),
        ],
      );
    }
    // Expense hierarchy: subcategories appear only after pressing a
    // category's arrow.
    return CategoryHierarchyPicker(
      lists: _lists,
      extraNames: _outcome
          .where((n) =>
              _lists.byName(n) == null &&
              !_lists.legacyAliases.containsKey(n) &&
              n.trim() != 'העברה')
          .toList(),
      selected: _category,
      accent: _accent,
      onSelected: _chooseCategory,
      onAddNew: _addCategory,
    );
  }

  Widget _chip(String label,
      {required bool selected, required VoidCallback onTap, bool dashed = false}) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        decoration: BoxDecoration(
          color: selected ? _accent : AppColors.card,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
              color: selected ? _accent : AppColors.line, width: 1.5),
          boxShadow: selected
              ? null
              : const [
                  BoxShadow(
                      color: Color(0x12141910),
                      blurRadius: 14,
                      offset: Offset(0, 6))
                ],
        ),
        child: Text(label,
            style: TextStyle(
                fontSize: 13.5,
                fontWeight: FontWeight.w700,
                color: selected ? Colors.white : const Color(0xFF4A4D45))),
      ),
    );
  }

  Widget _descriptionField() {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(16),
        boxShadow: const [
          BoxShadow(
              color: Color(0x14141910), blurRadius: 20, offset: Offset(0, 8))
        ],
      ),
      child: TextField(
        controller: _descCtrl,
        onChanged: (_) => _scheduleSuggestion(),
        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
        decoration: InputDecoration(
          hintText: _isIncome ? 'לדוגמה: משכורת' : 'לדוגמה: סופרפארם לוד',
          hintStyle: const TextStyle(color: AppColors.muted),
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 15),
        ),
      ),
    );
  }

  Widget _saveBar() {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(18, 8, 18, 16),
        child: GestureDetector(
          onTap: _loading ? null : _save,
          child: Container(
            height: 54,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: _loading ? _accent.withValues(alpha: 0.6) : _accent,
              borderRadius: BorderRadius.circular(18),
            ),
            child: Text(
              _loading ? '…' : (_isIncome ? 'שמור הכנסה' : 'שמור הוצאה'),
              style: const TextStyle(
                  color: Colors.white, fontSize: 16, fontWeight: FontWeight.w800),
            ),
          ),
        ),
      ),
    );
  }
}
