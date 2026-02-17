class SessionModel {
  final String sessionId;
  final DateTime date;
  final Map<String, dynamic> metrics;

  SessionModel({
    required this.sessionId,
    required this.date,
    required this.metrics,
  });

  factory SessionModel.fromJson(Map<String, dynamic> json) {
    return SessionModel(
      sessionId: json['session_id'] ?? '',
      date: DateTime.parse(json['date']),
      metrics: Map<String, dynamic>.from(json['metrics'] ?? {}),
    );
  }
}
