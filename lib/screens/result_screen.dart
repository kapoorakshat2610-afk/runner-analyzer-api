import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';

class ResultScreen extends StatelessWidget {
  final Map<String, dynamic> resultData;

  const ResultScreen({super.key, required this.resultData});

  double _toDouble(dynamic v, {double fallback = 0.0}) {
    if (v == null) return fallback;
    return double.tryParse(v.toString()) ?? fallback;
  }

  int _toInt(dynamic v, {int fallback = 0}) {
    if (v == null) return fallback;
    return int.tryParse(v.toString()) ?? fallback;
  }

  String _toStr(dynamic v, {String fallback = "N/A"}) {
    if (v == null) return fallback;
    final s = v.toString().trim();
    return s.isEmpty ? fallback : s;
  }

  List<String> _toStringList(dynamic v) {
    if (v is List) {
      return v.map((e) => e.toString()).toList();
    }
    return [];
  }

  Color _levelColor(String level) {
    final l = level.toLowerCase();
    if (l == "beginner") return Colors.red;
    if (l == "intermediate") return Colors.orange;
    if (l == "advanced") return Colors.green;
    return Colors.grey;
  }

  Future<void> _generatePdf(
    BuildContext context, {
    required String performance,
    required double score,
    required double kneeAngle,
    required double diff,
    required double ideal,
    required bool mlUsed,
    required String source,
    required List<String> mistakes,
    required List<String> suggestions,
    int? framesAnalyzed,
    double? confidence,
  }) async {
    final pdf = pw.Document();

    pdf.addPage(
      pw.Page(
        build: (pw.Context ctx) {
          return pw.Column(
            crossAxisAlignment: pw.CrossAxisAlignment.start,
            children: [
              pw.Text(
                "Runner Analysis Report",
                style: pw.TextStyle(fontSize: 22),
              ),
              pw.SizedBox(height: 16),
              pw.Text("Overall Score: ${score.toStringAsFixed(1)}"),
              pw.Text("Performance Level: ${performance.toUpperCase()}"),
              pw.SizedBox(height: 12),
              pw.Text("Average Knee Angle: ${kneeAngle.toStringAsFixed(1)}°"),
              pw.Text("Ideal Knee Angle: ${ideal.toStringAsFixed(0)}°"),
              pw.Text("Difference from Ideal: ${diff.toStringAsFixed(1)}°"),
              pw.SizedBox(height: 12),
              pw.Text("ML Used: ${mlUsed ? "YES" : "NO"}"),
              pw.Text("Source: $source"),
              if (framesAnalyzed != null) pw.Text("Frames Analyzed: $framesAnalyzed"),
              if (confidence != null) pw.Text("Keypoints Confidence: ${confidence.toStringAsFixed(3)}"),
              pw.SizedBox(height: 16),
              pw.Text("Mistakes:", style: pw.TextStyle(fontSize: 14)),
              pw.SizedBox(height: 6),
              ...mistakes.map((m) => pw.Bullet(text: m)),
              pw.SizedBox(height: 12),
              pw.Text("Suggestions:", style: pw.TextStyle(fontSize: 14)),
              pw.SizedBox(height: 6),
              ...suggestions.map((s) => pw.Bullet(text: s)),
            ],
          );
        },
      ),
    );

    await Printing.layoutPdf(
      onLayout: (format) async => pdf.save(),
    );
  }

