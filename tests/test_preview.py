from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / "preview" / "K2-preview.html"


def test_preview_is_reproducible_single_file_and_offline():
    before = PREVIEW.read_bytes()
    subprocess.run([sys.executable, "preview/build_preview.py"], cwd=ROOT, check=True, capture_output=True)
    after = PREVIEW.read_bytes()
    assert before == after
    html = after.decode("utf-8")
    assert not re.search(r"<(?:script|link)[^>]+(?:src|href)=['\"]https?://", html, re.I)
    assert "https://" not in html and "http://" not in html
    assert 'id="embeddedState" type="application/json">{}</script>' in html
    assert 'data-source-revision="pending"' in html
    assert "هیچ فعالیتی از پیش وارد نشده است" in html
    catalog_match = re.search(r'<script id="catalogData" type="application/json">(.*?)</script>', html)
    weight_match = re.search(r'<script id="groupWeightsData" type="application/json">(.*?)</script>', html)
    assert catalog_match and weight_match
    catalog, weights = json.loads(catalog_match.group(1)), json.loads(weight_match.group(1))
    assert set(catalog) == {"علوم ریاضی و فنی", "علوم تجربی", "علوم انسانی", "هنر", "زبان‌های خارجی"}
    assert weights["علوم تجربی"]["exam"] == 40 and weights["هنر"]["transcript"] == 30


def test_preview_exposes_core_pages_and_persistent_data_controls():
    html = PREVIEW.read_text(encoding="utf-8")
    for label in (
        "داشبورد", "برنامهٔ امروز", "فعالیت‌ها", "آزمون و تحلیل", "مرور تطبیقی",
        "گزارش‌ها", "تنظیمات", "مباحث و تسلط", "انتخاب همهٔ درس‌ها", "انتخاب همهٔ کتاب‌ها",
        "خروجی HTML داده‌دار", "پشتیبان JSON", "بازیابی فایل", "ساخت مسیر پیشنهادی",
    ):
        assert label in html
    for implementation_marker in (
        "localStorage", "showSaveFilePicker", "backupJSON", "restoreFile",
        "wizard-finish", "subjectWeightsForm", "detectConflicts", "learningEvidence",
        "masteryMinSpacingDays", "addTopicEvidenceForm", "generateTopicPathway",
    ):
        assert implementation_marker in html
    assert "checked>" not in html


def test_preview_javascript_parses_when_node_is_available(tmp_path: Path):
    node = shutil.which("node")
    if node is None:
        return
    combined = tmp_path / "preview.js"
    combined.write_text(
        "\n".join((ROOT / "preview" / name).read_text(encoding="utf-8") for name in ("core.js", "forms.js", "app.js")),
        encoding="utf-8",
    )
    subprocess.run([node, "--check", str(combined)], cwd=ROOT, check=True, capture_output=True, text=True)
