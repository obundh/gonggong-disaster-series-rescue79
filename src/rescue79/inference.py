"""Portable, local-only inference for generated-still Rescue79 model review."""

from __future__ import annotations

import hashlib
import io
import math
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import cv2
import torch
from PIL import Image, ImageDraw, ImageOps
from torchvision.models.detection import (
    KeypointRCNN_ResNet50_FPN_Weights,
    keypointrcnn_resnet50_fpn,
)

from .model import TemporalConvClassifier

PORTABLE_SCHEMA = "rescue79-portable-static-model-v1"
EXPECTED_SOURCE_SHA256 = (
    "a8079d3f7243cfbc6efa6dbfaedd45a18e6669b35ab4d52a70fe8f36f70ed1ae"
)
EXPECTED_PORTABLE_SHA256 = (
    "603cf711a4ccd59119c63a207bb78f3399ce8860c6eed5d6692481f13ff2db0a"
)
PERSON_SCORE_THRESHOLD = 0.35
KEYPOINT_CONFIDENCE_THRESHOLD = 0.50
MAX_INPUT_SIDE = 1600
MAX_PIXELS = 25_000_000
LABELS_ALLOWED = {f"DIGIT_{value}" for value in range(10)} | {
    "NEUTRAL",
    "UNKNOWN",
}

COCO17_NAMES = (
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)
BODY_AND_ARMS_INDICES = (5, 6, 7, 8, 9, 10, 11, 12)
HEAD_DEPENDENT_LABELS = {"DIGIT_0", "DIGIT_4", "DIGIT_5", "DIGIT_9"}
SKELETON_EDGES = (
    (0, 1), (0, 2), (1, 3), (2, 4),
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
    (5, 11), (6, 12), (11, 12),
    (11, 13), (13, 15), (12, 14), (14, 16),
)


