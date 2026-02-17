import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:fl_chart/fl_chart.dart';

class CompareScreen extends StatefulWidget {
  const CompareScreen({super.key});

  @override
  State<CompareScreen> createState() => _CompareScreenState();
}

class _CompareScreenState extends State<CompareScreen> {
  // Using ADB reverse:
  // adb reverse tcp:8000 tcp:8000
  static const String baseUrl = "http://127.0.0.1:8000";

  bool loading = true;
  String error = "";

  // FULL data from API
  List<double> _allBalance = [];
  List<double> _allSpeed = [];
  List<String> _allLabels = [];

  // FILTERED data to show on UI
  List<double> balance = [];
  List<double> speed = [];
  List<String> labels = [];

  // Filter options
  final List<int> _filterOptions = [-1, 5, 10, 15]; // -1 = All
  int _selectedN = -1;

  // Touch info
  String touchedLabel = "";
  double? touchedBalance;
  double? touchedSpeed;

  @override
  void initState() {
    super.initState();
    fetchSessions();
  }

  double _toDouble(dynamic v) {
    if (v == null) return 0.0;
    if (v is num) return v.toDouble();
    if (v is String) return double.tryParse(v) ?? 0.0;
    return 0.0;
  }

  String _toLabel(dynamic v) {
    if (v == null) return "--";
    final s = v.toString();
    // If looks like ISO date: 2026-02-17 -> show 02-17
    if (s.length >= 10 && s.contains('-')) return s.substring(5, 10);
    return s;
  }

  double _extractMetric(Map<String, dynamic> s, String metricKey) {
    final metrics = s["metrics"];
    if (metrics is Map) return _toDouble(metrics[metricKey]);
    return 0.0;
  }

  List<Map<String, dynamic>> _asSessionList(dynamic raw) {
    if (raw is List) {
      return raw
          .whereType<Map>()
          .map((m) => Map<String, dynamic>.from(m))
          .toList();
    }
    if (raw is Map) {
      final entries = raw.entries.toList();
      entries.sort((a, b) {
        final ai = int.tryParse(a.key.toString());
        final bi = int.tryParse(b.key.toString());
        if (ai != null && bi != null) return ai.compareTo(bi);
        return a.key.toString().compareTo(b.key.toString());
      });
      return entries
          .map((e) => e.value)
          .whereType<Map>()
          .map((m) => Map<String, dynamic>.from(m))
          .toList();
    }
    return [];
  }

  String _extractLabel(Map<String, dynamic> s, int index) {
    if (s.containsKey("date")) return _toLabel(s["date"]);
    if (s.containsKey("created_at")) return _toLabel(s["created_at"]);
    if (s.containsKey("session_id")) return s["session_id"].toString();
    if (s.containsKey("id")) return s["id"].toString();
    return "S${index + 1}";
  }

  void _applyFilter() {
    final total = _allLabels.length;
    int start = 0;

    if (_selectedN != -1) {
      start = (total - _selectedN);
      if (start < 0) start = 0;
    }

    labels = _allLabels.sublist(start);
    balance = _allBalance.sublist(start);
    speed = _allSpeed.sublist(start);

    // reset touch when filter changes
    touchedLabel = "";
    touchedBalance = null;
    touchedSpeed = null;
  }

  String _pctChangeText(List<double> arr) {
    if (arr.length < 2) return "--";
    final first = arr.first;
    final last = arr.last;
    if (first == 0) return "--";
    final pct = ((last - first) / first) * 100.0;
    final sign = pct >= 0 ? "+" : "";
    return "$sign${pct.toStringAsFixed(1)}%";
  }

