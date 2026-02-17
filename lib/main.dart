import 'dart:convert';
import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'screens/result_screen.dart';
import 'screens/history_screen.dart';
import 'screens/compare_screen.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      debugShowCheckedModeBanner: false,
      home: HomeScreen(),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  static const String _baseUrl = "https://runner-analyzer-api-1.onrender.com";

  File? _videoFile;
  bool _isAnalyzing = false;
  Map<String, dynamic>? _result;

  // Athlete
  String _athleteName = "";
  final TextEditingController _nameController = TextEditingController();

  // ---------------- PICK VIDEO ----------------
  Future<void> _pickVideo() async {
    final res = await FilePicker.platform.pickFiles(
      type: FileType.video,
      allowMultiple: false,
    );

    if (res == null || res.files.isEmpty) return;

    final path = res.files.single.path;
    if (path == null) return;

    setState(() {
      _videoFile = File(path);
      _result = null;
    });
  }

  // ---------------- SERVER PING ----------------
  Future<void> _pingServer() async {
    try {
      final r = await http.get(Uri.parse("$_baseUrl/"));

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Server ping: ${r.statusCode}")),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Server error: $e")),
      );
    }
  }

  // ---------------- SAVE HISTORY ----------------
  Future<void> _saveResult(Map<String, dynamic> data) async {
    final prefs = await SharedPreferences.getInstance();

    final entry = jsonEncode({
      "time": DateTime.now().toIso8601String(),
      "athlete": _athleteName,
      "data": data,
    });

    final history = prefs.getStringList("history") ?? [];
    history.insert(0, entry);

    await prefs.setStringList("history", history);
  }

  // ---------------- REAL ANALYSIS ----------------
  Future<void> _analyzeVideo() async {
    if (_videoFile == null) return;

    if (_athleteName.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Please enter athlete name")),
      );
      return;
    }

    setState(() {
      _isAnalyzing = true;
      _result = null;
    });

    try {
      final uri = Uri.parse("$_baseUrl/analyze_video");

      final request = http.MultipartRequest("POST", uri);
      request.files.add(
        await http.MultipartFile.fromPath("file", _videoFile!.path),
      );

      final streamed = await request.send();
      final response = await http.Response.fromStream(streamed);

      if (response.statusCode != 200) {
        throw Exception("Server ${response.statusCode}: ${response.body}");
      }

      final decoded = jsonDecode(response.body);

      setState(() {
        _isAnalyzing = false;
        _result = decoded is Map<String, dynamic>
            ? decoded
            : <String, dynamic>{"raw": decoded};
      });

      await _saveResult(_result!);

      if (!mounted) return;

      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => ResultScreen(resultData: _result!),
        ),
      );
    } catch (e) {
      setState(() {
        _isAnalyzing = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Error: $e")),
      );
    }
  }

  // ---------------- DEMO MODE ----------------
  Future<void> _runDemo() async {
    if (_athleteName.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Please enter athlete name")),
      );
      return;
    }

    final demo = {
      "overall_score": 92.0,
      "average_knee_angle": 164.2,
      "difference_from_ideal": 0.8,
      "ideal_knee_angle": 165,
      "performance_level": "advanced",
      "mistakes": ["No major mistakes detected."],
      "suggestions": [
        "Maintain this running form and consistency.",
        "Keep stride smooth and controlled."
      ],
      "ml_used": true,
      "source": "demo_mode",
      "frames_analyzed": 20,
      "keypoints_confidence": 0.85,
    };

    await _saveResult(demo);

    if (!mounted) return;

    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ResultScreen(resultData: demo),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final fileName = _videoFile == null
        ? "No video selected"
        : _videoFile!.path.split(Platform.pathSeparator).last;

    return Scaffold(
      appBar: AppBar(
        title: const Text("Runner Analyzer"),
        actions: [
          IconButton(
            icon: const Icon(Icons.compare_arrows),
            tooltip: "Compare Sessions",
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const CompareScreen()),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.history),
            tooltip: "History",
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const HistoryScreen()),
              );
            },
          ),
        ],
      ),
      body: Stack(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: ListView(
              children: [
                // Athlete Input
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          "Athlete",
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 12),
                        TextField(
                          controller: _nameController,
                          decoration: const InputDecoration(
                            labelText: "Athlete Name",
                            border: OutlineInputBorder(),
                          ),
                          onChanged: (val) {
                            _athleteName = val.trim();
                          },
                        ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 16),

                // Select Video
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          "Step 1: Select Video",
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 10),
                        Text(fileName),
                        const SizedBox(height: 12),
                        ElevatedButton.icon(
                          onPressed: _isAnalyzing ? null : _pickVideo,
                          icon: const Icon(Icons.video_file),
                          label: const Text("Choose Video"),
                        ),
                        const SizedBox(height: 12),
                        OutlinedButton.icon(
                          onPressed: _isAnalyzing ? null : _pingServer,
                          icon: const Icon(Icons.wifi_tethering),
                          label: const Text("Test Server Connection"),
                        ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 16),

                // Analyze Card
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        const Text(
                          "Step 2: Analyze",
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 12),
                        ElevatedButton.icon(
                          onPressed:
                              (_videoFile == null || _isAnalyzing) ? null : _analyzeVideo,
                          icon: const Icon(Icons.analytics),
                          label: const Text("Analyze Video"),
                        ),
                        const SizedBox(height: 12),
                        OutlinedButton.icon(
                          onPressed: _isAnalyzing ? null : _runDemo,
                          icon: const Icon(Icons.science),
                          label: const Text("Run Demo Analysis"),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Full Screen Loading Overlay
          if (_isAnalyzing)
            Container(
              color: Colors.black.withOpacity(0.7),
              child: const Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircularProgressIndicator(color: Colors.white),
                    SizedBox(height: 20),
                    Text(
                      "Analyzing your performance...",
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                      ),
                    ),
                    SizedBox(height: 8),
                    Text(
                      "AI is evaluating motion patterns",
                      style: TextStyle(
                        color: Colors.white70,
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}
