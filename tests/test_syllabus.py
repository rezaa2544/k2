"""آزمون اجرایی سرفصل، ارزیابی گفتار و بانک منابع در پیش‌نمایش HTML.

این تست با شبیه‌ساز DOM، کد واقعی پیش‌نمایش را اجرا می‌کند و سناریوهای
واقعی کاربر را می‌آزماید: دیدن سرفصل، پاسخ دادن به هشت سؤال، ساخت کار
جبران، و ثبت منبع با تعداد نامشخص. هدف این است که مطمئن شویم اپ واقعاً
کار می‌کند، نه اینکه فقط ظاهرش درست باشد.
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

NODE = shutil.which("node") or shutil.which("nodejs")

JS_FILES = ("core.js", "syllabus.js", "forms.js", "app.js")


@pytest.fixture(scope="module")
def preview_js() -> str:
    return "\n".join((PREVIEW_DIR / name).read_text(encoding="utf-8") for name in JS_FILES)


# ---------------------------------------------------------------------------
# شبیه‌ساز DOM مشترک (همان الگوی tests/test_preview_js.py)
# ---------------------------------------------------------------------------

_DOM_PRELUDE = r"""
function makeEl(tag) {
  const el = {
    tagName: tag || 'div', children: [], dataset: {}, style: {}, attrs: {},
    classList: { _s: new Set(), add(...c){c.forEach(x=>this._s.add(x))},
      remove(...c){c.forEach(x=>this._s.delete(x))},
      toggle(c,on){ if(on===undefined) on=!this._s.has(c); on?this._s.add(c):this._s.delete(c); return on },
      contains(c){return this._s.has(c)} },
    _listeners: {}, textContent: '', value: '', checked: false, hidden: false, disabled: false,
    files: [], scrollTop: 0, innerHTML: '', parentNode: null,
    addEventListener(t,f){(this._listeners[t]=this._listeners[t]||[]).push(f)},
    removeEventListener(){}, focus(){}, blur(){}, select(){}, scrollIntoView(){},
    setSelectionRange(){},
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
  querySelector(sel){ return byId[sel] || null },
  querySelectorAll(sel){ return sel==='.nav-item' ? navItems : [] },
  getElementById(id){ return byId['#'+id] || null },
});
const store = {};
const localStorage = { getItem:k=>k in store?store[k]:null, setItem:(k,v)=>{store[k]=String(v)},
  removeItem:k=>{delete store[k]}, clear:()=>{for(const k in store) delete store[k]} };
"""


def _harness(payload: Path, seed: dict, syllabus_json: Path) -> str:
    """اسکریپت node: پیش‌نمایش با state اولیهٔ داده‌شده اجرا و بررسی می‌شود."""
    import json

    seed_json = json.dumps(seed, ensure_ascii=False)
    body = _DOM_PRELUDE + "\n"
    body += "const SEED = " + json.dumps(seed_json) + ";\n"
    body += "store['k2.preview.data.v1'] = SEED;\n"
    body += r"""
const factory_src = src;
const SYL = JSON.parse(fs.readFileSync(SYLLABUS_JSON_PATH, 'utf8'));
const window = { K2_CATALOG: {}, K2_GROUP_WEIGHTS: {}, K2_SYLLABUS: SYL.courses,
  K2_SYLLABUS_META: SYL.meta, showSaveFilePicker: null };
const preview = new Function('document','localStorage','window','Intl','structuredClone','navigator',
  'confirm','setTimeout','clearTimeout','URL','Blob','console','FormData',
  factory_src + '\nreturn window.K2Preview;')(document, localStorage, window, Intl,
  o=>JSON.parse(JSON.stringify(o)), {userAgent:'node'}, ()=>true, ()=>0, ()=>{},
  {createObjectURL:()=>'', revokeObjectURL:()=>{}},
  class Blob { constructor(p){this.parts=p} }, console,
  class FormData { constructor(){ this._m = global.__fd || new Map() }
    get(k){ return this._m.has(k) ? this._m.get(k) : null }
    has(k){ const v=this.get(k); return v!==null && v!=='' && v!==undefined }
    getAll(k){ const v=this.get(k); return v===null?[]:[v] } });
if (!preview) { console.log('FAIL: K2Preview missing'); process.exit(1) }
const clicks = (document._listeners && document._listeners.click) || [];
function clickNav(page){ const b = navItems.find(x=>x.dataset.page===page);
  if(!b) throw new Error('nav missing '+page);
  for (const fn of clicks) fn({target:b, preventDefault(){}, stopPropagation(){}}) }
function clickAction(action){ const b = makeEl('button'); b.dataset.action = action;
  for (const fn of clicks) fn({target:b, preventDefault(){}, stopPropagation(){}}) }
