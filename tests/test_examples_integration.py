from __future__ import annotations

import json
from pathlib import Path

import pytest

from rescue79.inference import Runtime

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.integration
def test_public_generated_examples_match_audited_results() -> None:
    runtime = Runtime(ROOT / "models" / "rescue79-hard4-portable-v1.pt")
    expected = (
        ("d7_generated_example.png", "7"),
        ("d9_generated_example.png", "9"),
    )
    results = []
    for filename, digit in expected:
        output = runtime.review((ROOT / "examples" / filename).read_bytes(), digit)
        results.append(
            {
                "filename": filename,
                "expected_digit": digit,
                "verdict": output["verdict"],
                "predicted_digit": output["predicted_digit"],
                "score_uncalibrated": output["score_uncalibrated"],
                "eligible_person_count": output["quality"]["eligible_person_count"],
                "visible_joint_count": output["quality"]["visible_joint_count"],
                "suppressed_same_person_duplicate_indices": output["pose"][
                    "suppressed_same_person_duplicate_indices"
                ],
            }
        )
        assert output["verdict"] == "CORRECT"
        assert output["predicted_digit"] == digit
        assert output["quality"]["pass"] is True
    print(json.dumps(results, ensure_ascii=False, indent=2))