class ReviewError(RuntimeError):
    """A safe, user-displayable review error."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _interpolate_feature(
    values: np.ndarray, visible: np.ndarray, target_time: np.ndarray
) -> np.ndarray:
    source_time = np.linspace(0.0, 1.0, values.shape[0], dtype=np.float64)
    valid = visible & np.isfinite(values)
    if not np.any(valid):
        return np.full(target_time.shape, np.nan, dtype=np.float32)
    if np.count_nonzero(valid) == 1:
        return np.full(target_time.shape, float(values[valid][0]), dtype=np.float32)
    return np.interp(target_time, source_time[valid], values[valid]).astype(np.float32)


def resample_and_normalize(arrays: dict[str, np.ndarray], frames: int = 48) -> np.ndarray:
    """Recreate the exact 48x17x6 feature contract used during training."""

    if frames < 4:
        raise ValueError("frames must be at least 4")
    xy = arrays["xy_normalized"].astype(np.float32)
    confidence = arrays["confidence"].astype(np.float32)
    visibility = arrays["visibility_mask"].astype(bool)
    target_time = np.linspace(0.0, 1.0, frames, dtype=np.float64)
    source_time = np.linspace(0.0, 1.0, xy.shape[0], dtype=np.float64)

    out_xy = np.empty((frames, xy.shape[1], 2), dtype=np.float32)
    out_conf = np.empty((frames, xy.shape[1]), dtype=np.float32)
    out_vis = np.empty((frames, xy.shape[1]), dtype=np.float32)
    for joint in range(xy.shape[1]):
        for axis in range(2):
            out_xy[:, joint, axis] = _interpolate_feature(
                xy[:, joint, axis], visibility[:, joint], target_time
            )
        out_conf[:, joint] = np.interp(
            target_time, source_time, confidence[:, joint]
        )
        out_vis[:, joint] = (
            np.interp(
                target_time, source_time, visibility[:, joint].astype(np.float32)
            )
            >= 0.5
        )

    left_shoulder, right_shoulder, left_hip, right_hip = 5, 6, 11, 12
    normalized = np.zeros_like(out_xy)
    for frame in range(frames):
        valid = out_vis[frame].astype(bool) & np.isfinite(out_xy[frame]).all(axis=1)
        shoulders_valid = valid[left_shoulder] and valid[right_shoulder]
        hips_valid = valid[left_hip] and valid[right_hip]
        if shoulders_valid:
            shoulder_center = (
                out_xy[frame, left_shoulder] + out_xy[frame, right_shoulder]
            ) / 2.0
            center = shoulder_center
            scale_candidates = [
                float(
                    np.linalg.norm(
                        out_xy[frame, left_shoulder]
                        - out_xy[frame, right_shoulder]
                    )
                )
            ]
            if hips_valid:
                hip_center = (
                    out_xy[frame, left_hip] + out_xy[frame, right_hip]
                ) / 2.0
                scale_candidates.extend(
                    [
                        float(
                            np.linalg.norm(
                                out_xy[frame, left_hip] - out_xy[frame, right_hip]
                            )
                        ),
                        0.5 * float(np.linalg.norm(shoulder_center - hip_center)),
                    ]
                )
            scale = max(scale_candidates)
        elif np.any(valid):
            points = out_xy[frame, valid]
            center = points.mean(axis=0)
            scale = float(np.linalg.norm(points.max(axis=0) - points.min(axis=0)))
        else:
            center = np.zeros(2, dtype=np.float32)
            scale = 1.0
        scale = max(scale, 1e-4)
        normalized[frame, valid] = (out_xy[frame, valid] - center) / scale

    normalized[~out_vis.astype(bool)] = 0.0
    delta = np.zeros_like(normalized)
    delta[1:] = normalized[1:] - normalized[:-1]
    delta[~out_vis.astype(bool)] = 0.0
    features = np.concatenate(
        [
            normalized,
            np.clip(out_conf, 0.0, 1.0)[..., None],
            out_vis[..., None],
            delta,
        ],
        axis=-1,
    )
    if features.shape != (frames, 17, 6) or not np.isfinite(features).all():
        raise ValueError(f"Invalid feature tensor: {features.shape}")
    return features.astype(np.float32)


def _diagnostic_confidence(raw_scores: np.ndarray) -> np.ndarray:
    values = raw_scores.astype(np.float64)
    result = np.empty_like(values)
    positive = values >= 0
    result[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    exponent = np.exp(values[~positive])
    result[~positive] = exponent / (1.0 + exponent)
    return result.astype(np.float32)


def prepare_static_features(
    keypoints_xy: np.ndarray,
    raw_keypoint_scores: np.ndarray,
    width: int,
    height: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert one COCO-17 pose into the static 48-frame model contract."""

    xy = np.asarray(keypoints_xy, dtype=np.float32)
    raw = np.asarray(raw_keypoint_scores, dtype=np.float32)
    if xy.shape != (17, 2) or raw.shape != (17,):
        raise ReviewError("자세 인식 결과의 관절 모양이 올바르지 않습니다.")
    confidence = _diagnostic_confidence(raw)
    finite = np.isfinite(xy).all(axis=1) & np.isfinite(raw)
    in_bounds = (
        (xy[:, 0] >= 0.0)
        & (xy[:, 0] <= float(width))
        & (xy[:, 1] >= 0.0)
        & (xy[:, 1] <= float(height))
    )
    visible = finite & in_bounds & (confidence >= KEYPOINT_CONFIDENCE_THRESHOLD)
    square_side = float(max(width, height))
    normalized = np.full((17, 2), np.nan, dtype=np.float32)
    normalized[visible] = np.clip(xy[visible] / square_side, 0.0, 1.0)
    arrays = {
        "xy_normalized": np.repeat(normalized[None, ...], 48, axis=0),
        "confidence": np.repeat(confidence[None, ...], 48, axis=0),
        "visibility_mask": np.repeat(visible.astype(np.uint8)[None, ...], 48, axis=0),
    }
    return resample_and_normalize(arrays), visible, confidence


def _quality(visibility: np.ndarray, expected_label: str, person_count: int) -> dict[str, Any]:
    missing = [
        COCO17_NAMES[index]
        for index in BODY_AND_ARMS_INDICES
        if not bool(visibility[index])
    ]
    head_required = expected_label in HEAD_DEPENDENT_LABELS
    head_visible = [COCO17_NAMES[index] for index in range(5) if visibility[index]]
    passed = not missing and (bool(head_visible) if head_required else True)
    passed = bool(passed and person_count == 1)
    return {
        "pass": passed,
        "visible_joint_count": int(visibility.sum()),
        "missing_required_joint_names": missing,
        "head_landmark_required": head_required,
        "visible_head_landmark_names": head_visible,
        "eligible_person_count": int(person_count),
        "single_person_gate_pass": person_count == 1,
        "explanation_ko": (
            "필요한 관절과 한 사람 조건을 확인했습니다."
            if passed
            else "사람 수 또는 필요한 관절 정보가 부족하여 판정을 보류합니다."
        ),
    }


