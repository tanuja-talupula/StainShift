"""
Verification tests for Next.js website assets, schemas, and static data.
"""

import json
from pathlib import Path
import pytest


def test_public_benchmark_json_bundled_in_website():
    """Confirms public results JSON is in website/public/data/."""
    website_json = Path("website/public/data/stainshift_results.json")
    assert website_json.is_file(), f"File missing: {website_json}"

    with open(website_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["benchmark_metadata"]["mlflow_run_id"] == "c76c59f4bd7c4fe39f2ed2135856845a"
    assert data["dataset_metadata"]["held_out_test_images"] == 1077
    assert len(data["conditions_evaluated"]) == 8
    assert len(data["comparison_table"]) == 8


def test_demo_manifest_and_all_72_images_exist():
    """Verifies that all 72 demo images referenced in demo_manifest.json exist in website/public/."""
    manifest_p = Path("website/public/demo/demo_manifest.json")
    assert manifest_p.is_file(), f"Demo manifest missing: {manifest_p}"

    with open(manifest_p, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    examples = manifest["examples"]
    assert len(examples) == 9

    images_found = 0
    for ex in examples:
        for cond, cdata in ex["conditions"].items():
            img_rel = cdata["image_url"].lstrip("/")
            img_file = Path("website/public") / img_rel
            assert img_file.is_file(), f"Referenced demo image does not exist: {img_file}"
            assert img_file.stat().st_size > 1000, f"Image {img_file} is corrupted/too small"
            images_found += 1

    assert images_found == 72, f"Expected 72 images, found {images_found}"


def test_no_private_paths_in_demo_manifest():
    """Confirms no filesystem paths leak into demo manifest."""
    manifest_p = Path("website/public/demo/demo_manifest.json")
    with open(manifest_p, "r", encoding="utf-8") as f:
        text = f.read()

    for forbidden in ["/Users/", "/home/", "\\Users\\", "password", "token", "secret"]:
        assert forbidden.lower() not in text.lower(), f"Forbidden string '{forbidden}' leaked in manifest"
