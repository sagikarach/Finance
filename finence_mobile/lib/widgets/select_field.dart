import 'package:flutter/material.dart';

class SelectField extends StatelessWidget {
  final String label;
  final String? value;
  final String placeholder;
  final bool enabled;
  final VoidCallback onTap;

  const SelectField({
    super.key,
    required this.label,
    required this.value,
    required this.placeholder,
    required this.onTap,
    this.enabled = true,
  });

  @override
  Widget build(BuildContext context) {
    final text = (value == null || value!.trim().isEmpty) ? placeholder : value!;
    final isPlaceholder = (value == null || value!.trim().isEmpty);

    return InkWell(
      onTap: enabled ? onTap : null,
      borderRadius: BorderRadius.circular(12),
      child: InputDecorator(
        decoration: InputDecoration(
          labelText: label,
          suffixIcon: const Icon(Icons.keyboard_arrow_down),
          enabled: enabled,
        ),
        child: Text(
          text,
          style: TextStyle(
            color: isPlaceholder
                ? Theme.of(context).hintColor
                : Theme.of(context).textTheme.bodyMedium?.color,
            fontWeight: isPlaceholder ? FontWeight.w400 : FontWeight.w600,
          ),
        ),
      ),
    );
  }
}

Future<String?> showStringPickerBottomSheet({
  required BuildContext context,
  required String title,
  required List<String> items,
  String? selected,
}) {
  return showModalBottomSheet<String>(
    context: context,
    showDragHandle: true,
    isScrollControlled: true,
    builder: (ctx) {
      return SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                title,
                style: Theme.of(ctx).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: 12),
              Flexible(
                child: Card(
                  child: ListView.separated(
                    shrinkWrap: true,
                    itemCount: items.length,
                    separatorBuilder: (_, __) =>
                        Divider(height: 1, color: Colors.black.withValues(alpha: 0.06)),
                    itemBuilder: (context, i) {
                      final it = items[i];
                      final isSel = it == selected;
                      return ListTile(
                        title: Text(it),
                        trailing: isSel ? const Icon(Icons.check) : null,
                        onTap: () => Navigator.of(ctx).pop(it),
                      );
                    },
                  ),
                ),
              ),
            ],
          ),
        ),
      );
    },
  );
}