def decode_image(payload: bytes) -> Image.Image:
    """Decode an image in memory, with conservative size checks."""

    try:
        with Image.open(io.BytesIO(payload)) as opened:
            width, height = opened.size
            if width <= 0 or height <= 0 or width * height > MAX_PIXELS:
                raise ReviewError("사진이 너무 큽니다. 2,500만 화소 이하를 사용해 주세요.")
            return ImageOps.exif_transpose(opened).convert("RGB").copy()
    except ReviewError:
        raise
    except Exception as exc:
        raise ReviewError("PNG, JPG 또는 WEBP 사진을 선택해 주세요.") from exc


def resize_image(image: Image.Image) -> Image.Image:
    longest = max(image.size)
    if longest <= MAX_INPUT_SIDE:
        return image.copy()
    scale = MAX_INPUT_SIDE / float(longest)
    size = (
        max(1, int(round(image.width * scale))),
        max(1, int(round(image.height * scale))),
    )
    # Preserve the exact resize contract used for the audited 50-image holdout.
    # Changing the interpolation algorithm changes the downstream COCO pose and
    # therefore makes the published holdout result inapplicable to this runtime.
    resized = cv2.resize(np.asarray(image), size, interpolation=cv2.INTER_AREA)
    return Image.fromarray(np.ascontiguousarray(resized), mode="RGB")


def _tensor_to_numpy(value: Any) -> np.ndarray:
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().numpy()
    return np.asarray(value)


def _box_pair_metrics(primary: np.ndarray, candidate: np.ndarray) -> dict[str, float] | None:
    first = np.asarray(primary, dtype=np.float64)
    second = np.asarray(candidate, dtype=np.float64)
    if first.shape != (4,) or second.shape != (4,) or not np.isfinite([first, second]).all():
        return None
    first_width, first_height = first[2] - first[0], first[3] - first[1]
    second_width, second_height = second[2] - second[0], second[3] - second[1]
    if min(first_width, first_height, second_width, second_height) <= 0:
        return None
    first_area = float(first_width * first_height)
    second_area = float(second_width * second_height)
    intersection_width = max(0.0, min(first[2], second[2]) - max(first[0], second[0]))
    intersection_height = max(0.0, min(first[3], second[3]) - max(first[1], second[1]))
    intersection = float(intersection_width * intersection_height)
    union = first_area + second_area - intersection
    smaller, larger = min(first_area, second_area), max(first_area, second_area)
    first_center = np.asarray([(first[0] + first[2]) / 2, (first[1] + first[3]) / 2])
    second_center = np.asarray([(second[0] + second[2]) / 2, (second[1] + second[3]) / 2])
    diagonal = float(np.hypot(first_width, first_height))
    return {
        "box_iou": intersection / union,
        "intersection_over_smaller_box": intersection / smaller,
        "smaller_to_larger_area_ratio": smaller / larger,
        "center_distance_primary_diagonal_ratio": float(
            np.linalg.norm(first_center - second_center) / diagonal
        ),
        "primary_box_diagonal_px": diagonal,
    }


