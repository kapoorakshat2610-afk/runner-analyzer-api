import math
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import joblib


# ============================================================
# MODEL PATHS
# ============================================================

POSE_MODEL_PATH = (
    Path(__file__).resolve().parent.parent
    / "models"
    / "pose"
    / "pose_landmarker_full.task"
)

RUNNER_MODEL_PATH = (
    Path(__file__).resolve().parent.parent
    / "models"
    / "runner_model.pkl"
)


# ============================================================
# MODEL LOADER
# ============================================================

_runner_model = None


def load_runner_model():
    """
    Load the trained Random Forest model once.

    The model expects one feature:
        avg_knee_angle
    """

    global _runner_model

    if _runner_model is not None:
        return _runner_model

    if not RUNNER_MODEL_PATH.exists():
        return None

    try:
        _runner_model = joblib.load(
            RUNNER_MODEL_PATH
        )
        return _runner_model

    except Exception:
        _runner_model = None
        return None


# ============================================================
# ANGLE CALCULATION
# ============================================================

def angle_3pts(
    a: np.ndarray,
    b: np.ndarray,
    c: np.ndarray,
) -> float:
    """
    Calculate angle ABC in degrees.
    """

    ba = a - b
    bc = c - b

    denom = (
        np.linalg.norm(ba)
        * np.linalg.norm(bc)
    )

    if denom == 0:
        return float("nan")

    cos_angle = (
        np.dot(ba, bc)
        / denom
    )

    cos_angle = float(
        np.clip(
            cos_angle,
            -1.0,
            1.0,
        )
    )

    return math.degrees(
        math.acos(cos_angle)
    )


# ============================================================
# VIDEO ANALYSIS
# ============================================================

def analyze_video_knee_angle(
    video_path: str,
) -> dict:
    """
    Analyze a running video using
    MediaPipe Tasks Pose Landmarker.

    The ML model uses the 2D average knee angle.

    Returns:
        {
            "avg_knee_angle": float,
            "frames_analyzed": int,
            "confidence": float
        }
    """

    if not POSE_MODEL_PATH.exists():
        raise RuntimeError(
            f"Pose model not found: {POSE_MODEL_PATH}"
        )

    try:
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
    except Exception as exc:
        raise RuntimeError(
            f"MediaPipe Tasks import failed: {exc}"
        )

    try:
        from mediapipe import Image
        from mediapipe import ImageFormat
    except Exception as exc:
        raise RuntimeError(
            f"MediaPipe Image API import failed: {exc}"
        )

    base_options = python.BaseOptions(
        model_asset_path=str(
            POSE_MODEL_PATH
        )
    )

    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    try:
        landmarker = (
            vision.PoseLandmarker
            .create_from_options(options)
        )

    except Exception as exc:
        raise RuntimeError(
            f"Failed to create Pose Landmarker: {exc}"
        )

    cap = cv2.VideoCapture(
        video_path
    )

    if not cap.isOpened():
        landmarker.close()

        raise RuntimeError(
            "Cannot open uploaded video"
        )

    # Sample every 5th frame.
    frame_step = 5

    angles = []
    confidences = []

    frames_used = 0
    frame_idx = 0

    try:

        while True:

            ok, frame = cap.read()

            if not ok:
                break

            frame_idx += 1

            if frame_idx % frame_step != 0:
                continue

            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB,
            )

            mp_image = Image(
                image_format=ImageFormat.SRGB,
                data=rgb,
            )

            try:

                result = (
                    landmarker.detect(
                        mp_image
                    )
                )

            except Exception:
                continue

            if not result.pose_landmarks:
                continue

            landmarks = (
                result.pose_landmarks[0]
            )

            # ------------------------------------------------
            # 2D POINT
            # ------------------------------------------------

            def point_2d(
                index: int,
            ) -> np.ndarray:

                landmark = landmarks[index]

                return np.array(
                    [
                        landmark.x,
                        landmark.y,
                    ],
                    dtype=np.float32,
                )

            # ------------------------------------------------
            # LANDMARKS
            # ------------------------------------------------
            #
            # Left:
            # 23 = hip
            # 25 = knee
            # 27 = ankle
            #
            # Right:
            # 24 = hip
            # 26 = knee
            # 28 = ankle
            #

            left_angle = angle_3pts(
                point_2d(23),
                point_2d(25),
                point_2d(27),
            )

            right_angle = angle_3pts(
                point_2d(24),
                point_2d(26),
                point_2d(28),
            )

            valid_angles = []

            if not math.isnan(
                left_angle
            ):
                valid_angles.append(
                    left_angle
                )

            if not math.isnan(
                right_angle
            ):
                valid_angles.append(
                    right_angle
                )

            if not valid_angles:
                continue

            frame_angle = float(
                np.mean(
                    valid_angles
                )
            )

            # Ignore invalid angles.
            if not (
                20.0
                <= frame_angle
                <= 200.0
            ):
                continue

            angles.append(
                frame_angle
            )

            # ------------------------------------------------
            # CONFIDENCE
            # ------------------------------------------------

            visibility_values = []

            for index in (
                23,
                25,
                27,
                24,
                26,
                28,
            ):

                visibility = getattr(
                    landmarks[index],
                    "visibility",
                    0.0,
                )

                visibility_values.append(
                    float(visibility)
                )

            frame_confidence = float(
                np.mean(
                    visibility_values
                )
            )

            confidences.append(
                frame_confidence
            )

            frames_used += 1

    finally:

        cap.release()
        landmarker.close()

    if (
        frames_used == 0
        or not angles
    ):

        raise RuntimeError(
            "No valid pose frames detected. "
            "Try a clearer side-view running video "
            "with the full body visible."
        )

    average_angle = float(
        np.mean(angles)
    )

    if not (
        20.0
        <= average_angle
        <= 200.0
    ):

        raise RuntimeError(
            f"Invalid knee angle computed: "
            f"{average_angle}"
        )

    average_confidence = (
        float(
            np.mean(
                confidences
            )
        )
        if confidences
        else 0.0
    )

    return {
        "avg_knee_angle": average_angle,
        "frames_analyzed": frames_used,
        "confidence": average_confidence,
    }


