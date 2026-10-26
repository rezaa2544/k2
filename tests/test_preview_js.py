"""تست اجرایی پیش‌نمایش HTML: هر ۱۳ صفحه و جریان‌های تعاملی بدون مرورگر.

پیش‌نمایش باید واقعاً کار کند، نه اینکه فقط ظاهرش درست باشد. این تست با یک
شبیه‌ساز DOM سبک، کد جاوااسکریپت پیش‌نمایش را اجرا می‌کند و ناوبری و
جریان تایمر/مهلت/مشکل/بازبینی شبانه را می‌آزماید.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PREVIEW_DIR = ROOT / "preview"
PREVIEW = PREVIEW_DIR / "K2-preview.html"

PAGES = [
    "dashboard", "weekly", "courses", "backlogs", "classes", "problems",
    "tests", "review", "comprehensive", "deadlines", "timer", "reports",
    "settings",
]

NODE = shutil.which("node") or shutil.which("nodejs")


@pytest.fixture(scope="module")
def preview_js() -> str:
    return "\n".join(
        (PREVIEW_DIR / name).read_text(encoding="utf-8")
        for name in ("core.js", "syllabus.js", "backlog.js", "examseries.js", "priority.js", "forms.js", "app.js")
    )


def _smoke_script() -> str:
    return r"""
const factory_src = process.argv[2];
function makeEl(tag) {
  const el = {
    tagName: tag || 'div', children: [], dataset: {}, style: {}, attrs: {},
    classList: { _s: new Set(), add(...c){c.forEach(x=>this._s.add(x))}, remove(...c){c.forEach(x=>this._s.delete(x))},
      toggle(c,on){ if(on===undefined) on=!this._s.has(c); on?this._s.add(c):this._s.delete(c); return on },
      contains(c){return this._s.has(c)} },
    _listeners: {}, textContent: '', value: '', checked: false, hidden: false, disabled: false,
    files: [], scrollTop: 0, innerHTML: '', parentNode: null,
    addEventListener(t,f){(this._listeners[t]=this._listeners[t]||[]).push(f)},
    removeEventListener(){}, focus(){}, blur(){}, select(){}, scrollIntoView(){}, setSelectionRange(){},
    setAttribute(k,v){this.attrs[k]=v}, getAttribute(k){return k in this.attrs?this.attrs[k]:null},
    removeAttribute(k){delete this.attrs[k]}, append(...c){c.forEach(x=>this.children.push(x))},
    remove(){}, click(){},
    matches(sel){ if(sel==='.nav-item') return !!this.dataset.page;
      if(sel && sel.indexOf('[data-action]')===0) return !!this.dataset.action; return false },
    closest(sel){ let cur=this; while(cur){ if(cur.matches && cur.matches(sel)) return cur; cur=cur.parentNode } return null },
    querySelector(){return null}, querySelectorAll(){return []},
    getBoundingClientRect(){return {top:0,left:0,width:0,height:0}},
  };
  return el;
}
const byId = {};
for (const id of ['pageTitle','pageHint','pageContent','navList','toast','statusMessage','storageState',
  'dateLabel','refreshButton','modalBackdrop','modalTitle','modalBody','modalActions',
  'modalClose','modalForm','restoreInput','programMenuButton','programMenu','helpMenuButton','helpMenu',
  'embeddedState','catalogData','groupWeightsData','csvData','timerClock']) byId['#'+id] = makeEl();
const navItems = ['dashboard','weekly','courses','backlogs','classes','problems','tests','review',
  'comprehensive','deadlines','timer','reports','settings','today','topics','onboarding']
  .map(page => { const b = makeEl('button'); b.dataset.page = page; return b; });
const document = Object.assign(makeEl('#document'), {
  documentElement: makeEl('html'), body: makeEl('body'), createElement: makeEl,
  querySelector(sel){ if (byId[sel]) return byId[sel];
    if (sel && sel[0]==='#' && byId[sel]) return byId[sel]; return null },
  querySelectorAll(sel){ return sel==='.nav-item' ? navItems : [] },
  getElementById(id){ return byId['#'+id] || null },
});
const store = {};
const localStorage = { getItem:k=>k in store?store[k]:null, setItem:(k,v)=>{store[k]=String(v)},
  removeItem:k=>{delete store[k]}, clear:()=>{for(const k in store) delete store[k]} };
