"""
Empirical Verification Test Suite for StainShift Minimal UI Cleanup.
Tests local build output (website/out) and live deployment (https://stainshift-ai.vercel.app).
"""

import os
import json
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import pytest

REPO_ROOT = Path("/Users/maheshreddy/teamwork_projects/stainshift")
WEBSITE_DIR = REPO_ROOT / "website"
OUT_DIR = WEBSITE_DIR / "out"
LIVE_URL = "https://stainshift-ai.vercel.app"


# =========================================================================
# 1. BUILD ARTIFACTS VERIFICATION (LOCAL out/ DIRECTORY)
# =========================================================================

def test_local_build_homepage_hero_buttons_absent():
    """Assert hero section in out/index.html does NOT contain 'Try AI Workspace' or 'View Benchmark'."""
    index_html = OUT_DIR / "index.html"
    assert index_html.is_file(), f"Build artifact missing: {index_html}"

    content = index_html.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")

    # Find the hero section (first section with min-h-[92vh] or containing the main h1)
    h1 = soup.find("h1")
    assert h1 is not None, "Hero h1 not found"
    hero_section = h1.find_parent("section")
    assert hero_section is not None, "Hero section not found"

    hero_text = hero_section.get_text()

    # Hero headline & stats must be present
    assert "Your CNN gets" in hero_text
    assert "stain shifts?" in hero_text
    assert "N = 1,077 held-out patches" in hero_text

    # Buttons in hero must NOT be present
    assert "Try AI Workspace" not in hero_text, "Found 'Try AI Workspace' inside hero section!"
    assert "View Benchmark" not in hero_text, "Found 'View Benchmark' inside hero section!"

    # Also assert no <a> tags inside hero pointing to /workspace/ or #benchmark
    for a in hero_section.find_all("a"):
        href = a.get("href", "")
        assert "workspace" not in href, f"Found link to workspace in hero: {a}"
        assert href != "#benchmark", f"Found link to #benchmark in hero: {a}"


def test_local_build_navbar_cta_present():
    """Assert out/index.html header/nav still contains 'Try AI Workspace' CTA button."""
    index_html = OUT_DIR / "index.html"
    content = index_html.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")

    header = soup.find("header")
    assert header is not None, "Navbar header not found"

    header_links = header.find_all("a")
    workspace_links = [a for a in header_links if "/workspace" in a.get("href", "")]
    assert len(workspace_links) >= 1, "Expected at least 1 /workspace/ link in header"

    link_texts = [a.get_text() for a in workspace_links]
    assert any("Try AI Workspace" in t for t in link_texts), f"Header workspace link text missing 'Try AI Workspace': {link_texts}"


def test_local_build_workspace_benchmark_section_absent():
    """Assert out/workspace/index.html does NOT contain 'Benchmark & Examples' section or cards."""
    ws_html = OUT_DIR / "workspace" / "index.html"
    assert ws_html.is_file(), f"Workspace build artifact missing: {ws_html}"

    content = ws_html.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")

    ws_text = soup.get_text()

    assert "Benchmark & Examples" not in ws_text, "Found 'Benchmark & Examples' in workspace page!"
    assert "CRC-VAL-HE-7K Single-Cohort Study" not in ws_text, "Found cohort study label in workspace page!"
    assert "Inspect accuracy recovery from 33.9% to 97.7%" not in ws_text
    assert "Explore 72 pre-evaluated tissue patches" not in ws_text

    # Workspace functional elements must remain
    assert "Back to Overview" in ws_text
    assert "Run Prediction" in ws_text


def test_local_build_dashboard_and_demo_exist():
    """Assert out/dashboard/index.html and out/demo/index.html exist and contain expected titles."""
    dash_html = OUT_DIR / "dashboard" / "index.html"
    assert dash_html.is_file(), f"Dashboard HTML missing: {dash_html}"
    dash_text = dash_html.read_text(encoding="utf-8")
    assert "Verified Benchmark Results Dashboard" in dash_text
    assert "Public Results JSON" in dash_text

    demo_html = OUT_DIR / "demo" / "index.html"
    assert demo_html.is_file(), f"Demo HTML missing: {demo_html}"
    demo_text = demo_html.read_text(encoding="utf-8")
    assert "Demo Explorer" in demo_text
    assert "Explore 72 pre-evaluated tissue patches" in demo_text


def test_public_benchmark_json_file_validity():
    """Assert public results JSON exists in out/data/ and has complete benchmark schema."""
    json_path = OUT_DIR / "data" / "stainshift_results.json"
    assert json_path.is_file(), f"Public JSON missing in out: {json_path}"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "CRC-VAL-HE-7K" in str(data["dataset_metadata"])
    assert len(data["conditions_evaluated"]) == 8
    assert len(data["comparison_table"]) == 8
    assert data["dataset_metadata"]["held_out_test_images"] == 1077


def test_demo_manifest_and_72_patches_in_build():
    """Assert out/demo/demo_manifest.json exists and all 72 image paths exist in out/."""
    manifest_p = OUT_DIR / "demo" / "demo_manifest.json"
    assert manifest_p.is_file(), f"Demo manifest missing in out: {manifest_p}"
    with open(manifest_p, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    examples = manifest["examples"]
    assert len(examples) == 9

    images_count = 0
    for ex in examples:
        for cond, cdata in ex["conditions"].items():
            img_rel = cdata["image_url"].lstrip("/")
            img_file = OUT_DIR / img_rel
            assert img_file.is_file(), f"Demo image missing in out/: {img_file}"
            assert img_file.stat().st_size > 500, f"Demo image corrupted: {img_file}"
            images_count += 1

    assert images_count == 72, f"Expected 72 patches in out/, found {images_count}"