# ============================================================
# ML PREDICTION
# ============================================================

def predict_performance(
    average_knee_angle: float,
) -> dict:
    """
    Predict performance using runner_model.pkl.

    The trained model expects one named feature:
        avg_knee_angle
    """

    model = load_runner_model()

    if model is None:
        return {
            "ml_used": False,
            "ml_prediction": None,
            "ml_confidence": 0.0,
            "ml_probabilities": {},
        }

    try:

        X = pd.DataFrame(
            {
                "avg_knee_angle": [
                    float(
                        average_knee_angle
                    )
                ]
            }
        )

        prediction = model.predict(
            X
        )[0]

        probabilities = (
            model.predict_proba(X)[0]
        )

        class_probabilities = {
            str(label): round(
                float(probability),
                4,
            )
            for label, probability
            in zip(
                model.classes_,
                probabilities,
            )
        }

        prediction_confidence = (
            float(
                np.max(
                    probabilities
                )
            )
        )

        return {
            "ml_used": True,
            "ml_prediction": str(
                prediction
            ).lower(),
            "ml_confidence": round(
                prediction_confidence,
                4,
            ),
            "ml_probabilities": (
                class_probabilities
            ),
        }

    except Exception:
        return {
            "ml_used": False,
            "ml_prediction": None,
            "ml_confidence": 0.0,
            "ml_probabilities": {},
        }


# ============================================================
# REPORT
# ============================================================