  Future<void> fetchSessions() async {
    setState(() {
      loading = true;
      error = "";

      _allBalance = [];
      _allSpeed = [];
      _allLabels = [];

      balance = [];
      speed = [];
      labels = [];

      touchedLabel = "";
      touchedBalance = null;
      touchedSpeed = null;
    });

    try {
      final url = Uri.parse("$baseUrl/sessions?player_id=P1");
      final res = await http.get(url).timeout(const Duration(seconds: 20));

      if (res.statusCode != 200) {
        throw Exception("Server error ${res.statusCode}: ${res.body}");
      }

      final body = res.body.trim();
      if (body.startsWith("<")) {
        throw Exception("Backend returned HTML/text, not JSON. Check baseUrl/adb reverse.");
      }

      final decoded = jsonDecode(body);

      dynamic rawSessions;
      if (decoded is Map) {
        rawSessions = decoded["sessions"];
      } else if (decoded is List) {
        rawSessions = decoded;
      } else {
        throw Exception("Unexpected response format (not JSON object/list).");
      }

      final sessions = _asSessionList(rawSessions);
      if (sessions.isEmpty) throw Exception("No sessions found from API.");

      for (int i = 0; i < sessions.length; i++) {
        final s = sessions[i];

        // ✅ STEP 6: read metric keys
        _allBalance.add(_extractMetric(s, "balance_score"));
        _allSpeed.add(_extractMetric(s, "speed_score"));

        _allLabels.add(_extractLabel(s, i));
      }

      _applyFilter();
    } catch (e) {
      error = "Exception: $e";
    }

    setState(() => loading = false);
  }

  List<FlSpot> _spots(List<double> arr) =>
      List.generate(arr.length, (i) => FlSpot(i.toDouble(), arr[i]));

  double _maxY() {
    final all = <double>[...balance, ...speed];
    if (all.isEmpty) return 100;
    final m = all.reduce((a, b) => a > b ? a : b);
    return m < 100 ? 100 : m;
  }

  Widget _legendDot(Color c) => Container(
        width: 10,
        height: 10,
        decoration: BoxDecoration(color: c, shape: BoxShape.circle),
      );

