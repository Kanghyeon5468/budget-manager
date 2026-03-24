import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

const String defaultBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://127.0.0.1:8000',
);

void main() {
  runApp(const BudgetApp());
}

class BudgetApp extends StatelessWidget {
  const BudgetApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Budget Manager',
      theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue)),
      home: const ExpenseScreen(),
    );
  }
}

class ExpenseScreen extends StatefulWidget {
  const ExpenseScreen({super.key});

  @override
  State<ExpenseScreen> createState() => _ExpenseScreenState();
}

class _ExpenseScreenState extends State<ExpenseScreen> {
  final TextEditingController _rawInputController = TextEditingController();
  final TextEditingController _amountController = TextEditingController();
  final TextEditingController _categoryController = TextEditingController();
  final TextEditingController _descriptionController = TextEditingController();

  String _activeBaseUrl = defaultBaseUrl;
  String _currentCurrency = 'GBP';
  String _rawInput = '';
  bool _loading = false;
  List<Map<String, dynamic>> _records = [];

  @override
  void initState() {
    super.initState();
    _initializeBackendConnection();
  }

  @override
  void dispose() {
    _rawInputController.dispose();
    _amountController.dispose();
    _categoryController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Uri _uri(String path) => Uri.parse('$_activeBaseUrl$path');

  Future<void> _initializeBackendConnection() async {
    final rawCandidates = [
      defaultBaseUrl,
      'http://127.0.0.1:8000',
      'http://localhost:8000',
      'http://10.0.2.2:8000',
    ];
    final seen = <String>{};
    final candidates = rawCandidates.where(seen.add).toList();

    for (final baseUrl in candidates) {
      try {
        final response = await http
            .get(Uri.parse('$baseUrl/api/health'))
            .timeout(const Duration(seconds: 2));
        if (response.statusCode == 200) {
          setState(() => _activeBaseUrl = baseUrl);
          await _loadRecords();
          return;
        }
      } catch (_) {
        // Try next candidate.
      }
    }
    _showMessage('Cannot connect to backend.');
  }

  Future<void> _loadRecords() async {
    try {
      final response = await http.get(_uri('/api/records'));
      if (response.statusCode != 200) {
        _showMessage('Failed to load records.');
        return;
      }
      final decoded = jsonDecode(response.body) as List<dynamic>;
      setState(() {
        _records = decoded.map((e) => Map<String, dynamic>.from(e as Map)).toList();
      });
    } catch (_) {
      _showMessage('Cannot connect to backend.');
    }
  }

  Future<void> _preview() async {
    final text = _rawInputController.text.trim();
    if (text.isEmpty) {
      _showMessage('Please enter expense text.');
      return;
    }
    setState(() => _loading = true);

    try {
      final response = await http.post(
        _uri('/api/preview'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'expense_text': text, 'preferred_currency': _currentCurrency}),
      );
      final decoded = jsonDecode(response.body) as Map<String, dynamic>;
      if (response.statusCode != 200) {
        _showMessage(decoded['error']?.toString() ?? 'Preview failed.');
        return;
      }

      setState(() {
        _amountController.text = decoded['amount']?.toString() ?? '';
        final parsedCurrency = decoded['currency']?.toString().toUpperCase() ?? _currentCurrency;
        if (parsedCurrency == 'GBP' || parsedCurrency == 'KRW') {
          _currentCurrency = parsedCurrency;
        }
        _categoryController.text = decoded['category']?.toString() ?? 'Lifestyle';
        _descriptionController.text = decoded['description']?.toString() ?? 'General expense';
        _rawInput = decoded['raw_input']?.toString() ?? text;
      });
      _showMessage('Classification ready.');
    } catch (_) {
      _showMessage('Preview failed. Check backend connection.');
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _confirm() async {
    if (_amountController.text.trim().isEmpty) {
      _showMessage('Amount is required.');
      return;
    }
    setState(() => _loading = true);

    try {
      final response = await http.post(
        _uri('/api/confirm'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'amount': _amountController.text.trim(),
          'currency': _currentCurrency,
          'category': _categoryController.text.trim(),
          'description': _descriptionController.text.trim(),
          'raw_input': _rawInput,
          'source': 'app',
        }),
      );
      final decoded = jsonDecode(response.body) as Map<String, dynamic>;
      if (response.statusCode != 200) {
        _showMessage(decoded['error']?.toString() ?? 'Save failed.');
        return;
      }

      setState(() {
        _amountController.clear();
        _categoryController.clear();
        _descriptionController.clear();
        _rawInputController.clear();
        _rawInput = '';
      });
      _showMessage('Saved successfully.');
      await _loadRecords();
    } catch (_) {
      _showMessage('Save failed. Check backend connection.');
    } finally {
      setState(() => _loading = false);
    }
  }

  void _resetForm() {
    setState(() {
      _rawInputController.clear();
      _amountController.clear();
      _categoryController.clear();
      _descriptionController.clear();
      _rawInput = '';
    });
    _showMessage('Form reset.');
  }

  Future<void> _clearAllRecords() async {
    final shouldClear = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Clear all records?'),
          content: const Text('This will permanently delete all expense records.'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Delete All'),
            ),
          ],
        );
      },
    );
    if (shouldClear != true) {
      return;
    }

    setState(() => _loading = true);
    try {
      final response = await http.post(_uri('/api/reset'));
      if (response.statusCode != 200) {
        _showMessage('Failed to clear records.');
        return;
      }
      _resetForm();
      await _loadRecords();
      _showMessage('All records deleted.');
    } catch (_) {
      _showMessage('Failed to clear records.');
    } finally {
      setState(() => _loading = false);
    }
  }

  void _showMessage(String message) {
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Budget Manager'),
        actions: [
          PopupMenuButton<String>(
            initialValue: _currentCurrency,
            onSelected: (value) {
              setState(() => _currentCurrency = value);
              _showMessage('Currency set to $value.');
            },
            itemBuilder: (context) => const [
              PopupMenuItem(value: 'GBP', child: Text('GBP')),
              PopupMenuItem(value: 'KRW', child: Text('KRW')),
            ],
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              child: Center(
                child: Text(
                  'Currency: $_currentCurrency',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
            ),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            TextField(
              controller: _rawInputController,
              decoration: const InputDecoration(
                labelText: 'Step 1 - Expense input',
                hintText: 'e.g. 30 GBP food',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed: _loading ? null : _preview,
                    child: const Text('Classify with AI'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _amountController,
                    decoration: const InputDecoration(labelText: 'Amount', border: OutlineInputBorder()),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _categoryController,
                    decoration: const InputDecoration(labelText: 'Category', border: OutlineInputBorder()),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    controller: _descriptionController,
                    decoration: const InputDecoration(labelText: 'Description', border: OutlineInputBorder()),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed: _loading ? null : _confirm,
                    child: const Text('Step 2 - Confirm and Save'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: _loading ? null : _resetForm,
                    child: const Text('Reset Form'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: FilledButton.tonal(
                    onPressed: _loading ? null : _clearAllRecords,
                    child: const Text('Clear All Records'),
                  ),
                ),
              ],
            ),
            const Divider(height: 20),
            Expanded(
              child: RefreshIndicator(
                onRefresh: _loadRecords,
                child: ListView.builder(
                  itemCount: _records.length,
                  itemBuilder: (context, index) {
                    final row = _records[index];
                    return ListTile(
                      title: Text('${row['amount']} ${row['currency']} - ${row['category']}'),
                      subtitle: Text('${row['date']} | ${row['description']}'),
                    );
                  },
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
