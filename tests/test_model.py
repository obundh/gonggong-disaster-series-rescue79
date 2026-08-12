from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import torch

from rescue79.inference import (
    PORTABLE_SCHEMA,
    ReviewError,
    Runtime,
    _portable_checkpoint,
    prepare_static_features,
    select_person,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models" / "rescue79-hard4-portable-v1.pt"


def test_checkpoint_is_portable_and_audited() -> None:
    checkpoint = torch.load(MODEL, map_location="cpu", weights_only=True)
    assert checkpoint["schema_version"] == PORTABLE_SCHEMA
    assert checkpoint["provenance"]["absolute_source_paths_removed"] is True
    assert checkpoint["safety"]["human_review_required"] is True
    assert checkpoint["safety"]["automatic_112_119_dispatch_enabled"] is False
    assert "E:\\" not in repr(checkpoint)
    assert len(checkpoint["model_state"]) == 46


def test_runtime_loads_without_training_sources() -> None:
    loaded = Runtime(MODEL)
    metadata = loaded.metadata()
    assert metadata["ready"] is True
    assert metadata["pose_model_loaded"] is False
    assert metadata["automatic_dispatch_enabled"] is False
    assert metadata["real_cctv_performance_measured"] is False
    assert len(metadata["model_sha256"]) == 64
    assert metadata["model_sha256"] == sha256_file(MODEL)


def test_modified_portable_checkpoint_is_rejected(tmp_path: Path) -> None:
    changed = bytearray(MODEL.read_bytes())
    changed[-1] ^= 1
    path = tmp_path / MODEL.name
    path.write_bytes(changed)
    with pytest.raises(ReviewError, match="SHA-256"):
        _portable_checkpoint(path)


def test_static_feature_contract() -> None:
    keypoints = np.stack(
        [np.linspace(100, 300, 17), np.linspace(80, 460, 17)], axis=1
    ).astype(np.float32)
    raw_scores = np.full((17,), 5.0, dtype=np.float32)
    features, visibility, confidence = prepare_static_features(
        keypoints, raw_scores, 640, 480
    )
    assert features.shape == (48, 17, 6)
    assert np.isfinite(features).all()
    assert visibility.all()
    assert (confidence > 0.99).all()


def test_resize_uses_audited_opencv_area_contract() -> None:
    from PIL import Image
    import cv2

    from rescue79.inference import MAX_INPUT_SIDE, resize_image

    source = np.arange(1900 * 1000 * 3, dtype=np.uint8).reshape(1000, 1900, 3)
    resized = np.asarray(resize_image(Image.fromarray(source)))
    expected_size = (MAX_INPUT_SIDE, int(round(1000 * MAX_INPUT_SIDE / 1900)))
    expected = cv2.resize(source, expected_size, interpolation=cv2.INTER_AREA)
    assert np.array_equal(resized, expected)


def test_classifier_output_contract() -> None:
    loaded = Runtime(MODEL)
    inputs = torch.zeros((1, 48, 17, 6), dtype=torch.float32)
    with torch.inference_mode():
        output = loaded.classifier(inputs)
    assert output.shape == (1, 12)
    assert torch.isfinite(output).all()


def test_strict_same_person_duplicate_is_suppressed() -> None:
    # Two detector rows describe the same body with nearly identical core joints.
    boxes = torch.tensor([[10, 10, 210, 410], [12, 12, 208, 408]], dtype=torch.float32)
    keypoints = torch.zeros((2, 17, 3), dtype=torch.float32)
    for index in range(17):
        keypoints[0, index, :2] = torch.tensor([30 + index * 7, 40 + index * 13])
        keypoints[1, index, :2] = keypoints[0, index, :2] + 0.5
    prediction = {
        "scores": torch.tensor([0.99, 0.80]),
        "labels": torch.tensor([1, 1]),
        "boxes": boxes,
        "keypoints": keypoints,
        "keypoints_scores": torch.ones((2, 17)),
    }
    selected, count, scores, suppressed = select_person(prediction)
    assert selected == 0
    assert count == 1
    assert scores == [pytest.approx(0.99), pytest.approx(0.80)]
    assert suppressed == [1]


def test_distinct_people_fail_closed() -> None:
    prediction = {
        "scores": torch.tensor([0.99, 0.88]),
        "labels": torch.tensor([1, 1]),
        "boxes": torch.tensor([[10, 10, 210, 410], [300, 10, 500, 410]], dtype=torch.float32),
        "keypoints": torch.zeros((2, 17, 3)),
        "keypoints_scores": torch.ones((2, 17)),
    }
    selected, count, _scores, suppressed = select_person(prediction)
    assert selected is None
    assert count == 2
    assert suppressed == []