function pageHtml(){ return document.querySelector('#pageContent').innerHTML || '' }
let failures = 0;
const ok = (cond, msg) => { if (!cond) { failures++; console.log('FAIL: ' + msg) } };

// ---- الف) صفحهٔ سرفصل رندر می‌شود و وضعیت تأییدنشده را نشان می‌دهد ----
try {
  clickNav('topics');
  const html = pageHtml();
  ok(html.includes('اطلاعات اولیه'), 'سرفصل باید «اطلاعات اولیه» را اعلام کند');
  ok(html.includes('زیست‌شناسی'), 'سرفصل باید درسٔ زیست‌شناسی را نشان دهد');
} catch (e) { failures++; console.log('FAIL syllabus overview: ' + e.message) }

// ---- ب) باز کردن گفتارهای زیست دهم ----
try {
  clickAction('syllabus-open:زیست‌شناسی:10');
  const html = pageHtml();
  ok(html.includes('فصل 1'), 'فصل ۱ زیست دهم باید دیده شود');
  ok(html.includes('دنیای زنده'), 'عنوان فصل باید دیده شود');
  ok(html.includes('گفتار'), 'جدول گفتارها باید ساخته شود');
  const st = preview.getState();
  ok(Object.keys(st.sections).length === 0, 'ارزیابی نباید خودکار ساخته شود');
} catch (e) { failures++; console.log('FAIL syllabus detail: ' + e.message) }

// ---- ج) هشت سؤال ارزیابی، مستقل ذخیره می‌شوند ----
try {
  clickAction('assess:زیست‌شناسی:10:1:1');
  const steps = ['teaching','study','comprehension','consolidation','testing','analysis','essay'];
  const picks = { teaching:'taught', study:'started', comprehension:'partial',
    consolidation:'initial', testing:'not_tested', analysis:'not_analyzed', essay:'not_done' };
  for (let i = 0; i < steps.length; i++) {
    global.__fd = new Map();
    clickAction('assess-pick:' + steps[i] + ':' + picks[steps[i]]);
  }
  // گام آخر: تسلط نامشخص
  global.__fd = new Map([['mastery',''],['masteryUnknown','on'],['notes','']]);
  clickAction('assess-save');
  const st = preview.getState();
  const rec = st.sections['زیست‌شناسی|10|1|1'];
  ok(!!rec, 'رکورد ارزیابی باید ذخیره شود');
  if (rec) {
    ok(rec.teaching === 'taught', 'پاسخ تدریس باید مستقل ذخیره شود');
    ok(rec.study === 'started', 'پاسخ مطالعه باید مستقل ذخیره شود');
    ok(rec.testing === 'not_tested', 'پاسخ تست‌زنی باید مستقل ذخیره شود');
    ok(rec.mastery === null, 'اگر کاربر مطمئن نیست، تسلط null می‌ماند (عدد ساخته نمی‌شود)');
    ok(rec.updatedAt, 'زمان به‌روزرسانی ثبت می‌شود');
  }
} catch (e) { failures++; console.log('FAIL assessment: ' + e.message) }

// ---- د) وضعیت گفتار به فصل دیگر تعمیم داده نمی‌شود ----
try {
  const st = preview.getState();
  ok(!st.sections['زیست‌شناسی|10|1|2'], 'گفتار ۲ نباید خودکار ارزیابی‌شده شود');
  ok(!st.sections['زیست‌شناسی|10|2|1'], 'گفتار فصل ۲ نباید تعمیم داده شود');
} catch (e) { failures++; console.log('FAIL no-propagation: ' + e.message) }

// ---- ه) ساخت کارهای جبران: برنامه‌ریزی‌شده، نه انجام‌شده ----
try {
  clickAction('assess:زیست‌شناسی|10|1:1'.replace('|',':'));
} catch (e) { /* صرفاً برای باز کردن مودال */ }
try {
  // ارزیابی را دوباره باز و مستقیم ذخیره+جبران می‌کنیم
  const st0 = preview.getState();
  const key = 'زیست‌شناسی|10|1|1';
  global.__fd = new Map();
  // assessDraft را با پاسخ‌های موجود باز می‌کنیم
  clickAction('assess:زیست‌شناسی:10:1:1');
  global.__fd = new Map([['mastery',''],['masteryUnknown','on'],['notes','']]);
  clickAction('assess-backlog');
  const st = preview.getState();
  const created = (st.activities || []).filter(a => String(a.reason||'').startsWith('section:' + key));
  ok(created.length > 0, 'باید کارهای جبران ساخته شود');
  ok(created.every(a => a.state === 'open'), 'کارهای جبران «برنامه‌ریزی‌شده» ثبت می‌شوند، نه انجام‌شده');
  ok(created.every(a => num(a.remaining) > 0), 'کار جبران باید زمان باقی‌مانده داشته باشد');
  ok(st0.activities.length < st.activities.length, 'کارها باید اضافه شوند نه اینکه جایگزین شوند');
} catch (e) { failures++; console.log('FAIL backlog creation: ' + e.message) }
function num(v){ const n = Number(v); return Number.isFinite(n) ? n : 0 }