def _same_person_duplicate(
    prediction: dict[str, Any], primary_index: int, candidate_index: int
) -> bool:
    """Suppress only a fully evidenced duplicate of the same COCO person."""

    boxes = _tensor_to_numpy(prediction.get("boxes", np.empty((0, 4))))
    keypoints = _tensor_to_numpy(prediction.get("keypoints", np.empty((0, 17, 3))))
    raw_scores = _tensor_to_numpy(
        prediction.get("keypoints_scores", np.empty((0, 17)))
    )
    count = len(boxes)
    if (
        not (0 <= primary_index < count and 0 <= candidate_index < count)
        or keypoints.ndim != 3
        or keypoints.shape[0] != count
        or keypoints.shape[1] < 13
        or raw_scores.ndim != 2
        or raw_scores.shape[0] != count
        or raw_scores.shape[1] < 13
    ):
        return False
    metrics = _box_pair_metrics(boxes[primary_index], boxes[candidate_index])
    if metrics is None:
        return False
    first_xy = np.asarray(keypoints[primary_index, :13, :2], dtype=np.float64)
    second_xy = np.asarray(keypoints[candidate_index, :13, :2], dtype=np.float64)
    first_scores = np.asarray(raw_scores[primary_index, :13], dtype=np.float64)
    second_scores = np.asarray(raw_scores[candidate_index, :13], dtype=np.float64)
    common = (
        np.isfinite(first_xy).all(axis=1)
        & np.isfinite(second_xy).all(axis=1)
        & np.isfinite(first_scores)
        & np.isfinite(second_scores)
        & (first_scores >= 0.0)
        & (second_scores >= 0.0)
    )
    if not np.any(common):
        return False
    distances = (
        np.linalg.norm(first_xy[common] - second_xy[common], axis=1)
        / metrics["primary_box_diagonal_px"]
    )
    checks = (
        metrics["box_iou"] >= 0.40,
        metrics["intersection_over_smaller_box"] >= 0.90,
        metrics["smaller_to_larger_area_ratio"] >= 0.35,
        metrics["center_distance_primary_diagonal_ratio"] <= 0.22,
        int(common.sum()) >= 10,
        float(np.median(distances)) <= 0.015,
        float(np.quantile(distances, 0.90)) <= 0.025,
        int(np.count_nonzero(distances <= 0.025)) >= 10,
    )
    return all(bool(value) for value in checks)


def select_person(
    prediction: dict[str, Any],
) -> tuple[int | None, int, list[float], list[int]]:
    """Fail closed unless one effective person remains after strict deduplication."""

    scores = _tensor_to_numpy(prediction.get("scores", np.empty(0))).astype(float)
    labels = _tensor_to_numpy(prediction.get("labels", np.empty(0))).astype(int)
    eligible = sorted(
        (
            index
            for index, (score, label) in enumerate(zip(scores, labels, strict=True))
            if label == 1 and score >= PERSON_SCORE_THRESHOLD
        ),
        key=lambda index: scores[index],
        reverse=True,
    )
    retained: list[int] = []
    suppressed: list[int] = []
    for index in eligible:
        if any(_same_person_duplicate(prediction, primary, index) for primary in retained):
            suppressed.append(index)
        else:
            retained.append(index)
    person_scores = [float(scores[index]) for index in eligible]
    if len(retained) != 1:
        return None, len(retained), person_scores, suppressed
    return retained[0], 1, person_scores, suppressed