const window = { K2_CATALOG: {}, K2_GROUP_WEIGHTS: {}, showSaveFilePicker: null };
const preview = new Function('document','localStorage','window','Intl','structuredClone','navigator',
  'confirm','setTimeout','clearTimeout','URL','Blob','console','FormData',
  factory_src + '\nreturn window.K2Preview;')(document, localStorage, window, Intl,
  o=>JSON.parse(JSON.stringify(o)), {userAgent:'node'}, ()=>true, ()=>0, ()=>{},
  {createObjectURL:()=>'', revokeObjectURL:()=>{}},
  class Blob { constructor(p){this.parts=p} }, console,
  class FormData { get(){return null} has(){return false} getAll(){return []} });
if (!preview) { console.log('FAIL: K2Preview missing'); process.exit(1) }
const clicks = (document._listeners && document._listeners.click) || [];
function clickNav(page){ const b = navItems.find(x=>x.dataset.page===page);
  if(!b) throw new Error('nav missing '+page);
  for (const fn of clicks) fn({target:b, preventDefault(){}, stopPropagation(){}}) }
function clickAction(action){ const b = makeEl('button'); b.dataset.action = action;
  for (const fn of clicks) fn({target:b, preventDefault(){}, stopPropagation(){}}) }
let failures = 0;
const titles = {};
for (const page of ['dashboard','weekly','courses','backlogs','classes','problems','tests','review',
  'comprehensive','deadlines','timer','reports','settings']) {
  try {
    clickNav(page);
    const title = document.querySelector('#pageTitle').textContent;
    const html = document.querySelector('#pageContent').innerHTML || '';
    titles[page] = title;
    if (!html || html.length < 40) throw new Error('empty render');
  } catch (e) { failures++; console.log('FAIL page ' + page + ': ' + e.message) }
}
// جریان تایمر
try {
  clickNav('timer'); clickAction('timer-start');
  let st = preview.getState();
  if (!st.timer.running) throw new Error('timer start');
  clickAction('timer-pause');
  st = preview.getState();
  if (!st.timer.paused) throw new Error('timer pause');
  clickAction('timer-pause');
  st = preview.getState();
  if (st.timer.paused) throw new Error('timer resume');
  clickAction('timer-stop');
  st = preview.getState();
  if (!st.sessions.length) throw new Error('session save');
  if (st.timer.running) throw new Error('timer still running');
} catch (e) { failures++; console.log('FAIL timer flow: ' + e.message) }
// دیالوگ‌ها
for (const [page, action] of [['deadlines','add-deadline'],['problems','add-problem'],
  ['weekly','nightly-review'],['timer','add-session'],['courses','topic-fields']]) {
  try { clickNav(page); clickAction(action); }
  catch (e) { failures++; console.log('FAIL dialog ' + action + ': ' + e.message) }
}
console.log(JSON.stringify({failures, titles}));
process.exit(failures ? 1 : 0);
"""


@pytest.mark.skipif(NODE is None, reason="node برای اجرای پیش‌نمایش لازم است")
def test_preview_pages_and_interactive_flows_run(preview_js, tmp_path):
    """هر ۱۳ صفحه رندر می‌شوند و جریان تایمر/دیالوگ‌ها بدون خطاست."""
    script = _smoke_script()
    # کد پیش‌نمایش از سطر فرمان بلندتر از آن است که بشود پاس داد؛ از فایل
    # موقت می‌خوانیم.
    payload = tmp_path / "preview-bundle.js"
    payload.write_text(preview_js, encoding="utf-8")
    harness = tmp_path / "smoke.js"
    prelude = (
        "const fs=require('fs');const src=fs.readFileSync("
        + repr(str(payload))
        + ",'utf8');\n"
    )
    harness.write_text(
        prelude
        + script.replace(
            "const factory_src = process.argv[2];", "const factory_src = src;"
        ),
        encoding="utf-8",
    )
    # روی ویندوز رمزگذاری پیش‌فرض متنِ خروجی زیرفروندها cp1252 است و
    # فارسیِ خروجی node را نمی‌خواند؛ رمزگذاری را صریح می‌کنیم.
    result = subprocess.run(
        [NODE, str(harness)],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        cwd=str(ROOT),
    )
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    assert result.returncode == 0, stdout + stderr
    assert "FAIL" not in stdout, stdout


def test_preview_has_no_network_calls_in_js():
    """کد پیش‌نمایش هیچ درخواست شبکه‌ای نمی‌زند."""
    js = "\n".join(
        (PREVIEW_DIR / name).read_text(encoding="utf-8")
        for name in ("core.js", "syllabus.js", "backlog.js", "examseries.js", "priority.js", "forms.js", "app.js")
    )
    for pattern in (
        r"\bfetch\s*\(", r"XMLHttpRequest", r"\.open\s*\(\s*['\"](GET|POST)",
        r"WebSocket", r"navigator\.sendBeacon", r"importScripts",
        r"https?://(?!www\.w3\.org)",
    ):
        assert not re.search(pattern, js), pattern


def test_preview_pages_match_desktop_navigation():
    """فهرست صفحات پیش‌نمایش با نسخهٔ دسکتاپ یکی است (بند ۱۷).

    پیش‌نمایش سیزده آیتم ناوبری دارد و درخت سرفصل داخل همان صفحهٔ
    «مباحث» باز می‌شود؛ دسکتاپ برای همان کار صفحهٔ مستقل «سرفصل درس‌ها»
    را دارد. پس عنوان «سرفصل درس‌ها» عمداً از مقایسهٔ عنوان‌ها کنار
    گذاشته می‌شود، نه اینکه صفحه‌ای گم شده باشد.
    """
    from k2.ui.app import NAV_ITEMS

    html = PREVIEW.read_text(encoding="utf-8")
    nav_titles = re.findall(r'<span class="nav-icon">[^<]*</span><span>([^<]+)</span>', html)
    assert len(nav_titles) == 13
    desktop_titles = [
        title for _, title, _ in NAV_ITEMS if title != "سرفصل درس‌ها"
    ]
    assert nav_titles == desktop_titles
    assert "سرفصل درس‌ها" in [t for _, t, _ in NAV_ITEMS]


def _setup_wizard_script() -> str:
    """هر ۷ گام جادوگر پیش‌نمایش رندر می‌شوند و کنش‌های هر گام برداشته می‌شود."""
    return r"""
