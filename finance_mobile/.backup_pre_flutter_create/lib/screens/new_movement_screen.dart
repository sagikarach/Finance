import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../models/movement.dart';

class NewMovementScreen extends StatefulWidget {
  const NewMovementScreen({super.key});

  @override
  State<NewMovementScreen> createState() => _NewMovementScreenState();
}

class _NewMovementScreenState extends State<NewMovementScreen> {
  final _formKey = GlobalKey<FormState>();
  final _amountCtrl = TextEditingController();
  final _accountCtrl = TextEditingController();
  final _categoryCtrl = TextEditingController();
  final _descCtrl = TextEditingController();

  DateTime _date = DateTime.now();
  bool _isIncome = false;
  String _type = 'ONE_TIME';
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _amountCtrl.dispose();
    _accountCtrl.dispose();
    _categoryCtrl.dispose();
    _descCtrl.dispose();
    super.dispose();
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
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      setState(() => _error = 'Not logged in');
      return;
    }
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final amount = double.parse(_amountCtrl.text.trim());
      final signedAmount = _isIncome ? amount.abs() : -amount.abs();
      final id = const Uuid().v4();
      final movement = Movement(
        id: id,
        amount: signedAmount,
        date: _isoDate(_date),
        accountName: _accountCtrl.text.trim(),
        category: _categoryCtrl.text.trim(),
        type: _type,
        description: _descCtrl.text.trim().isEmpty ? null : _descCtrl.text.trim(),
        eventId: null,
        deleted: false,
      );

      await FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .collection('movements')
          .doc(id)
          .set(movement.toFirestore(), SetOptions(merge: true));

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
      appBar: AppBar(title: const Text('Add movement')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            children: [
              SegmentedButton<bool>(
                segments: const [
                  ButtonSegment(value: false, label: Text('Expense')),
                  ButtonSegment(value: true, label: Text('Income')),
                ],
                selected: {_isIncome},
                onSelectionChanged: (v) => setState(() => _isIncome = v.first),
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _amountCtrl,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'Amount (positive)'),
                validator: (v) {
                  final s = (v ?? '').trim();
                  if (s.isEmpty) return 'Required';
                  final n = double.tryParse(s);
                  if (n == null) return 'Invalid number';
                  if (n <= 0) return 'Must be > 0';
                  return null;
                },
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(child: Text('Date: ${_isoDate(_date)}')),
                  TextButton(onPressed: _pickDate, child: const Text('Pick')),
                ],
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _accountCtrl,
                decoration: const InputDecoration(labelText: 'Account (free text)'),
                validator: (v) =>
                    (v ?? '').trim().isEmpty ? 'Required' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _categoryCtrl,
                decoration: const InputDecoration(labelText: 'Category (free text)'),
                validator: (v) =>
                    (v ?? '').trim().isEmpty ? 'Required' : null,
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: _type,
                items: const [
                  DropdownMenuItem(value: 'ONE_TIME', child: Text('ONE_TIME')),
                  DropdownMenuItem(value: 'MONTHLY', child: Text('MONTHLY')),
                  DropdownMenuItem(value: 'YEARLY', child: Text('YEARLY')),
                ],
                onChanged: (v) => setState(() => _type = v ?? 'ONE_TIME'),
                decoration: const InputDecoration(labelText: 'Type'),
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _descCtrl,
                decoration: const InputDecoration(labelText: 'Description (optional)'),
              ),
              const SizedBox(height: 12),
              if (_error != null)
                Text(_error!, style: const TextStyle(color: Colors.red)),
              const Spacer(),
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton(
                      onPressed: _loading ? null : _save,
                      child: Text(_loading ? '...' : 'Save'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}