  @override
  Widget build(BuildContext context) {
    final latestBalance = balance.isNotEmpty ? balance.last.toStringAsFixed(1) : "--";
    final latestSpeed = speed.isNotEmpty ? speed.last.toStringAsFixed(1) : "--";

    final balanceImprove = _pctChangeText(balance);
    final speedImprove = _pctChangeText(speed);

    return Scaffold(
      appBar: AppBar(
        title: const Text("Performance Analytics"),
        actions: [
          IconButton(
            onPressed: fetchSessions,
            icon: const Icon(Icons.refresh),
            tooltip: "Reload",
          )
        ],
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : error.isNotEmpty
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text(
                      error,
                      style: const TextStyle(color: Colors.red),
                      textAlign: TextAlign.center,
                    ),
                  ),
                )
              : Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      // ✅ Filter Dropdown
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            "Sessions shown: ${labels.length}",
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                          DropdownButton<int>(
                            value: _selectedN,
                            items: _filterOptions.map((n) {
                              final text = (n == -1) ? "All" : "Last $n";
                              return DropdownMenuItem<int>(
                                value: n,
                                child: Text(text),
                              );
                            }).toList(),
                            onChanged: (v) {
                              if (v == null) return;
                              setState(() {
                                _selectedN = v;
                                _applyFilter();
                              });
                            },
                          ),
                        ],
                      ),

                      const SizedBox(height: 8),

                      // ✅ Legend
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          _legendDot(Colors.blue),
                          const SizedBox(width: 6),
                          const Text("Balance"),
                          const SizedBox(width: 18),
                          _legendDot(Colors.orange),
                          const SizedBox(width: 6),
                          const Text("Speed"),
                        ],
                      ),

                      const SizedBox(height: 10),

                      // ✅ Summary row: latest + improvement %
                      Text(
                        "Latest → Balance: $latestBalance | Speed: $latestSpeed",
                        style: const TextStyle(fontWeight: FontWeight.w600),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        "Improvement (first→last in range) → Balance: $balanceImprove | Speed: $speedImprove",
                        textAlign: TextAlign.center,
                      ),

                      const SizedBox(height: 10),

                      // Touch readout
                      if (touchedBalance != null || touchedSpeed != null)
                        Text(
                          "Selected: $touchedLabel | Balance: ${touchedBalance?.toStringAsFixed(1) ?? '--'} | Speed: ${touchedSpeed?.toStringAsFixed(1) ?? '--'}",
                          textAlign: TextAlign.center,
                        )
                      else
                        const Text(
                          "Tip: Tap/drag on the graph to see values",
                          textAlign: TextAlign.center,
                        ),

                      const SizedBox(height: 12),

                      // ✅ STEP 7: Two lines
                      SizedBox(
                        height: 260,
                        child: LineChart(
                          LineChartData(
                            minY: 0,
                            maxY: _maxY(),
                            gridData: const FlGridData(show: true),
                            borderData: FlBorderData(show: true),

                            // ✅ STEP 8: touch handling
                            lineTouchData: LineTouchData(
                              enabled: true,
                              handleBuiltInTouches: true,
                              touchSpotThreshold: 30,
                              touchCallback: (event, response) {
                                final spots = response?.lineBarSpots;
                                if (spots == null || spots.isEmpty) return;

                                final i = spots.first.x.toInt();
                                if (i < 0 || i >= labels.length) return;

                                setState(() {
                                  touchedLabel = labels[i];
                                  touchedBalance = balance[i];
                                  touchedSpeed = speed[i];
                                });
                              },
                              touchTooltipData: LineTouchTooltipData(
                                getTooltipItems: (touchedSpots) {
                                  // show only ONE tooltip (combined) using index
                                  if (touchedSpots.isEmpty) return [];
                                  final i = touchedSpots.first.x.toInt();
                                  if (i < 0 || i >= labels.length) return [];
                                  return [
                                    LineTooltipItem(
                                      "${labels[i]}\nBalance: ${balance[i].toStringAsFixed(1)}\nSpeed: ${speed[i].toStringAsFixed(1)}",
                                      const TextStyle(fontSize: 12),
                                    )
                                  ];
                                },
                              ),
                            ),

                            titlesData: FlTitlesData(
                              leftTitles: const AxisTitles(
                                sideTitles: SideTitles(showTitles: true),
                              ),
                              bottomTitles: AxisTitles(
                                sideTitles: SideTitles(
                                  showTitles: true,
                                  interval: labels.length > 8 ? 2 : 1,
                                  getTitlesWidget: (value, meta) {
                                    final i = value.toInt();
                                    if (i >= 0 && i < labels.length) {
                                      return Padding(
                                        padding: const EdgeInsets.only(top: 6),
                                        child: Text(
                                          labels[i],
                                          style: const TextStyle(fontSize: 10),
                                        ),
                                      );
                                    }
                                    return const SizedBox.shrink();
                                  },
                                ),
                              ),
                              topTitles: const AxisTitles(
                                sideTitles: SideTitles(showTitles: false),
                              ),
                              rightTitles: const AxisTitles(
                                sideTitles: SideTitles(showTitles: false),
                              ),
                            ),

                            lineBarsData: [
                              LineChartBarData(
                                spots: _spots(balance),
                                isCurved: true,
                                color: Colors.blue,
                                barWidth: 3,
                                dotData: const FlDotData(show: true),
                                belowBarData: BarAreaData(show: false),
                              ),
                              LineChartBarData(
                                spots: _spots(speed),
                                isCurved: true,
                                color: Colors.orange,
                                barWidth: 3,
                                dotData: const FlDotData(show: true),
                                belowBarData: BarAreaData(show: false),
                              ),
                            ],
                          ),
                        ),
                      ),

                      const SizedBox(height: 12),

                      Expanded(
                        child: ListView.separated(
                          itemCount: labels.length,
                          separatorBuilder: (_, __) => const Divider(height: 1),
                          itemBuilder: (context, i) {
                            return ListTile(
                              dense: true,
                              title: Text("Session ${i + 1} (${labels[i]})"),
                              subtitle: Text(
                                "Balance: ${balance[i].toStringAsFixed(1)} | Speed: ${speed[i].toStringAsFixed(1)}",
                              ),
                              onTap: () {
                                setState(() {
                                  touchedLabel = labels[i];
                                  touchedBalance = balance[i];
                                  touchedSpeed = speed[i];
                                });
                              },
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