// «failures» و «rows» را اسکریپت میزبان تعریف کرده؛ اینجا فقط استفاده می‌کنیم.
const TOTAL = 7;
const wizardRows = [];
clickAction('setup');
const host = document.querySelector('#pageContent');
if (!host) { console.log('FAIL: pageContent missing'); process.exit(1) }
for (let step = 0; step < TOTAL; step++) {
  try {
    preview.setState(Object.assign({}, preview.getState(), {
      onboarding: Object.assign({}, preview.getState().onboarding, { step }),
    }));
    preview.render();
    const html = host.innerHTML || '';
    if (html.length < 40) throw new Error('empty render');
    // فقط ناحیهٔ کنش‌های گام را می‌کنیم؛ بقیهٔ صفحه ممکن است <span> معنادار
    // داشته باشد ولی این ناحیه قبلاً با <span></span> پُر می‌شد.
    const m = html.match(/<div class="setup-actions">([\s\S]*?)<\/div>/);
    if (!m) throw new Error('setup-actions missing');
    const inner = m[1];
    if (inner.indexOf('<span></span>') >= 0) throw new Error('empty placeholder span');
    if (inner.indexOf('<span >') >= 0) throw new Error('empty placeholder span (spaced)');
    const labels = (inner.match(/>([^<>]+)</g) || []).map(s => s.slice(1, -1).trim())
      .filter(Boolean);
    if (!labels.length) throw new Error('no action buttons');
    if (!labels.some(l => l.indexOf('ذخیره') === 0)) throw new Error('no save button');
    wizardRows.push(step + ':' + labels.join('|'));
  } catch (e) { failures++; console.log('FAIL step ' + step + ': ' + e.message) }
}
console.log(JSON.stringify({ failures, titles, rows: wizardRows }));
process.exit(failures ? 1 : 0);
"""


@pytest.mark.skipif(NODE is None, reason="node برای اجرای پیش‌نمایش لازم است")
def test_setup_wizard_steps_have_no_dead_placeholder_spans(preview_js, tmp_path):
    """ردیف کنش‌های هر گام راه‌اندازی فقط دکمهٔ واقعی دارد.

    پیش‌تر برای خانه‌های خالی ``<span></span>`` ساخته می‌شد و با
    ``justify-content:space-between`` فاصلهٔ مردهٔ بزرگ می‌ساخت و دکمهٔ اصلی
    را به لبهٔ مقابل کارت پرت می‌کرد.
    """
    payload = tmp_path / "preview-bundle.js"
    payload.write_text(preview_js, encoding="utf-8")
    harness = tmp_path / "wizard.js"
    prelude = (
        "const fs=require('fs');const src=fs.readFileSync("
        + repr(str(payload))
        + ",'utf8');\n"
    )
    harness.write_text(
        prelude
        + _smoke_script().replace(
            "const factory_src = process.argv[2];", "const factory_src = src;"
        ).replace(
            "console.log(JSON.stringify({failures, titles}));\nprocess.exit(failures ? 1 : 0);",
            _setup_wizard_script(),
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [NODE, str(harness)],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        cwd=str(ROOT),
    )
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    assert result.returncode == 0, stdout + stderr
    assert "FAIL" not in stdout, stdout
    import json

    data = json.loads(stdout.strip().splitlines()[-1])
    assert data["failures"] == 0
    assert len(data["rows"]) == 7


def test_preview_setup_page_scrolls_inside_a_bounded_window():
    """صفحهٔ بلند باید داخل پنجرهٔ شبیه‌سازی‌شده اسکرول شود، نه بیرون زدن.

    بی ``overflow-y:auto`` روی ``.page-content`` و بی ``max-height`` روی
    ``.app-layout``، صفحهٔ راه‌اندازی (فهرست کامل کتاب‌ها) کل پنجره را به
    بلندی هزاران پیکسل می‌کشید و ``.app-window{overflow:hidden}`` بقیه را
    می‌بُرد.
    """
    css = (PREVIEW_DIR / "base.css").read_text(encoding="utf-8")
    html = PREVIEW.read_text(encoding="utf-8")

    page_content = re.search(r"\.page-content\{([^}]*)\}", css)
    assert page_content, "قاعدهٔ .page-content پیدا نشد"
    assert "overflow-y:auto" in page_content.group(1), page_content.group(1)
    assert "overflow-x:hidden" in page_content.group(1), page_content.group(1)

    app_layout = re.search(r"\.app-layout\{([^}]*)\}", css)
    assert app_layout, "قاعدهٔ .app-layout پیدا نشد"
    assert "max-height" in app_layout.group(1), app_layout.group(1)
    assert "min-height:750px" in app_layout.group(1), app_layout.group(1)

    # همان قواعد باید در HTML ساخته‌شده هم باشند.
    assert ".page-content{min-height:0;flex:1;overflow-y:auto" in html
    assert ".app-layout{display:flex;min-height:750px;max-height:" in html


def test_preview_setup_actions_push_primary_button_to_the_far_edge():
    """کنش اصلی لبهٔ مقابل است، بدون فاصلهٔ مردهٔ ``space-between``."""
    css = (PREVIEW_DIR / "base.css").read_text(encoding="utf-8")
    actions = re.search(r"\.setup-actions\{([^}]*)\}", css)
    assert actions, "قاعدهٔ .setup-actions پیدا نشد"
    assert "justify-content:space-between" not in actions.group(1)
    assert "justify-content:flex-start" in actions.group(1)
    assert ".setup-actions .btn.primary{margin-inline-start:auto}" in css
    # و در HTML نهایی هم.
    assert ".setup-actions .btn.primary{margin-inline-start:auto}" in (
        PREVIEW.read_text(encoding="utf-8")
    )
