import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AthleteDashboard extends StatefulWidget {
  final String athlete;

  const AthleteDashboard({super.key, required this.athlete});

  @override
  State<AthleteDashboard> createState() => _AthleteDashboardState();
}

class _AthleteDashboardState extends State<AthleteDashboard> {
  List<Map<String, dynamic>> sessions = [];

  double _toDouble(dynamic v) {
    if (v == null) return 0.0;
    return double.tryParse(v.toString()) ?? 0.0;
  }

  int _calcScore(Map<String, dynamic> data) {
    const double ideal = 165;
    final knee = _toDouble(data["average_knee_angle"]);
    final diff = (ideal - knee).abs();
    double score = 100 - (diff * 2);
    if (score < 0) score = 0;
    if (score > 100) score = 100;
    return score.round();
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final list = prefs.getStringList("history") ?? [];

    final parsed = <Map<String, dynamic>>[];
    for (final item in list) {
      try {
        final decoded = jsonDecode(item) as Map<String, dynamic>;
        final athlete = (decoded["athlete"] ?? "Unknown").toString();
        if (athlete == widget.athlete) {
          parsed.add(decoded);
        }
      } catch (_) {}
    }

    setState(() => sessions = parsed);
  }

  @override
  Widget build(BuildContext context) {
    if (sessions.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: Text("${widget.athlete} Dashboard")),
        body: const Center(child: Text("No sessions for this athlete yet.")),
      );
    }

    final scores = sessions.map((e) {
      final data = Map<String, dynamic>.from(e["data"] ?? {});
      return _calcScore(data);
    }).toList();

    final total = scores.length;
    final best = scores.reduce((a, b) => a > b ? a : b);
    final latest = scores.first; // newest first in our storage
    final avg = (scores.reduce((a, b) => a + b) / total).round();

    return Scaffold(
      appBar: AppBar(title: Text("${widget.athlete} Dashboard")),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: ListView(
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Text(
                      widget.athlete,
                      style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _stat("Sessions", total.toString()),
                        _stat("Avg", avg.toString()),
                        _stat("Best", best.toString()),
                        _stat("Latest", latest.toString()),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _stat(String label, String value) {
    return Column(
      children: [
        Text(value, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
        const SizedBox(height: 4),
        Text(label),
      ],
    );
  }
}
