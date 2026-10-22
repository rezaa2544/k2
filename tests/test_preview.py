from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / "preview" / "K2-preview.html"


def test_preview_is_reproducible_single_file_and_offline():
    before = PREVIEW.read_bytes()
    subprocess.run([sys.executable, "preview/build_preview.py"], cwd=ROOT, check=True, capture_output=True)
    after = PREVIEW.read_bytes()
    # مقایسه با پایان‌خط یکدست‌شده لازم است: روی ویندوز ``git checkout``
    # فایل را CRLF می‌کند و ساختِ بازتولیدشده LF است؛ بی این یکدست‌سازی
    # همین تست روی ویندوز شکست می‌خورد.
    assert before.replace(b"\r\n", b"\n") == after.replace(b"\r\n", b"\n")
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
        "داشبورد امروز", "برنامه هفتگی", "بانک دروس", "عقب‌افتادگی‌ها",
        "کلاس‌های من", "مشکلات یادگیری", "تست و تحلیل", "مرورهای من",
        "آزمون‌های جامع", "مهلت‌های من", "ساعت مطالعه", "گزارش مشاور",
        "تنظیمات", "انتخاب همهٔ درس‌ها", "انتخاب همهٔ کتاب‌ها",
        "خروجی HTML داده‌دار", "پشتیبان JSON", "بازیابی فایل",
        "ساخت مسیر پیشنهادی", "کارهای تثبیت فعال",
        # زیربخش‌هایی که در صفحه‌های سیزده‌گانه حفظ شده‌اند
        "مباحث و تسلط", "تثبیت حافظه", "فعالیت‌ها و صف کارها",
    ):
        assert label in html, label
    for implementation_marker in (
        "localStorage", "showSaveFilePicker", "backupJSON", "restoreFile",
        "wizard-finish", "subjectWeightsForm", "detectConflicts", "learningEvidence",
        "masteryMinSpacingDays", "addTopicEvidenceForm", "generateTopicPathway",
        "consolidationPage", "ladderState",
        # نشانه‌های پیاده‌سازی قابلیت‌های تازه
        "timer-start", "timer-pause", "timer-stop", "addDeadlineForm",
        "addSessionForm", "addProblemForm", "nightlyReviewDialog", "backCalculate",
        "KONKUR_STAGES", "FINAL_STAGES", "sessionTotals", "weeklyPage",
    ):
        assert implementation_marker in html, implementation_marker
    assert html.count('class="nav-item') == 13
    assert "checked>" not in html


def test_preview_zip_bundle_is_current_and_reproducible():
    """ZIP دانلود پیش‌نمایش باید تازه و قطعی باشد تا لینک README کهنه نشود."""
    sys.path.insert(0, str(ROOT / "preview"))
    try:
        from build_preview_zip import ENTRY, build_zip
    finally:
        sys.path.pop(0)

    bundle = ROOT / "downloads" / "K2-preview-html.zip"
    assert bundle.exists(), "فایل ZIP دانلود در downloads/ نیست"
    from build_preview_zip import normalize

    payload = bundle.read_bytes()
    with zipfile.ZipFile(bundle) as archive:
        assert archive.namelist() == [ENTRY]
        html_from_zip = archive.read(ENTRY)
    # محتوای ZIP باید همان HTML جاری باشد (مستقل از CRLF ویندوز)
    on_disk = (ROOT / "preview" / "K2-preview.html").read_bytes()
    assert html_from_zip == normalize(on_disk)
    # بسته باید دقیقاً با اسکریپت بازتولید شود (کهنگی یعنی عدم تطابق)
    assert payload == build_zip(on_disk)


def test_preview_zip_bundle_is_platform_independent(monkeypatch):
    """بسته روی ویندوز و یونیکس بایت‌به‌بایت یکسان ساخته می‌شود.

    ``zipfile.ZipInfo`` مقدار create_system را از sys.platform می‌گیرد؛ بی تثبیت
    آن هش بسته روی ویندوز تغییر می‌کند و CI شکست می‌خورد.
    """
    sys.path.insert(0, str(ROOT / "preview"))
    try:
        from build_preview_zip import build_zip
    finally:
        sys.path.pop(0)

    on_disk = (ROOT / "preview" / "K2-preview.html").read_bytes()
    unix_bytes = build_zip(on_disk)
    monkeypatch.setattr(sys, "platform", "win32")
    assert build_zip(on_disk) == unix_bytes
    monkeypatch.setattr(sys, "platform", "darwin")
    assert build_zip(on_disk) == unix_bytes


def test_preview_javascript_parses_when_node_is_available(tmp_path: Path):
    node = shutil.which("node")
    if node is None:
        return
    combined = tmp_path / "preview.js"
    combined.write_text(
        "\n".join((ROOT / "preview" / name).read_text(encoding="utf-8") for name in ("core.js", "forms.js", "app.js")),
        encoding="utf-8",
    )
    subprocess.run(
        [node, "--check", str(combined)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