def build_report(
    average_knee_angle: float,
    frames_analyzed: int,
    confidence: float | None = None,
) -> dict:
    """
    Build the complete running report.

    Overall score:
        Existing rule-based score.

    Performance level:
        Trained Random Forest model when available.

    This keeps the existing score calculation while
    replacing the old rule-based performance level
    with the trained ML prediction.
    """

    ideal_knee_angle = 165.0

    average_angle = float(
        average_knee_angle
    )

    difference = abs(
        ideal_knee_angle
        - average_angle
    )

    confidence_value = (
        float(confidence)
        if confidence is not None
        else 0.0
    )

    # --------------------------------------------------------
    # EXISTING SCORE
    # --------------------------------------------------------

    difference_for_score = min(
        difference,
        30.0,
    )

    score = (
        100.0
        - difference_for_score * 2.0
    )

    if confidence_value < 0.35:

        score = max(
            score,
            55.0,
        )

    score = max(
        0.0,
        min(
            100.0,
            score,
        ),
    )

    # --------------------------------------------------------
    # ML PREDICTION
    # --------------------------------------------------------

    ml_result = predict_performance(
        average_angle
    )

    ml_performance = (
        ml_result["ml_prediction"]
    )

    # Use ML prediction when available.
    # Otherwise preserve previous rule-based behavior.

    if ml_performance:

        performance_level = (
            ml_performance
        )

    else:

        if score >= 85:

            performance_level = (
                "advanced"
            )

        elif score >= 60:

            performance_level = (
                "intermediate"
            )

        else:

            performance_level = (
                "beginner"
            )

    # --------------------------------------------------------
    # MISTAKES + SUGGESTIONS
    # --------------------------------------------------------

    mistakes = []
    suggestions = []

    if confidence_value < 0.35:

        mistakes.append(
            "Low pose detection confidence in video."
        )

        suggestions.extend(
            [
                "Record in good lighting with full body visible.",
                "Use a side-view camera angle.",
                "Avoid camera shake.",
                "Try another recording for more accurate analysis.",
            ]
        )

    else:

        if difference <= 2:

            mistakes.append(
                "No major knee-angle deviation detected."
            )

            suggestions.extend(
                [
                    "Maintain this running form.",
                    "Keep stride smooth and controlled.",
                    "Maintain consistency.",
                ]
            )

        elif difference <= 6:

            mistakes.append(
                "Minor knee alignment deviation from the target angle."
            )

            suggestions.extend(
                [
                    "Aim closer to the target knee angle.",
                    "Focus on steady stride mechanics.",
                    "Focus on controlled knee drive.",
                ]
            )

        else:

            mistakes.append(
                "Knee angle deviation is high compared to the target angle."
            )

            suggestions.extend(
                [
                    "Practice knee-drive drills.",
                    "Focus on controlled landing technique.",
                    "Reduce overstriding.",
                    "Keep cadence steady.",
                    "Record from a side view with good lighting.",
                ]
            )

    # --------------------------------------------------------
    # FINAL REPORT
    # --------------------------------------------------------

    return {

        "overall_score": round(
            score,
            1,
        ),

        "average_knee_angle": round(
            average_angle,
            1,
        ),

        "difference_from_ideal": round(
            difference,
            1,
        ),

        "ideal_knee_angle":
            ideal_knee_angle,

        "performance_level":
            performance_level,

        "mistakes":
            mistakes,

        "suggestions":
            suggestions,

        "ml_used":
            ml_result["ml_used"],

        "ml_prediction":
            ml_result["ml_prediction"],

        "ml_confidence":
            ml_result["ml_confidence"],

        "ml_probabilities":
            ml_result["ml_probabilities"],

        "analysis_method": (
            "MediaPipe Pose Landmarker "
            "+ 2D knee angle "
            "+ Random Forest ML"
        ),

        "score_method":
            "Rule-based knee-angle scoring",

        "source":
            "uploaded_video",

        "frames_analyzed":
            frames_analyzed,

        "keypoints_confidence":
            round(
                confidence_value,
                3,
            ),
    }


# ============================================================
# COMPLETE PIPELINE
# ============================================================

def analyze_running_video(
    video_path: str,
) -> dict:
    """
    Complete running-video analysis pipeline.
    """

    analysis = (
        analyze_video_knee_angle(
            video_path
        )
    )

    return build_report(
        average_knee_angle=analysis[
            "avg_knee_angle"
        ],
        frames_analyzed=analysis[
            "frames_analyzed"
        ],
        confidence=analysis.get(
            "confidence"
        ),
    )