def _portable_checkpoint(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ReviewError(f"모델 파일을 찾지 못했습니다: {path.name}")
    actual_sha256 = sha256_file(path)
    if actual_sha256 != EXPECTED_PORTABLE_SHA256:
        raise ReviewError(
            "모델 파일의 SHA-256이 공개 모델 카드와 다릅니다. "
            "공식 Release에서 다시 받아 주세요."
        )
    try:
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    except Exception as exc:
        raise ReviewError("모델 파일을 안전하게 읽지 못했습니다.") from exc
    if not isinstance(checkpoint, dict) or checkpoint.get("schema_version") != PORTABLE_SCHEMA:
        raise ReviewError("이 공개판에 맞는 Rescue79 모델이 아닙니다.")
    source = checkpoint.get("provenance", {}).get("source_checkpoint_sha256")
    if source != EXPECTED_SOURCE_SHA256:
        raise ReviewError("모델 출처 해시가 공개 모델 카드와 다릅니다.")
    config = checkpoint.get("model_config")
    labels = checkpoint.get("label_to_index")
    state = checkpoint.get("model_state")
    if not isinstance(config, dict) or not isinstance(labels, dict) or not isinstance(state, dict):
        raise ReviewError("모델의 필수 정보가 빠졌습니다.")
    if set(map(str, labels)) != LABELS_ALLOWED or sorted(map(int, labels.values())) != list(range(12)):
        raise ReviewError("모델 숫자표가 예상과 다릅니다.")
    return checkpoint


@dataclass
class Runtime:
    """Lazy pose/classifier runtime; it never writes uploaded images to disk."""

    checkpoint_path: Path
    device_name: str = "cpu"

    def __post_init__(self) -> None:
        self.device = torch.device(self.device_name)
        checkpoint = _portable_checkpoint(self.checkpoint_path)
        self.label_to_index = {
            str(label): int(index)
            for label, index in checkpoint["label_to_index"].items()
        }
        self.index_to_label = {index: label for label, index in self.label_to_index.items()}
        self.classifier = TemporalConvClassifier(**checkpoint["model_config"])
        self.classifier.load_state_dict(checkpoint["model_state"], strict=True)
        self.classifier.to(self.device).eval()
        self.model_sha256 = sha256_file(self.checkpoint_path)
        self.source_checkpoint_sha256 = checkpoint["provenance"]["source_checkpoint_sha256"]
        self._pose_model: torch.nn.Module | None = None
        self._lock = threading.Lock()

    def warmup_pose_model(self) -> None:
        """Download/load official COCO pose weights on first use."""

        if self._pose_model is None:
            weights = KeypointRCNN_ResNet50_FPN_Weights.COCO_V1
            self._pose_model = keypointrcnn_resnet50_fpn(weights=weights)
            self._pose_model.to(self.device).eval()

    def metadata(self) -> dict[str, Any]:
        return {
            "ready": True,
            "model_name": "Rescue79 hard4 portable v1",
            "model_sha256": self.model_sha256,
            "source_checkpoint_sha256": self.source_checkpoint_sha256,
            "pose_model_loaded": self._pose_model is not None,
            "device": str(self.device),
            "local_only": True,
            "human_review_required": True,
            "automatic_dispatch_enabled": False,
            "real_cctv_performance_measured": False,
        }

    def review(self, payload: bytes, expected_digit: str) -> dict[str, Any]:
        if expected_digit not in {"7", "9"}:
            raise ReviewError("먼저 사진의 정답 7 또는 9를 선택해 주세요.")
        expected_label = f"DIGIT_{expected_digit}"
        image = decode_image(payload)
        probe = resize_image(image)
        with self._lock:
            self.warmup_pose_model()
            assert self._pose_model is not None
            weights = KeypointRCNN_ResNet50_FPN_Weights.COCO_V1
            pose_tensor = weights.transforms()(probe).to(self.device)
            with torch.inference_mode():
                prediction = self._pose_model([pose_tensor])[0]
            selected, person_count, person_scores, suppressed_duplicates = select_person(
                prediction
            )

            if selected is None:
                return self._abstention(
                    image=image,
                    probe=probe,
                    expected_digit=expected_digit,
                    reason=(
                        "사람을 찾지 못했습니다."
                        if person_count == 0
                        else "한 장에 여러 사람이 보여 판정을 보류했습니다."
                    ),
                    person_count=person_count,
                    person_scores=person_scores,
                    suppressed_duplicates=suppressed_duplicates,
                )

            keypoints = _tensor_to_numpy(prediction["keypoints"])[selected, :17, :2]
            raw_scores = _tensor_to_numpy(prediction["keypoints_scores"])[selected, :17]
            features, visibility, confidence = prepare_static_features(
                keypoints, raw_scores, probe.width, probe.height
            )
            quality = _quality(visibility, expected_label, person_count)
            with torch.inference_mode():
                logits = self.classifier(
                    torch.from_numpy(features).unsqueeze(0).to(self.device)
                )
                scores = torch.softmax(logits, dim=1)[0].cpu().numpy()

        top_indices = np.argsort(scores)[::-1][:3]
        top3 = [
            {
                "label": self.index_to_label[int(index)],
                "digit": _display_digit(self.index_to_label[int(index)]),
                "score_uncalibrated": float(scores[index]),
            }
            for index in top_indices
        ]
        predicted_label = top3[0]["label"]
        predicted_digit = top3[0]["digit"]
        if not quality["pass"]:
            verdict = "ABSTAIN"
            reason = quality["explanation_ko"]
        elif predicted_label == expected_label:
            verdict = "CORRECT"
            reason = "모델 결과가 내가 고른 정답과 같습니다. 관절선도 꼭 확인하세요."
        else:
            verdict = "INCORRECT"
            reason = "모델 결과가 내가 고른 정답과 다릅니다. 시험 기록으로 남겨 주세요."
        overlay = draw_overlay(
            probe,
            keypoints=keypoints,
            visibility=visibility,
            prediction=predicted_digit,
            verdict=verdict,
        )
        return {
            "status": "COMPLETED",
            "verdict": verdict,
            "reason_ko": reason,
            "expected_digit": expected_digit,
            "predicted_digit": predicted_digit,
            "predicted_label": predicted_label,
            "score_uncalibrated": float(top3[0]["score_uncalibrated"]),
            "score_warning_ko": (
                "이 점수는 정답 확률이나 구조 요청 확률이 아닌 비보정 순위 점수입니다."
            ),
            "top3": top3,
            "quality": quality,
            "pose": {
                "person_scores": person_scores,
                "suppressed_same_person_duplicate_indices": suppressed_duplicates,
                "keypoint_confidences": [float(value) for value in confidence],
            },
            "overlay_png_base64": image_to_base64_png(overlay),
            "input_sha256": sha256_bytes(payload),
            "uploaded_image_retained": False,
            "human_review_required": True,
            "automatic_dispatch_enabled": False,
        }

    def _abstention(
        self,
        *,
        image: Image.Image,
        probe: Image.Image,
        expected_digit: str,
        reason: str,
        person_count: int,
        person_scores: list[float],
        suppressed_duplicates: list[int],
    ) -> dict[str, Any]:
        overlay = draw_overlay(
            probe,
            keypoints=None,
            visibility=None,
            prediction="-",
            verdict="ABSTAIN",
        )
        return {
            "status": "COMPLETED",
            "verdict": "ABSTAIN",
            "reason_ko": reason,
            "expected_digit": expected_digit,
            "predicted_digit": None,
            "predicted_label": None,
            "score_uncalibrated": None,
            "score_warning_ko": "증거가 부족하면 숫자를 억지로 선택하지 않습니다.",
            "top3": [],
            "quality": {
                "pass": False,
                "eligible_person_count": person_count,
                "single_person_gate_pass": person_count == 1,
                "visible_joint_count": 0,
                "missing_required_joint_names": [],
                "explanation_ko": reason,
            },
            "pose": {
                "person_scores": person_scores,
                "suppressed_same_person_duplicate_indices": suppressed_duplicates,
                "keypoint_confidences": [],
            },
            "overlay_png_base64": image_to_base64_png(overlay),
            "input_sha256": None,
            "uploaded_image_retained": False,
            "human_review_required": True,
            "automatic_dispatch_enabled": False,
        }


def _display_digit(label: str) -> str:
    if label.startswith("DIGIT_"):
        return label.removeprefix("DIGIT_")
    if label == "NEUTRAL":
        return "중립"
    return "알 수 없음"


def draw_overlay(
    image: Image.Image,
    *,
    keypoints: np.ndarray | None,
    visibility: np.ndarray | None,
    prediction: str,
    verdict: str,
) -> Image.Image:
    canvas = image.copy().convert("RGB")
    draw = ImageDraw.Draw(canvas)
    scale = max(2, int(round(max(canvas.size) / 500)))
    if keypoints is not None and visibility is not None:
        for left, right in SKELETON_EDGES:
            if visibility[left] and visibility[right]:
                draw.line(
                    [tuple(keypoints[left]), tuple(keypoints[right])],
                    fill=(255, 222, 54),
                    width=3 * scale,
                )
        radius = 3 * scale
        for index, point in enumerate(keypoints):
            if visibility[index] and all(math.isfinite(float(value)) for value in point):
                x, y = map(float, point)
                draw.ellipse(
                    (x - radius, y - radius, x + radius, y + radius),
                    fill=(220, 44, 44),
                    outline=(255, 255, 255),
                    width=max(1, scale),
                )
    panel_height = max(42, 28 * scale)
    color = {
        "CORRECT": (28, 130, 78),
        "INCORRECT": (190, 55, 45),
        "ABSTAIN": (165, 112, 24),
    }.get(verdict, (60, 70, 80))
    draw.rectangle((0, 0, canvas.width, panel_height), fill=(18, 21, 26))
    draw.text(
        (12 * scale, 7 * scale),
        f"Prediction: {prediction}   Result: {verdict}",
        fill=color,
        stroke_width=max(1, scale // 2),
        stroke_fill=(255, 255, 255),
    )
    return canvas


def image_to_base64_png(image: Image.Image) -> str:
    import base64

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("ascii")
