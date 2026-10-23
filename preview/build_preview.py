"""Assemble the offline, single-file K2 browser preview from local sources."""
from __future__ import annotations
import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "src"))
from k2.konkur_catalog import (  # noqa: E402
    EXAM_WEIGHT_BY_GROUP,
    GENERAL_SUBJECT_SYLLABUS,
    GROUPS,
    SYLLABUS_BY_COURSE,
    SYLLABUS_STATUS,
    SYLLABUS_STATUS_LABEL,
    courses_for_group,
)


def _catalog_from_domain() -> dict:
    """Preview catalog is built from the Python source of truth, never hand-copied."""
    result = {}
    for group in GROUPS:
        result[group] = []
        for course in courses_for_group(group):
            result[group].append({
                "name": course.name,
                "type": course.course_type,
                "examCoefficient": course.exam_coefficient,
                "coefficientStatus": course.coefficient_status,
                "sourceLabel": "اطلاعیهٔ بازنشرشده؛ منبع اولیه مستقیم cross-check نشده",
                "note": course.note,
                "books": [{
                    "title": book.title, "code": book.code, "grade": book.grade,
                    "editionYear": book.edition_year, "status": book.status,
                    "transcriptNote": book.transcript_note,
                    "relation": book.relation,
                } for book in course.books],
            })
    return result


