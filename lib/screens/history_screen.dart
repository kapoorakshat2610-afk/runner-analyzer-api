import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:fl_chart/fl_chart.dart';
import 'result_screen.dart';
import 'athlete_dashboard.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<Map<String, dynamic>> history = [];

  String selectedAthlete = "All";
  List<String> athleteList = ["All"];

  double _toDouble(dynamic v) {
    if (v == null) return 0.0;
    return double.tryParse(v.toString()) ?? 0.0;
  }

  Color _levelColor(String level) {
    final l = level.toLowerCase();
    if (l == "beginner") return Colors.red;
    if (l == "intermediate") return Colors.orange;
    if (l == "advanced") return Colors.green;
    return Colors.grey;
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

  List<Map<String, dynamic>> get filteredHistory {
    if (selectedAthlete == "All") return history;
    return history
        .where((e) => (e["athlete"]?.toString() ?? "Unknown") == selectedAthlete)
        .toList();
  }

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    final prefs = await SharedPreferences.getInstance();
    final list = prefs.getStringList("history") ?? [];

    final parsed = <Map<String, dynamic>>[];
    for (final item in list) {
      try {
        final decoded = jsonDecode(item);
        parsed.add(Map<String, dynamic>.from(decoded));
      } catch (_) {}
    }

    final names = parsed
        .map((e) => e["athlete"]?.toString() ?? "Unknown")
        .toSet()
        .toList();

    names.sort();
    names.insert(0, "All");

    setState(() {
      history = parsed;
      athleteList = names;

      if (!athleteList.contains(selectedAthlete)) {
        selectedAthlete = "All";
      }
    });
  }

  Future<void> _clearHistory() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove("history");

    setState(() {
      history = [];
      athleteList = ["All"];
      selectedAthlete = "All";
    });
  }

  Widget _buildGraph() {
    final dataList = filteredHistory;

    if (dataList.length < 2) {
      return const SizedBox(
        height: 200,
        child: Center(
          child: Text("Add more sessions to see the graph."),
        ),
      );
    }

    final spots = dataList.asMap().entries.map((e) {
      final data = Map<String, dynamic>.from(e.value["data"] ?? {});
      final score = _calcScore(data);
      return FlSpot(e.key.toDouble(), score.toDouble());
    }).toList();

    return SizedBox(
      height: 200,
      child: LineChart(
        LineChartData(
          titlesData: FlTitlesData(show: false),
          borderData: FlBorderData(show: false),
          gridData: FlGridData(show: false),
          lineBarsData: [
            LineChartBarData(
              isCurved: true,
              barWidth: 4,
              dotData: FlDotData(show: true),
              spots: spots,
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (history.isEmpty) {
      return Scaffold(
        appBar: AppBar(
          title: const Text("History"),
          actions: [
            IconButton(
              icon: const Icon(Icons.delete),
              onPressed: _clearHistory,
            ),
          ],
        ),
        body: const Center(
          child: Text("No history yet."),
        ),
      );
    }

    final listToShow = filteredHistory;

    return Scaffold(
      appBar: AppBar(
        title: const Text("History"),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadHistory,
          ),
          IconButton(
            icon: const Icon(Icons.delete),
            onPressed: _clearHistory,
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [

            // Athlete Dropdown
            Row(
              children: [
                const Text("Athlete: "),
                const SizedBox(width: 10),
                Expanded(
                  child: DropdownButton<String>(
                    value: selectedAthlete,
                    isExpanded: true,
                    items: athleteList
                        .map((name) => DropdownMenuItem(
                              value: name,
                              child: Text(name),
                            ))
                        .toList(),
                    onChanged: (val) {
                      if (val == null) return;
                      setState(() {
                        selectedAthlete = val;
                      });
                    },
                  ),
                ),
              ],
            ),

            const SizedBox(height: 10),

            // Dashboard Button
            if (selectedAthlete != "All")
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  icon: const Icon(Icons.person),
                  label: const Text("Open Athlete Dashboard"),
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) =>
                            AthleteDashboard(athlete: selectedAthlete),
                      ),
                    );
                  },
                ),
              ),

            const SizedBox(height: 12),

            // Graph
            _buildGraph(),

            const SizedBox(height: 12),

            // History List
            Expanded(
              child: ListView.builder(
                itemCount: listToShow.length,
                itemBuilder: (context, index) {
                  final entry = listToShow[index];

                  final time = entry["time"]?.toString() ?? "";
                  final athlete = entry["athlete"]?.toString() ?? "Unknown";

                  final data = Map<String, dynamic>.from(entry["data"] ?? {});
                  final knee = data["average_knee_angle"]?.toString() ?? "N/A";
                  final level = (data["performance_level"] ?? "unknown").toString();
                  final score = _calcScore(data);

                  final badgeColor = _levelColor(level);

                  return Card(
                    margin: const EdgeInsets.symmetric(vertical: 6),
                    child: ListTile(
                      leading: CircleAvatar(
                        child: Text(score.toString()),
                      ),
                      title: Text(athlete),
                      subtitle: Text("Knee: $knee°\n$time"),
                      trailing: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: badgeColor.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(999),
                          border: Border.all(color: badgeColor),
                        ),
                        child: Text(
                          level.toUpperCase(),
                          style: TextStyle(
                            color: badgeColor,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => ResultScreen(resultData: data),
                          ),
                        );
                      },
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
