"""Export the audited hard4 weights without workstation-specific absolute paths."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import torch

SOURCE_SHA256 = "a8079d3f7243cfbc6efa6dbfaedd45a18e6669b35ab4d52a70fe8f36f70ed1ae"
PORTABLE_SCHEMA = "rescue79-portable-static-model-v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export(source: Path, output: Path) -> None:
    actual = sha256_file(source)
    if actual != SOURCE_SHA256:
        raise SystemExit(f"Source SHA-256 mismatch: {actual}")
    checkpoint = torch.load(source, map_location="cpu", weights_only=True)
    required = {"model_state", "model_config", "label_to_index", "training_config"}
    if not isinstance(checkpoint, dict) or not required.issubset(checkpoint):
        raise SystemExit("Source checkpoint schema is incomplete")
    portable = {
        "schema_version": PORTABLE_SCHEMA,
        "model_state": checkpoint["model_state"],
        "model_config": checkpoint["model_config"],
        "label_to_index": checkpoint["label_to_index"],
        "training_summary": {
            "source_scope": "generated_still_diagnostic_only_not_field_proof",
            "base_synthetic_windows": 15_840,
            "adaptation_original_generated_stills": 34,
            "adaptation_label_counts": {"DIGIT_7": 16, "DIGIT_9": 18},
            "derived_augmented_inputs": 1_088,
            "augmentations_per_still": 32,
            "epochs": 80,
            "trained_parameters": [
                "classifier.weight rows 7 and 9",
                "classifier.bias rows 7 and 9",
            ],
            "holdout_generated_stills": 50,
            "holdout_result": {"DIGIT_7": "25/25", "DIGIT_9": "25/25"},
            "real_cctv_performance_measured": False,
            "hard_negative_false_positive_rate_measured": False,
        },
        "provenance": {
            "source_checkpoint_sha256": actual,
            "source_schema_version": checkpoint.get("schema_version"),
            "base_checkpoint_sha256": "545e7a7e20fb114f47b094fec126bcd57ed466c7150a52b5ae68889450ec1163",
            "cases_manifest_sha256": "d97d07bf6f1a692f14043c2538ece086dd7754fab7f7360c0880f267e5f9c750",
            "extractor_artifact_sha256": "89963ca43f2af48e1247937b19d3757c38407380c999607d7c67c7e209a5d5f7",
            "trainer_source_sha256": "4ccbe2052fe5c6a19aea12c5658afcce1224ff5655ddba0a09f54206ca48ea13",
            "absolute_source_paths_removed": True,
            "export_kind": "inference_only_path_independent",
        },
        "safety": {
            "human_review_required": True,
            "automatic_112_119_dispatch_enabled": False,
            "real_emergency_decision_authority": False,
            "static_still_cannot_prove_temporal_7979": True,
            "score_is_uncalibrated": True,
        },
        "license": {
            "identifier": "MIT",
            "details_file": "MODEL_LICENSE.md",
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(portable, output)

    reloaded = torch.load(output, map_location="cpu", weights_only=True)
    if reloaded["schema_version"] != PORTABLE_SCHEMA:
        raise SystemExit("Portable readback failed")
    for key, value in checkpoint["model_state"].items():
        if not torch.equal(value.cpu(), reloaded["model_state"][key].cpu()):
            raise SystemExit(f"Tensor changed during export: {key}")
    print(f"portable_path={output}")
    print(f"portable_sha256={sha256_file(output)}")
    print(f"source_sha256={actual}")
    print(f"tensor_count={len(reloaded['model_state'])}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    export(args.source.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