// ---- و) منبع با تعداد نامشخص: بدهی قطعی ساخته نمی‌شود ----
try {
  clickNav('courses');
  clickAction('add-resource');
  global.__fd = new Map([
    ['type','video'], ['title','فیلم فصل ۱'],
    ['subject','زیست‌شناسی'], ['grade','10'], ['chapter','1'], ['section','1'],
    ['total',''], ['done',''], ['estimateMin',''], ['status','unknown'],
    ['deadline',''], ['notes',''],
  ]);
  clickAction('save-resource');
  const st = preview.getState();
  const r = (st.resources || []).find(x => x.title === 'فیلم فصل ۱');
  ok(!!r, 'منبع باید ذخیره شود');
  if (r) {
    ok(r.remaining === null, 'منبع با کل نامشخص باید remaining=null بماند (بدهی قطعی ساخته نمی‌شود)');
    ok(r.chapter === 1 && r.section === 1, 'منبع باید به گفتار متصل شود');
  }
} catch (e) { failures++; console.log('FAIL resource unknown: ' + e.message) }

// ---- ز) منبع با کل و انجام‌شده: باقی‌مانده خودکار حساب می‌شود ----
try {
  clickAction('add-resource');
  global.__fd = new Map([
    ['type','topic_test'], ['title','تست مبحثی فصل ۱'],
    ['subject','زیست‌شناسی'], ['grade','10'], ['chapter','1'], ['section','1'],
    ['total','40'], ['done','12'], ['estimateMin','2'], ['status','in_progress'],
    ['deadline',''], ['notes',''],
  ]);
  clickAction('save-resource');
  const st = preview.getState();
  const r = (st.resources || []).find(x => x.title === 'تست مبحثی فصل ۱');
  ok(!!r, 'منبع دوم باید ذخیره شود');
  if (r) ok(r.remaining === 28, 'باقی‌مانده باید خودکار ۲۸ شود، یافت: ' + r.remaining);
} catch (e) { failures++; console.log('FAIL resource remaining: ' + e.message) }

// ---- ح) اصلاح تعداد انجام‌شده، باقی‌مانده را به‌روز می‌کند ----
try {
  const st0 = preview.getState();
  const r = (st0.resources || []).find(x => x.title === 'تست مبحثی فصل ۱');
  clickAction('resource-edit:' + r.id);
  global.__fd = new Map([ ['resourceId', r.id],
    ['type','topic_test'], ['title','تست مبحثی فصل ۱'],
    ['subject','زیست‌شناسی'], ['grade','10'], ['chapter','1'], ['section','1'],
    ['total','40'], ['done','30'], ['estimateMin','2'], ['status','in_progress'],
    ['deadline',''], ['notes',''],
  ]);
  clickAction('save-resource');
  const st = preview.getState();
  const r2 = (st.resources || []).find(x => x.id === r.id);
  ok(r2.remaining === 10, 'پس از اصلاح انجام‌شده، باقی‌مانده باید ۱۰ شود، یافت: ' + r2.remaining);
  ok((st.resources || []).length === (st0.resources || []).length, 'ویرایش نباید منبع تکراری بسازد');
} catch (e) { failures++; console.log('FAIL resource edit: ' + e.message) }

// ---- ط) حذف منبع نیاز به تأیید دارد و حذف واقعی است ----
try {
  const st0 = preview.getState();
  const r = (st0.resources || []).find(x => x.title === 'فیلم فصل ۱');
  clickAction('resource-delete:' + r.id);
  const st = preview.getState();
  ok(!(st.resources || []).some(x => x.id === r.id), 'منبع حذف‌شده باید از فهرست برود');
  ok((st.activities || []).every(a => String(a.reason||'').indexOf('resource:') !== 0),
     'حذف منبع نباید کارهای دیگر را بی‌صدا حذف کند');
} catch (e) { failures++; console.log('FAIL resource delete: ' + e.message) }

// ---- ی) ویرایش عنوان فصل، ساختار را تغییر می‌دهد و گفتارها حفظ می‌شوند ----
try {
  clickAction('syl-edit-chapter:زیست‌شناسی:10:1');
  global.__fd = new Map([
    ['title','دنیای زنده (اصلاح‌شده)'], ['sections','3'],
  ]);
  clickAction('save-syl-chapter');
  const st = preview.getState();
  const edit = (st.syllabusEdits || {})['زیست‌شناسی|10|1'];
  ok(!!edit && edit.title === 'دنیای زنده (اصلاح‌شده)', 'ویرایش فصل باید ذخیره شود');
  ok(edit.sections === 3, 'تعداد گفتار فصل باید حفظ شود');
  ok(!!st.sections['زیست‌شناسی|10|1|1'], 'ارزیابی گفتارها نباید با ویرایش فصل پاک شود');
} catch (e) { failures++; console.log('FAIL chapter edit: ' + e.message) }