  @override
  Widget build(BuildContext context) {
    // Backend-first fields
    final double kneeAngle = _toDouble(resultData["average_knee_angle"], fallback: 0);
    final double ideal = _toDouble(resultData["ideal_knee_angle"], fallback: 165);

    final double diff = _toDouble(
      resultData["difference_from_ideal"],
      fallback: (ideal - kneeAngle).abs(),
    );

    final String performance = _toStr(resultData["performance_level"], fallback: "unknown");
    final bool mlUsed = resultData["ml_used"] == true;
    final String source = _toStr(resultData["source"], fallback: "unknown");

    // Prefer backend score if present
    final double computedScore = (() {
      double s = 100 - (diff * 2);
      if (s < 0) s = 0;
      if (s > 100) s = 100;
      return s;
    })();

    final double score = _toDouble(resultData["overall_score"], fallback: computedScore);

    // Backend mistakes/suggestions
    final List<String> mistakes = _toStringList(resultData["mistakes"]);
    final List<String> suggestions = _toStringList(resultData["suggestions"]);

    // Optional backend fields
    final int? framesAnalyzed = resultData["frames_analyzed"] == null
        ? null
        : _toInt(resultData["frames_analyzed"], fallback: 0);

    final double? confidence = resultData["keypoints_confidence"] == null
        ? null
        : _toDouble(resultData["keypoints_confidence"], fallback: 0);

    final Color badgeColor = _levelColor(performance);

    final bool lowConfidence = confidence != null && confidence < 0.35;
    final bool lowFrames = framesAnalyzed != null && framesAnalyzed < 5;

    return Scaffold(
      appBar: AppBar(
        title: const Text("Analysis Report"),
        actions: [
          // Share
          IconButton(
            icon: const Icon(Icons.share),
            onPressed: () {
              final report = "Runner Analyzer Report\n"
                  "Overall Score: ${score.toStringAsFixed(1)}\n"
                  "Performance Level: ${performance.toUpperCase()}\n"
                  "Average Knee Angle: ${kneeAngle.toStringAsFixed(1)}°\n"
                  "Ideal Knee Angle: ${ideal.toStringAsFixed(0)}°\n"
                  "Difference from Ideal: ${diff.toStringAsFixed(1)}°\n"
                  "ML Used: ${mlUsed ? "YES" : "NO"}\n"
                  "Source: $source\n"
                  "${framesAnalyzed != null ? "Frames Analyzed: $framesAnalyzed\n" : ""}"
                  "${confidence != null ? "Keypoints Confidence: ${confidence.toStringAsFixed(3)}\n" : ""}\n"
                  "Mistakes:\n- ${mistakes.isEmpty ? "N/A" : mistakes.join("\n- ")}\n\n"
                  "Suggestions:\n- ${suggestions.isEmpty ? "N/A" : suggestions.join("\n- ")}\n";

              Share.share(report);
            },
          ),

          // PDF
          IconButton(
            icon: const Icon(Icons.picture_as_pdf),
            onPressed: () => _generatePdf(
              context,
              performance: performance,
              score: score,
              kneeAngle: kneeAngle,
              diff: diff,
              ideal: ideal,
              mlUsed: mlUsed,
              source: source,
              mistakes: mistakes.isEmpty ? ["N/A"] : mistakes,
              suggestions: suggestions.isEmpty ? ["N/A"] : suggestions,
              framesAnalyzed: framesAnalyzed,
              confidence: confidence,
            ),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: ListView(
          children: [
            // ✅ Confidence banner
            if (lowConfidence || lowFrames)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(
                    children: [
                      const Icon(Icons.warning_amber_rounded),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          lowFrames
                              ? "Very few frames analyzed. Try a longer, clearer side-view video."
                              : "Low pose detection confidence. For best results: side-view, full body visible, good lighting, stable camera.",
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

            if (lowConfidence || lowFrames) const SizedBox(height: 12),

            // SCORE CARD
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    SizedBox(
                      width: 110,
                      height: 110,
                      child: Stack(
                        alignment: Alignment.center,
                        children: [
                          CircularProgressIndicator(
                            value: (score.clamp(0, 100)) / 100,
                            strokeWidth: 10,
                          ),
                          Text(
                            score.toStringAsFixed(0),
                            style: const TextStyle(
                              fontSize: 30,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text("Overall Score"),
                          const SizedBox(height: 10),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                            decoration: BoxDecoration(
                              color: badgeColor.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(999),
                              border: Border.all(color: badgeColor),
                            ),
                            child: Text(
                              performance.toUpperCase(),
                              style: TextStyle(
                                color: badgeColor,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                          const SizedBox(height: 10),
                          Text("ML Used: ${mlUsed ? "YES" : "NO"}"),
                          Text("Source: $source"),
                          if (framesAnalyzed != null) Text("Frames: $framesAnalyzed"),
                          if (confidence != null) Text("Confidence: ${confidence.toStringAsFixed(3)}"),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 16),

            // KNEE DATA
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "Knee Mechanics",
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 12),
                    Text("Average Knee Angle: ${kneeAngle.toStringAsFixed(1)}°"),
                    Text("Ideal Knee Angle: ${ideal.toStringAsFixed(0)}°"),
                    Text("Difference from Ideal: ${diff.toStringAsFixed(1)}°"),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 16),

            // MISTAKES
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "Mistakes",
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 10),
                    if (mistakes.isEmpty)
                      const Text("• N/A")
                    else
                      for (final m in mistakes) Text("• $m"),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 16),

            // SUGGESTIONS
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "Suggestions",
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 10),
                    if (suggestions.isEmpty)
                      const Text("• N/A")
                    else
                      for (final s in suggestions) Text("• $s"),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
