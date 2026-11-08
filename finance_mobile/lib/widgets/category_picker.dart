import 'package:flutter/material.dart';

import '../models/category_lists.dart';
import '../theme/app_colors.dart';

/// Expense categories as chips grouped by the hierarchy: one chip per
/// category, and its subcategories appear only after pressing that chip's
/// arrow (always visible). Tapping a name selects it — a parent category on
/// its own is a valid choice.
class CategoryHierarchyPicker extends StatefulWidget {
  final CategoryLists lists;
  final List<String> extraNames; // custom names outside the hierarchy
  final String selected;
  final Color accent;
  final ValueChanged<String> onSelected;
  final VoidCallback onAddNew;

  const CategoryHierarchyPicker({
    super.key,
    required this.lists,
    required this.extraNames,
    required this.selected,
    required this.accent,
    required this.onSelected,
    required this.onAddNew,
  });

  @override
  State<CategoryHierarchyPicker> createState() => _CategoryHierarchyPickerState();
}

class _CategoryHierarchyPickerState extends State<CategoryHierarchyPicker> {
  final Set<String> _expanded = <String>{};

  @override
  Widget build(BuildContext context) {
    final lists = widget.lists;
    final selectedParent = lists.parentOf(widget.selected);
    final rows = <Widget>[];
    final singles = <Widget>[];
    for (final p in lists.parents) {
      final children = lists.childrenOf(p.name);
      if (children.isEmpty) {
        singles.add(_chip(p.name, selected: p.name == widget.selected));
        continue;
      }
      final open = _expanded.contains(p.name);
      rows.add(Padding(
        padding: const EdgeInsets.only(bottom: 9),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _parentChip(p.name,
                selected: p.name == widget.selected,
                containsSelection: selectedParent == p.name,
                open: open),
            if (open)
              Padding(
                padding: const EdgeInsetsDirectional.only(start: 22, top: 9),
                child: Wrap(
                  spacing: 9,
                  runSpacing: 9,
                  children: [
                    for (final c in children)
                      _chip(c.name, selected: c.name == widget.selected),
                  ],
                ),
              ),
          ],
        ),
      ));
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ...rows,
        Wrap(
          spacing: 9,
          runSpacing: 9,
          children: [
            ...singles,
            for (final c in widget.extraNames)
              _chip(c, selected: c == widget.selected),
            _chip('＋ חדש', selected: false, onTap: widget.onAddNew),
          ],
        ),
      ],
    );
  }

  BoxDecoration _decoration({required bool selected, bool outline = false}) {
    return BoxDecoration(
      color: selected ? widget.accent : AppColors.card,
      borderRadius: BorderRadius.circular(14),
      border: Border.all(
          color: (selected || outline) ? widget.accent : AppColors.line, width: 1.5),
      boxShadow: selected
          ? null
          : const [
              BoxShadow(color: Color(0x12141910), blurRadius: 14, offset: Offset(0, 6))
            ],
    );
  }

  Widget _chip(String label, {required bool selected, VoidCallback? onTap}) {
    return GestureDetector(
      onTap: onTap ?? () => widget.onSelected(label),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        decoration: _decoration(selected: selected),
        child: Text(label,
            style: TextStyle(
                fontSize: 13.5,
                fontWeight: FontWeight.w700,
                color: selected ? Colors.white : const Color(0xFF4A4D45))),
      ),
    );
  }

  Widget _parentChip(String name,
      {required bool selected, required bool containsSelection, required bool open}) {
    final fg = selected ? Colors.white : const Color(0xFF4A4D45);
    return Container(
      decoration: _decoration(selected: selected, outline: containsSelection),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: () => widget.onSelected(name),
            child: Padding(
              padding: const EdgeInsetsDirectional.fromSTEB(14, 9, 6, 9),
              child: Text(name,
                  style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800, color: fg)),
            ),
          ),
          GestureDetector(
            key: ValueKey('expand:$name'),
            behavior: HitTestBehavior.opaque,
            onTap: () => setState(() {
              if (!_expanded.remove(name)) _expanded.add(name);
            }),
            child: Padding(
              padding: const EdgeInsetsDirectional.fromSTEB(4, 6, 10, 6),
              child: Icon(
                open ? Icons.keyboard_arrow_down_rounded : Icons.keyboard_arrow_left_rounded,
                // a true "left" (toward the next chip), not mirrored in RTL
                textDirection: TextDirection.ltr,
                size: 24,
                color: fg,
                semanticLabel: open ? 'סגור תתי־קטגוריות' : 'הצג תתי־קטגוריות',
              ),
            ),
          ),
        ],
      ),
    );
  }
}
