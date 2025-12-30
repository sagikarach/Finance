import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';

import '../services/categories_service.dart';
import 'select_field.dart';

class CategoryPicker extends StatefulWidget {
  final bool isIncome;
  final String selected;
  final void Function(String) onSelected;
  final CategoriesService service;

  const CategoryPicker({
    super.key,
    required this.isIncome,
    required this.selected,
    required this.onSelected,
    required this.service,
  });

  @override
  State<CategoryPicker> createState() => _CategoryPickerState();
}

class _CategoryPickerState extends State<CategoryPicker> {
  bool _loading = true;
  String? _error;
  List<String> _income = <String>[];
  List<String> _outcome = <String>[];

  @override
  void initState() {
    super.initState();
    _pull(showToast: false);
  }

  Future<void> _pull({required bool showToast}) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final lists = await widget.service.fetch(source: Source.server);
      if (!mounted) return;
      setState(() {
        _income = lists.income;
        _outcome = lists.outcome;
        _loading = false;
      });
      if (showToast) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('קטגוריות סונכרנו')),
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
          SnackBar(content: Text('שגיאת סנכרון קטגוריות: $e')),
        );
      }
    }
  }

  Future<void> _addCategory(BuildContext context) async {
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
            child: const Text('ביטול'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(ctx).pop(ctrl.text),
            child: const Text('הוסף'),
          ),
        ],
      ),
    );
    final n = (name ?? '').trim();
    if (n.isEmpty) return;
    await widget.service.addCategory(isIncome: widget.isIncome, name: n);
    if (!mounted) return;
    setState(() {
      if (widget.isIncome) {
        if (!_income.contains(n)) _income = <String>[..._income, n]..sort();
      } else {
        if (!_outcome.contains(n)) _outcome = <String>[..._outcome, n]..sort();
      }
    });
    widget.onSelected(n);
  }

  @override
  Widget build(BuildContext context) {
    const fallback = <String>[];
    final cats = widget.isIncome ? _income : _outcome;

    Widget dropdownFor(List<String> cats) {
      final list = cats.isNotEmpty ? cats : fallback;
      final sel = list.contains(widget.selected)
          ? widget.selected
          : (list.isNotEmpty ? list.first : '');
      if (list.isEmpty) {
        return const InputDecorator(
          decoration: InputDecoration(
            labelText: 'קטגוריה',
            border: OutlineInputBorder(),
          ),
          child: Text('אין קטגוריות עדיין — לחץ "הוסף קטגוריה"'),
        );
      }
      return SelectField(
        label: 'קטגוריה',
        value: sel,
        placeholder: 'בחר קטגוריה',
        onTap: () async {
          final picked = await showStringPickerBottomSheet(
            context: context,
            title: 'בחירת קטגוריה',
            items: list,
            selected: sel,
          );
          if (picked != null) widget.onSelected(picked);
        },
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            const Expanded(child: SizedBox()),
            IconButton(
              tooltip: 'סנכרן קטגוריות',
              onPressed: _loading ? null : () => _pull(showToast: true),
              icon: _loading
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.sync),
            ),
          ],
        ),
        if (_error != null) ...[
          Text('שגיאה: $_error', style: const TextStyle(color: Colors.red)),
          const SizedBox(height: 8),
        ],
        if (_loading)
          const Center(child: CircularProgressIndicator())
        else
          dropdownFor(cats.isNotEmpty ? cats : fallback),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            onPressed: () => _addCategory(context),
            icon: const Icon(Icons.add),
            label: const Text('הוסף קטגוריה'),
          ),
        ),
      ],
    );
  }
}