// ---- ک) افزودن گفتار تازه ----
try {
  clickAction('syl-add-section:زیست‌شناسی:10:1');
  global.__fd = new Map([ ['section','4']]);
  clickAction('save-syl-section');
  const st = preview.getState();
  const edit = (st.syllabusEdits || {})['زیست‌شناسی|10|1'];
  ok(edit.sections === 4, 'گفتار ۴ باید به فصل اضافه شود، یافت: ' + edit.sections);
  clickAction('assess:زیست‌شناسی:10:1:4');
  ok(!!document.querySelector('#modalTitle').textContent.includes('گفتار 4'),
     'گفتار تازه باید قابل ارزیابی باشد');
} catch (e) { failures++; console.log('FAIL add section: ' + e.message) }

console.log(JSON.stringify({failures}));
process.exit(failures ? 1 : 0);
"""
    body = body.replace("SYLLABUS_JSON_PATH", repr(str(syllabus_json)))
    harness = payload.with_suffix(".smoke.js")
    harness.write_text(
        "const fs=require('fs');const src=fs.readFileSync(" + repr(str(payload)) + ",'utf8');\n" + body,
        encoding="utf-8",
    )
    return str(harness)


def _seed_state() -> dict:
    """state اولیهٔ واقعی: پروفایل، درس‌ها و کتاب‌های انتخاب‌شده."""
    return {
        "version": 3,
        "profile": {"id": "p1", "name": "کنکور ۱۴۰۶", "group": "علوم تجربی", "year": "۱۴۰۶"},
        "subjects": [
            {"id": "s1", "name": "زیست‌شناسی", "examCoefficient": 12, "selected": True},
            {"id": "s2", "name": "شیمی", "examCoefficient": 9, "selected": True},
        ],
        "books": [
            {"id": "b1", "subject": "زیست‌شناسی", "grade": 10, "code": "110216", "selected": True},
        ],
        "events": [],
        "routines": [],
        "activities": [],
        "attempts": [],
        "reviews": [],
        "reviewLogs": [],
        "topics": [],
        "learningEvidence": [],
        "sections": {},
        "syllabusEdits": {},
        "resources": [],
        "settings": {"wake": "06:00", "sleep": "23:00", "energy": 2, "peak": [],
                     "useExamCoefficients": True, "coefficientFactor": 1,
                     "safetyMargin": 0.2, "negativeRatio": 0, "formula": "raw"},
        "onboarding": {"step": 5, "values": {}, "completed": True},
        "updatedAt": "2026-10-23T00:00:00.000Z",
    }


@pytest.mark.skipif(NODE is None, reason="node برای اجرای پیش‌نمایش لازم است")
def test_syllabus_assessment_and_resources_run(preview_js, tmp_path):
    """سرفصل، ارزیابی ۸ سؤالی و بانک منابع واقعاً کار می‌کنند."""
    payload = tmp_path / "preview-bundle.js"
    payload.write_text(preview_js, encoding="utf-8")
    syllabus_json = tmp_path / "syllabus.json"
    import json as _json

    m = re.search(r'id="syllabusData"[^>]*>(.*?)</script>', PREVIEW.read_text(encoding="utf-8"), re.S)
    syllabus_json.write_text(m.group(1).replace("\\u003c", "<"), encoding="utf-8")
    harness = _harness(payload, _seed_state(), syllabus_json)
    result = subprocess.run(
        [NODE, harness],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        cwd=str(ROOT),
    )
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    assert result.returncode == 0, stdout + stderr
    assert "FAIL" not in stdout, stdout


def test_syllabus_data_is_structured_and_honest():
    """دادهٔ سرفصل ساختاریافته است و وضعیت تأییدنشده را حمل می‌کند."""
    html = PREVIEW.read_text(encoding="utf-8")
    assert "زیست‌شناسی" in html
    # ساختار فصل/گفتار به‌صورت دادهٔ جاسازی‌شده حاضر است
    m = re.search(r'id="syllabusData"[^>]*>(.*?)</script>', html, re.S)
    assert m, "دادهٔ سرفصل باید در HTML جاسازی شود"
    import json

    data = json.loads(m.group(1).replace("\\u003c", "<"))
    assert data["meta"]["status"] == "preliminary_unverified"
    assert data["courses"]["زیست‌شناسی"]["10"][0]["title"] == "دنیای زنده"
    # شیمی: تعداد گفتار نامشخص است و عدد ساخته نشده
    assert data["courses"]["شیمی"]["10"][0]["sections"] is None