catalog = _catalog_from_domain()
# escaping outside the f-string keeps this file importable on Python < 3.12,
# where backslashes are not allowed inside f-string expression parts.
_catalog_json = json.dumps(catalog, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
weights = {
    group: {"exam": exam, "transcript": transcript, "source": "reported_official_notice_1406"}
    for group, (exam, transcript) in EXAM_WEIGHT_BY_GROUP.items()
}
(ROOT / "catalog.json").write_text(
    json.dumps(catalog, ensure_ascii=False, separators=(",", ":")),
    encoding="utf-8",
    newline="\n",
)
(ROOT / "group_weights.json").write_text(
    json.dumps(weights, ensure_ascii=False, separators=(",", ":")),
    encoding="utf-8",
    newline="\n",
)

# ---------------------------------------------------------------------------
# سرفصل درس‌ها (پایه ← فصل ← گفتار) — دادهٔ اولیه تأییدنشده
# ---------------------------------------------------------------------------
#: ساختار سرفصل برای پیش‌نمایش: درس ← پایه ← فهرست فصل‌ها.
syllabus: dict[str, dict[str, list[dict]]] = {}
for _course, _by_grade in SYLLABUS_BY_COURSE.items():
    syllabus[_course] = {
        str(_grade): [
            {"no": _ch["no"], "title": _ch["title"], "sections": _ch["sections"]}
            for _ch in _chapters
        ]
        for _grade, _chapters in sorted(_by_grade.items())
    }
_syllabus_meta = {
    "status": SYLLABUS_STATUS,
    "statusLabel": SYLLABUS_STATUS_LABEL,
    "generalSubjects": GENERAL_SUBJECT_SYLLABUS,
}
_syllabus_json = json.dumps(
    {"meta": _syllabus_meta, "courses": syllabus}, ensure_ascii=False, separators=(",", ":")
).replace("<", "\\u003c")

_weights_json = json.dumps(weights, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")

# ---------------------------------------------------------------------------
# فونت همراه پیش‌نمایش: داخل خود فایل HTML embed می‌شود تا آفلاین و تک‌فایلی
# بماند (هیچ نشانی https لازم نیست). وزن‌ها همان سلسله‌مراتب دسکتاپ است.
# ---------------------------------------------------------------------------

#: وزن‌های فونت استعداد که همراه پیش‌نمایش می‌شوند.
FONT_WEIGHTS = (400, 600, 700, 800)


def _font_face() -> str:
    """قواعد ``@font-face`` با دادهٔ base64 فونت‌های استعداد."""
    rules = []
    for weight in FONT_WEIGHTS:
        path = ROOT / "fonts" / f"estedad-arabic-{weight}-normal.woff2"
        if not path.exists():
            continue
        payload = base64.b64encode(path.read_bytes()).decode("ascii")
        rules.append(
            "@font-face{font-family:'Estedad';font-style:normal;"
            f"font-weight:{weight};font-display:swap;"
            f"src:url(data:font/woff2;base64,{payload}) format('woff2')}}"
        )
    return "\n".join(rules)


_font_css = _font_face()
css = (ROOT / "base.css").read_text(encoding="utf-8")
app_js = "\n".join(
    (ROOT / name).read_text(encoding="utf-8")
    for name in ("core.js", "syllabus.js", "forms.js", "app.js")
)
extra_css = r'''
/* Functional browser-preview controls */
input,select,textarea{width:100%;min-height:38px;padding:7px 10px;border:1px solid var(--border);border-radius:8px;background:#fff;color:var(--text)}
input[type=checkbox],input[type=radio]{width:17px;min-height:17px;accent-color:var(--accent)}
label{display:flex;flex-direction:column;gap:5px;color:var(--muted);font-size:12px;font-weight:700}
label.check-label,.course-select,.book-row,.day-picker label{flex-direction:row;align-items:center;gap:9px}
textarea{min-height:72px;resize:vertical}.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:12px 0}
.button-row{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.section-row{display:flex;align-items:center;justify-content:space-between;gap:10px}
.table-wrap{overflow:auto;border:1px solid var(--border);border-radius:12px;background:#fff}
table{width:100%;border-collapse:collapse;min-width:680px}th,td{padding:9px 11px;border-bottom:1px solid #edf0ef;text-align:right;vertical-align:middle;font-size:11px}th{background:#f7faf8;color:#526765;font-weight:800}tr:last-child td{border-bottom:0}
.catalog-course{margin:10px 0}.course-select{display:grid;grid-template-columns:auto 1fr auto;justify-content:initial}.book-list{display:grid;gap:6px;margin-top:10px}.book-row{display:grid;grid-template-columns:auto 1fr;align-items:start;padding:7px 9px;border:1px solid #edf0ef;border-radius:8px;background:#fcfdfc}.book-row small{grid-column:2;color:var(--muted);font-weight:400}.pill{padding:2px 8px;border-radius:99px;font-size:10px;white-space:nowrap}.pill.info{background:var(--info-soft);color:var(--info)}.pill.gray{background:#f0f2f1;color:#64716e}.list-row{display:flex;align-items:center;justify-content:space-between;gap:9px;padding:9px 0;border-bottom:1px solid var(--border)}
.day-picker{display:flex;flex-wrap:wrap;gap:8px;border:1px solid var(--border);border-radius:9px;padding:9px}.day-picker label{font-size:10px}.warning{background:var(--warn-soft);border-color:#ead9aa;color:#71551b}.danger{color:var(--danger)}
.modal-progress{height:7px;overflow:hidden;border-radius:8px;background:#e7efeb;margin:8px 0 13px}.modal-progress i{display:block;height:100%;background:var(--accent);transition:width .2s}.modal-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:14px}
#modalBackdrop{overflow:auto;padding:20px}.modal{width:min(850px,96vw);max-height:92vh;overflow:auto}.menu-item{cursor:pointer}.status-bar .privacy{white-space:nowrap}
@media(max-width:720px){.form-grid{grid-template-columns:1fr}.section-row{align-items:flex-start;flex-direction:column}.course-select{grid-template-columns:auto 1fr}.course-select .pill{grid-column:2}.button-row>.btn{flex:1}}
'''
html = f'''<!doctype html>
<html lang="fa" dir="rtl" data-source-revision="pending">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light">
<title>K2 — پیش‌نمایش آفلاین تعاملی</title><style>{_font_css}\n{css}\n{extra_css}</style>
</head><body>
<div class="preview-wrap">
  <section class="app-window" aria-label="K2"><header class="menu-bar"><div class="menu-group"><div class="menu-wrap"><button class="menu-button" id="programMenuButton" data-menu="programMenu" aria-expanded="false">برنامه</button><div class="menu-panel" id="programMenu"><button class="menu-item" data-action="setup">راه‌اندازی / ادامهٔ مصاحبه</button><button class="menu-item" data-action="backup-json">پشتیبان JSON</button><button class="menu-item" data-action="save-html">خروجی HTML داده‌دار</button><button class="menu-item" data-action="restore">بازیابی داده</button><div class="menu-separator"></div><button class="menu-item" data-action="quit">خروج</button></div></div><div class="menu-wrap"><button class="menu-button" id="helpMenuButton" data-menu="helpMenu" aria-expanded="false">راهنما</button><div class="menu-panel" id="helpMenu"><button class="menu-item" data-action="about">دربارهٔ K2</button><button class="menu-item" data-action="privacy">ذخیره و حریم خصوصی</button></div></div></div><div class="menu-meta"><span id="storageState">ذخیره‌سازی آماده</span><span class="shortcut">F5 · Ctrl+S · Ctrl+Q</span></div></header>
  <div class="app-layout"><aside class="sidebar"><div class="brand"><div class="brand-mark">K2</div><div><div class="brand-name">مشاور هوشمند</div><div class="brand-caption">کنکور · برنامه‌ریزی واقع‌بینانه</div></div></div><div class="side-divider"></div><div class="side-caption">فضای مطالعه</div><nav aria-label="بخش‌های برنامه"><ul class="nav-list" id="navList"><li><button class="nav-item active" data-page="dashboard"><span class="nav-icon">⌂</span><span>داشبورد امروز</span></button></li><li><button class="nav-item" data-page="weekly"><span class="nav-icon">▤</span><span>برنامه هفتگی</span></button></li><li><button class="nav-item" data-page="courses"><span class="nav-icon">▦</span><span>بانک دروس</span></button></li><li><button class="nav-item" data-page="backlogs"><span class="nav-icon">◱</span><span>عقب‌افتادگی‌ها</span></button></li><li><button class="nav-item" data-page="classes"><span class="nav-icon">◷</span><span>کلاس‌های من</span></button></li><li><button class="nav-item" data-page="problems"><span class="nav-icon">✶</span><span>مشکلات یادگیری</span></button></li><li><button class="nav-item" data-page="tests"><span class="nav-icon">◈</span><span>تست و تحلیل</span></button></li><li><button class="nav-item" data-page="review"><span class="nav-icon">↻</span><span>مرورهای من</span></button></li><li><button class="nav-item" data-page="comprehensive"><span class="nav-icon">◉</span><span>آزمون‌های جامع</span></button></li><li><button class="nav-item" data-page="deadlines"><span class="nav-icon">⏱</span><span>مهلت‌های من</span></button></li><li><button class="nav-item" data-page="timer"><span class="nav-icon">◔</span><span>ساعت مطالعه</span></button></li><li><button class="nav-item" data-page="reports"><span class="nav-icon">▣</span><span>گزارش مشاور</span></button></li><li><button class="nav-item" data-page="settings"><span class="nav-icon">⚙</span><span>تنظیمات</span></button></li></ul></nav><div class="sidebar-footer"><strong>● آفلاین و خصوصی</strong>ذخیره در مرورگر؛ پشتیبان قابل‌انتقال</div></aside>
  <main class="content-area"><header class="topbar"><div class="top-title-box"><h1 class="top-title" id="pageTitle">داشبورد</h1><p class="top-subtitle" id="pageHint">خلاصهٔ وضعیت و قدم بعدی</p></div><span class="date-label" id="dateLabel"></span><button class="btn" id="refreshButton" title="تازه‌سازی همهٔ نماها">↻ تازه‌سازی</button></header><section class="page-content" id="pageContent" aria-live="polite"></section></main></div>
  <footer class="status-bar"><span id="statusMessage">پایگاه دادهٔ خالی · آمادهٔ راه‌اندازی</span><span class="privacy"><span class="privacy-dot">●</span> <span>داده‌ها روی همین دستگاه می‌مانند</span></span></footer></section>
</div>
<div class="toast" id="toast" role="status" aria-live="polite"></div><div class="modal-backdrop" id="modalBackdrop" role="presentation"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="modalTitle"><div class="modal-head"><h2 id="modalTitle"></h2><button class="modal-close" id="modalClose" aria-label="بستن">×</button></div><div id="modalBody"></div><div class="modal-actions" id="modalActions"></div></section></div><input id="restoreInput" type="file" accept=".json,.html,application/json,text/html" hidden>
<script id="catalogData" type="application/json">{_catalog_json}</script>
<script id="syllabusData" type="application/json">{_syllabus_json}</script>
<script id="groupWeightsData" type="application/json">{_weights_json}</script>
<script id="embeddedState" type="application/json">{{}}</script>
<script>window.K2_CATALOG=JSON.parse(document.getElementById('catalogData').textContent);window.K2_GROUP_WEIGHTS=JSON.parse(document.getElementById('groupWeightsData').textContent);window.K2_SYLLABUS=JSON.parse(document.getElementById('syllabusData').textContent).courses;window.K2_SYLLABUS_META=JSON.parse(document.getElementById('syllabusData').textContent).meta;</script>
<script>{app_js}</script>
</body></html>
'''
# Preserve no hard-coded choice or test/user data in the fresh-file payload.
(ROOT / "K2-preview.html").write_text(html, encoding="utf-8", newline="\n")
print(f"Built {ROOT / 'K2-preview.html'} ({len(html)} bytes)")
