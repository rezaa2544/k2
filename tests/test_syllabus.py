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

JS_FILES = ("core.js", "syllabus.js", "backlog.js", "examseries.js", "priority.js", "forms.js", "app.js")


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
      if(sel && sel.indexOf('[data-action]')===0) return !!this.dataset.action;
      if(sel && sel.indexOf('[data-activity-action]')===0) return !!this.dataset.activityAction;
      if(sel && sel.indexOf('[data-flow]')===0) return !!this.dataset.flow; return false },
    closest(sel){ let cur=this; while(cur){ if(cur.matches && cur.matches(sel)) return cur; cur=cur.parentNode } return null },
    querySelector(){return null}, querySelectorAll(){return []},
    getBoundingClientRect(){return {top:0,left:0,width:0,height:0}},
    // سریال‌سازی ساده تا خروجی HTML داده‌دار قابل آزمایش باشد
    get outerHTML(){
      const attrs = Object.entries(this.attrs||{}).map(([k,v])=>` ${k}="${String(v).replace(/"/g,'&quot;')}"`).join('');
      const inner = (this.children||[]).map(c=>c.outerHTML).join('') + (this.textContent||'');
      return `<${this.tagName}${attrs}>${inner}</${this.tagName}>`;
    },
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
// تگ وضعیت جاسازی‌شده باید داخل documentElement باشد تا خروجی HTML داده‌دار
// همان الگوی مرورگر واقعی را داشته باشد.
const _embedded = byId['#embeddedState'];
_embedded.tagName = 'script';
_embedded.attrs.id = 'embeddedState';
_embedded.attrs.type = 'application/json';
document.documentElement.children.push(_embedded);
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
const promptReply = { value: null };
global.__setPrompt = (v) => { promptReply.value = v };
// DOMParser کوچک: فقط تگ وضعیت جاسازی‌شده را برمی‌گرداند تا مسیر
// «بازیابی از HTML داده‌دار» قابل آزمایش باشد.
const DOMParser = class {
  parseFromString(text){
    const m = String(text).match(/<script id="embeddedState" type="application\/json">([\s\S]*?)<\/script>/);
    return { querySelector:(sel)=> (sel === '#embeddedState' && m) ? { textContent: m[1] } : null };
  }
};
const preview = new Function('document','localStorage','window','Intl','structuredClone','navigator',
  'confirm','prompt','setTimeout','clearTimeout','URL','Blob','console','FormData','DOMParser',
  factory_src + '\nreturn window.K2Preview;')(document, localStorage, window, Intl,
  o=>JSON.parse(JSON.stringify(o)), {userAgent:'node'}, ()=>true,
  (msg, def) => promptReply.value === null ? def : promptReply.value, ()=>0, ()=>{},
  {createObjectURL:()=>'', revokeObjectURL:()=>{}},
  class Blob { constructor(p){this.parts=p;(global.__blobs=global.__blobs||[]).push(this)} }, console,
  class FormData { constructor(){ this._m = global.__fd || new Map() }
    get(k){ const v = this._m.has(k) ? this._m.get(k) : null;
      return Array.isArray(v) ? (v[0] === undefined ? null : v[0]) : v }
    has(k){ const v=this.get(k); return v!==null && v!=='' && v!==undefined }
    getAll(k){ const v=this._m.has(k) ? this._m.get(k) : null;
      if (v===null || v===undefined) return [];
      return Array.isArray(v) ? v.slice() : [v] } }, DOMParser);
if (!preview) { console.log('FAIL: K2Preview missing'); process.exit(1) }
const clicks = (document._listeners && document._listeners.click) || [];
function clickNav(page){ const b = navItems.find(x=>x.dataset.page===page);
  if(!b) throw new Error('nav missing '+page);
  for (const fn of clicks) fn({target:b, preventDefault(){}, stopPropagation(){}}) }
function clickAction(action){ const b = makeEl('button'); b.dataset.action = action;
  for (const fn of clicks) fn({target:b, preventDefault(){}, stopPropagation(){}}) }
function pageHtml(){ return document.querySelector('#pageContent').innerHTML || '' }
function persistSilently(st){ preview.setState(st); }
function weekdayNow(){ return ((new Date().getDay()+1)%7) }
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
  // هشت سؤال؛ هر کدام با کلید خودش پاسخ داده می‌شود
  const steps = ['teaching','study','comprehension','consolidation','testing','analysis','essay','speed'];
  const picks = { teaching:'taught', study:'started', comprehension:'partial',
    consolidation:'initial', testing:'not_tested', analysis:'not_analyzed',
    essay:'not_done', speed:'slow' };
  ok(steps.length === 8, 'ارزیابی باید هشت سؤال داشته باشد، یافت: ' + steps.length);
  ok(steps[7] === 'speed', 'سؤال هشتم سرعت پاسخ‌دهی زمان‌دار است');
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
    ok(rec.speed === 'slow', 'پاسخ سؤال ۸ (سرعت) باید مستقل ذخیره شود، یافت: ' + rec.speed);
    ok(Object.keys(rec).filter(k => steps.includes(k)).length === 8,
       'هر هشت پاسخ ذخیره شوند، یافت: ' + Object.keys(rec).filter(k => steps.includes(k)).length);
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


# ---------------------------------------------------------------------------
# قواعد زمان‌بندی و کلاس‌های ثابت اولیه
# ---------------------------------------------------------------------------
#
# این آزمون‌ها روی ساختار برنامه قضاوت می‌کنند (getPlan) نه روی متن رندرشده؛
# چون متن شامل بلوک‌های غذا و تعهد هم می‌شود و مقایسهٔ آن‌ها با بلوک‌های
# مطالعه معنای درستی ندارد.

_PLAN_SCRIPT = r"""
const BASE_ACT = (id, title, subject, minutes) => ({ id, title, type: 'study',
  subjectName: subject, estimate: minutes, remaining: minutes, minChunk: 20,
  maxChunk: 90, splittable: true, state: 'open' });

// ---- الف) مطالعه پیش از ساعت ۹ صبح شروع نمی‌شود ----
try {
  const st0 = preview.getState();
  st0.settings.wake = '06:00';
  st0.settings.studyStart = '09:00';
  st0.activities = [BASE_ACT('a1', 'مطالعهٔ زیست', 'زیست‌شناسی', 120)];
  st0.events = [];
  persistSilently(st0);
  const plan = preview.getPlan();
  const before9 = plan.placements.filter(p => p.start < 9 * 60);
  ok(before9.length === 0, 'هیچ بلوکی پیش از ساعت ۹ صبح برنامه‌ریزی نشود، یافت: '
     + JSON.stringify(before9.map(p => p.start)));
  ok(plan.placements.length > 0, 'باید حداقل یک بلوک برنامه‌ریزی شود');
} catch (e) { failures++; console.log('FAIL 9am rule: ' + e.message) }

// ---- ب) بین بلوک‌های مطالعه یکسان حداقل ۱۵ دقیقه استراحت است ----
try {
  const st0 = preview.getState();
  st0.settings.breakMinutes = 15;
  st0.activities = [
    BASE_ACT('b1', 'کار یک', 'زیست‌شناسی', 90),
    BASE_ACT('b2', 'کار دو', 'شیمی', 90),
  ];
  st0.events = [];
  persistSilently(st0);
  const plan = preview.getPlan();
  const sorted = [...plan.placements].sort((a, b) => a.start - b.start);
  let bad = [];
  for (let i = 1; i < sorted.length; i++) {
    const gap = sorted[i].start - sorted[i-1].end;
    if (gap < 15) bad.push({ gap, after: sorted[i].title });
  }
  ok(bad.length === 0, 'بین بلوک‌های مطالعه حداقل ۱۵ دقیقه استراحت باشد، یافت: ' + JSON.stringify(bad));
  ok(sorted.length >= 2, 'باید دو بلوک برنامه‌ریزی شود');
} catch (e) { failures++; console.log('FAIL break rule: ' + e.message) }

// ---- ج) وعدهٔ غذا اشغال‌شده است و بلوک مطالعه روی آن نمی‌افتد ----
try {
  const st0 = preview.getState();
  st0.activities = [BASE_ACT('m1', 'مطالعهٔ شیمی', 'شیمی', 300)];
  st0.events = [];
  persistSilently(st0);
  const plan = preview.getPlan();
  const lunch = plan.blocks.find(b => b.title === 'ناهار');
  ok(!!lunch, 'بلوک ناهار باید در برنامه دیده شود');
  if (lunch) {
    const overlap = plan.placements.filter(p => p.start < lunch.end && p.end > lunch.start);
    ok(overlap.length === 0, 'هیچ بلوک مطالعه روی وعدهٔ غذا نیفتد، یافت: ' + overlap.length);
  }
} catch (e) { failures++; console.log('FAIL meal rule: ' + e.message) }

// ---- د) خواب کمتر از هدف، هشدار می‌دهد ----
try {
  const st0 = preview.getState();
  st0.settings.wake = '05:00';
  st0.settings.sleep = '23:30';   // ۵ ساعت و نیم — کمتر از هدف ۸ ساعت
  st0.settings.sleepTargetMinutes = 480;
  st0.activities = [BASE_ACT('s1', 'کار', 'شیمی', 60)];
  st0.events = [];
  persistSilently(st0);
  const plan = preview.getPlan();
  ok(plan.sleepWarning === true, 'خواب کمتر از هدف باید هشدار بدهد');
  ok(plan.sleepMinutes < 480, 'مدت خواب باید کمتر از هدف باشد، یافت: ' + plan.sleepMinutes);
} catch (e) { failures++; console.log('FAIL sleep warning: ' + e.message) }

// ---- ه) کلاس‌های ثابت اولیه با علامت «نیازمند تأیید» ----
try {
  clickAction('seed-classes');
  const st = preview.getState();
  const seeded = (st.events || []).filter(e => e.fromSeed);
  ok(seeded.length === 14, 'هر ۱۴ کلاس اولیه اضافه شود، یافت: ' + seeded.length);
  const unknown = seeded.filter(e => !e.start || !e.end);
  ok(unknown.length === 3, 'سه کلاس با ساعت نامشخص، یافت: ' + unknown.length);
  ok(unknown.every(e => e.needsConfirmation === true), 'کلاس نامشخص باید «نیازمند تأیید» باشد');
  ok(seeded.every(e => e.needsConfirmation === true), 'همهٔ کلاس‌های اولیه نیازمند تأییدند');
  ok(seeded.every(e => e.fromSeed === true), 'کلاس‌های اولیه باید قابل تشخیص باشند');
} catch (e) { failures++; console.log('FAIL seed classes: ' + e.message) }

// ---- و) کلاس ساعت‌نامشخص ظرفیت را اشغال نمی‌کند ----
try {
  const st0 = preview.getState();
  st0.events = [{ id: 'u1', title: 'دینی و زبان', kind: 'class', weekday: weekdayNow(),
    start: null, end: null, needsConfirmation: true, fromSeed: true }];
  st0.activities = [BASE_ACT('u2', 'مطالعهٔ ریاضی', 'ریاضی', 240)];
  persistSilently(st0);
  const plan = preview.getPlan();
  const busy = plan.blocks.find(b => b.title === 'دینی و زبان');
  ok(!busy, 'کلاس ساعت‌نامشخص نباید به‌عنوان بلوک اشغال‌شده دربیاید');
  ok(plan.placements.length > 0, 'برنامه باید فضای آزاد را پر کند');
} catch (e) { failures++; console.log('FAIL unknown-time class: ' + e.message) }

// ---- ز) کلاس زمان‌دار ظرفیت را اشغال می‌کند ----
try {
  const st0 = preview.getState();
  st0.events = [{ id: 'k1', title: 'زیست‌شناسی', kind: 'class', weekday: weekdayNow(),
    start: '09:00', end: '12:00', needsConfirmation: true, fromSeed: true }];
  st0.activities = [BASE_ACT('k2', 'مطالعهٔ زیست', 'زیست‌شناسی', 180)];
  persistSilently(st0);
  const plan = preview.getPlan();
  const cls = plan.blocks.find(b => b.title === 'زیست‌شناسی');
  ok(!!cls, 'کلاس زمان‌دار باید در بلوک‌های اشغال‌شده بیاید');
  const overlap = plan.placements.filter(p => p.start < 12 * 60 && p.end > 9 * 60);
  ok(overlap.length === 0, 'بلوک مطالعه نباید روی کلاس بیفتد، یافت: ' + overlap.length);
} catch (e) { failures++; console.log('FAIL occupied class: ' + e.message) }

// ---- ح) هیچ کاری بی‌صدا حذف نمی‌شود ----
try {
  const st0 = preview.getState();
  st0.events = [{ id: 'h1', title: 'کلاس سنگین', kind: 'class', weekday: weekdayNow(),
    start: '09:00', end: '23:00', recorded: false }];
  st0.activities = [BASE_ACT('h2', 'کار جا‌نشده', 'شیمی', 180)];
  persistSilently(st0);
  const plan = preview.getPlan();
  const st = preview.getState();
  ok(st.activities.length === 1, 'فعالیت از state حذف نشود');
  ok(plan.unplaced.length === 1, 'کار جا‌نشده باید گزارش شود، یافت: ' + plan.unplaced.length);
  ok(plan.unplaced[0].title === 'کار جا‌نشده', 'عنوان کار جا‌نشده درست باشد');
  ok(/کافی نماند/.test(plan.unplaced[0].reason), 'دلیل جا‌نشدن باید توضیح بدهد: ' + plan.unplaced[0].reason);
} catch (e) { failures++; console.log('FAIL no silent drop: ' + e.message) }

console.log(JSON.stringify({failures}));
process.exit(failures ? 1 : 0);
"""


@pytest.mark.skipif(NODE is None, reason="node برای اجرای پیش‌نمایش لازم است")
def test_scheduling_rules_and_fixed_classes(preview_js, tmp_path):
    """قواعد زمان‌بندی واقعاً رعایت می‌شوند و کاری بی‌صدا حذف نمی‌شود."""
    payload = tmp_path / "preview-bundle.js"
    payload.write_text(preview_js, encoding="utf-8")
    import json as _json

    m = re.search(r'id="syllabusData"[^>]*>(.*?)</script>', PREVIEW.read_text(encoding="utf-8"), re.S)
    syllabus_json = tmp_path / "syllabus.json"
    syllabus_json.write_text(m.group(1).replace("\\u003c", "<"), encoding="utf-8")
    seed = _seed_state()
    seed["settings"]["studyStart"] = "09:00"
    seed["settings"]["breakMinutes"] = 15
    harness = _harness(payload, seed, syllabus_json)
    body = Path(harness).read_text(encoding="utf-8")
    marker = "console.log(JSON.stringify({failures}));\nprocess.exit(failures ? 1 : 0);"
    assert marker in body, "plan harness marker"
    body = body.replace(marker, _PLAN_SCRIPT.strip() + "\n", 1)
    Path(harness).write_text(body, encoding="utf-8")
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


# ---------------------------------------------------------------------------
# عقب‌افتادگی‌ها: سند پایدار با انتخاب چندگانهٔ نوع
# ---------------------------------------------------------------------------

_BACKLOG_SCRIPT = r"""
const BASE_SETTINGS = { wake:'06:00', sleep:'23:00', studyStart:'09:00', breakMinutes:15,
  sleepTargetMinutes:480, safetyMargin:.2, useExamCoefficients:true, coefficientFactor:1 };
const mkAct = (id, title, subject, minutes, extra) => Object.assign({
  id, title, type:'study', subjectName:subject, estimate:minutes, remaining:minutes,
  minChunk:20, maxChunk:90, splittable:true, state:'open' }, extra || {});

// ---- الف) ثبت عقب‌افتادگی با انتخاب هم‌زمان چند نوع ----
try {
  const st0 = preview.getState();
  st0.settings = Object.assign({}, BASE_SETTINGS, st0.settings);
  st0.events = []; st0.activities = []; st0.backlogs = [];
  persistSilently(st0);
  clickNav('backlogs');
  clickAction('add-backlog');
  global.__fd = new Map([
    ['title','گفتار ۳ فصل ۲ زیست'], ['subject','زیست‌شناسی'],
    ['chapter','2'], ['section','3'], ['estimate','135'], ['remaining','135'],
    ['volume',''], ['volumeDone',''], ['importance','4'], ['due',''], ['notes',''],
  ]);
  global.__fd.set('types', ['study','concept','testing']);
  clickAction('save-backlog');
  const st = preview.getState();
  ok(st.backlogs.length === 1, 'یک عقب‌افتادگی ثبت شود، یافت: ' + st.backlogs.length);
  const b = st.backlogs[0];
  ok(b.types.length === 3, 'هر سه نوع هم‌زمان ثبت شوند، یافت: ' + JSON.stringify(b.types));
  ok(b.types.includes('study') && b.types.includes('concept') && b.types.includes('testing'),
     'انواع انتخابی درست باشند');
  ok(b.status === 'open', 'وضعیت اولیه «باز» باشد');
  ok(b.remaining === 135, 'باقی‌مانده از فرم ثبت شود');
} catch (e) { failures++; console.log('FAIL backlog create: ' + e.message) }

// ---- ب) مدت تخمینی خودکار از روی نوع‌ها ----
try {
  const st0 = preview.getState();
  st0.backlogs = []; st0.activities = []; st0.events = [];
  persistSilently(st0);
  clickAction('add-backlog');
  // مدت تخمینی خالی → باید از جمع نوع‌ها حساب شود (۴۰+۵۰+۴۵=۱۳۵)
  global.__fd = new Map([
    ['title','مطالعهٔ ناقص'], ['subject','شیمی'],
    ['chapter',''], ['section',''], ['estimate',''], ['remaining',''],
    ['volume',''], ['volumeDone',''], ['importance','3'], ['due',''], ['notes',''],
  ]);
  global.__fd.set('types', ['study','concept','testing']);
  clickAction('save-backlog');
  const st = preview.getState();
  ok(st.backlogs.length === 1, 'عقب‌افتادگی ثبت شود');
  ok(st.backlogs[0].estimate === 135, 'مدت تخمینی خودکار ۱۳۵ شود، یافت: ' + st.backlogs[0].estimate);
} catch (e) { failures++; console.log('FAIL backlog estimate: ' + e.message) }

// ---- ج) «مورد دیگر» بدون توضیح پذیرفته نمی‌شود ----
try {
  const st0 = preview.getState();
  st0.backlogs = []; st0.activities = []; st0.events = [];
  persistSilently(st0);
  clickAction('add-backlog');
  global.__fd = new Map([
    ['title','مورد نامشخص'], ['subject','شیمی'], ['chapter',''], ['section',''],
    ['estimate','30'], ['remaining','30'], ['volume',''], ['volumeDone',''],
    ['importance','3'], ['due',''], ['notes',''],
  ]);
  global.__fd.set('types', ['other']);
  clickAction('save-backlog');
  const st = preview.getState();
  ok(st.backlogs.length === 0, '«مورد دیگر» بدون توضیح ثبت نشود، یافت: ' + st.backlogs.length);
} catch (e) { failures++; console.log('FAIL backlog other-note: ' + e.message) }

// ---- د) «مورد دیگر» با توضیح پذیرفته می‌شود ----
try {
  const st0 = preview.getState();
  st0.backlogs = []; st0.activities = []; st0.events = [];
  persistSilently(st0);
  clickAction('add-backlog');
  global.__fd = new Map([
    ['title','مورد نامشخص'], ['subject','شیمی'], ['chapter',''], ['section',''],
    ['estimate','30'], ['remaining','30'], ['volume',''], ['volumeDone',''],
    ['importance','3'], ['due',''], ['notes','جزوهٔ کسر شده از دوستان'],
  ]);
  global.__fd.set('types', ['other']);
  clickAction('save-backlog');
  const st = preview.getState();
  ok(st.backlogs.length === 1, '«مورد دیگر» با توضیح ثبت شود');
  ok(st.backlogs[0].types.includes('other'), 'نوع other ثبت شود');
} catch (e) { failures++; console.log('FAIL backlog other-ok: ' + e.message) }

// ---- ه) قرار دادن در برنامه: فعالیت مشتق می‌سازد، عقب‌افتادگی می‌ماند ----
try {
  const st0 = preview.getState();
  st0.backlogs = [{ id:'bl1', title:'گفتار ۳ فصل ۲ زیست', types:['study','concept','testing'],
    subject:'زیست‌شناسی', subjectName:'زیست‌شناسی', grade:10, chapter:2, section:3,
    estimate:135, remaining:135, volume:null, volumeDone:null, importance:4, due:'',
    notes:'', status:'open', history:[], createdAt:new Date().toISOString(),
    updatedAt:new Date().toISOString() }];
  st0.activities = []; st0.events = [];
  persistSilently(st0);
  clickAction('backlog-schedule:bl1');
  const st = preview.getState();
  ok(st.backlogs.length === 1, 'عقب‌افتادگی پس از زمان‌بندی حذف نشود');
  ok(st.backlogs[0].status === 'scheduled', 'وضعیت به «در برنامهٔ امروز» تغییر کند');
  const act = (st.activities || []).find(a => a.backlogId === 'bl1');
  ok(!!act, 'فعالیت مشتق ساخته شود');
  if (act) {
    ok(act.state === 'open', 'فعالیت مشتق «برنامه‌ریزی‌شده» باشد نه انجام‌شده');
    ok(num(act.remaining) === 135, 'باقی‌ماندهٔ فعالیت از عقب‌افتادگی بیاید');
    ok(act.subjectName === 'زیست‌شناسی', 'درس منتقل شود');
  }
} catch (e) { failures++; console.log('FAIL backlog schedule: ' + e.message) }

// ---- و) ثبت پیشرفت ناقص از رویداد واقعی change، باقی‌مانده را کم می‌کند ----
try {
  const st0 = preview.getState();
  st0.backlogs = [{ id:'bl1', title:'گفتار ۳ فصل ۲ زیست', types:['study'],
    subject:'زیست‌شناسی', subjectName:'زیست‌شناسی', grade:10, chapter:2, section:3,
    estimate:135, remaining:135, volume:null, volumeDone:null, importance:4, due:'',
    notes:'', status:'scheduled', history:[], createdAt:new Date().toISOString(),
    updatedAt:new Date().toISOString() }];
  st0.activities = [mkAct('ac1', 'مطالعهٔ ناقص · گفتار ۳ فصل ۲ زیست', 'زیست‌شناسی', 135, { backlogId:'bl1' })];
  st0.events = [];
  persistSilently(st0);
  // کاربر ۶۰ دقیقه پیشرفت ثبت می‌کند (از دیالوگ واقعی)
  global.__setPrompt('60');
  const sel = makeEl('select');
  sel.dataset.activityAction = 'ac1';
  sel.value = 'partial';
  const changeHandlers = (document._listeners && document._listeners.change) || [];
  ok(changeHandlers.length > 0, 'شنوندهٔ change باید ثبت شده باشد');
  for (const fn of changeHandlers) fn({ target: sel, preventDefault(){}, stopPropagation(){} });
  const st = preview.getState();
  ok(st.backlogs.length === 1, 'عقب‌افتادگی پس از پیشرفت حذف نشود');
  ok(st.backlogs[0].remaining === 75, 'باقی‌مانده به ۷۵ کاهش یابد، یافت: ' + st.backlogs[0].remaining);
  ok(st.backlogs[0].status === 'partial', 'وضعیت «ناقص انجام شده» شود، یافت: ' + st.backlogs[0].status);
  ok(st.backlogs[0].history.length > 0, 'تاریخچهٔ پیشرفت ثبت شود');
  const act = (st.activities || []).find(a => a.id === 'ac1');
  ok(act && act.state === 'partial', 'فعالیت هم ناقص شود');
} catch (e) { failures++; console.log('FAIL backlog partial: ' + e.message) }

// ---- ز) انتقال به روز دیگر: عقب‌افتادگی می‌ماند، فعالیت بیرون می‌رود ----
try {
  const st0 = preview.getState();
  st0.backlogs = [{ id:'bl2', title:'تست‌نزدن', types:['testing'],
    subject:'شیمی', subjectName:'شیمی', grade:11, chapter:1, section:null,
    estimate:45, remaining:45, volume:null, volumeDone:null, importance:3, due:'',
    notes:'', status:'scheduled', history:[], createdAt:new Date().toISOString(),
    updatedAt:new Date().toISOString() }];
  st0.activities = [mkAct('ac2', 'تست‌نزدن', 'شیمی', 45, { backlogId:'bl2' })];
  st0.events = [];
  persistSilently(st0);
  const before = (preview.getState().backlogs || []).length;
  // کاربر دلیل انتقال را در دیالوگ وارد می‌کند
  global.__setPrompt('امروز وقت نشد');
  clickAction('backlog-defer:bl2');
  const st = preview.getState();
  ok(st.backlogs.length === before, 'عقب‌افتادگی پس از انتقال حذف نشود');
  ok(st.backlogs[0].status === 'deferred', 'وضعیت «به روز دیگر منتقل شد» شود');
  ok(st.backlogs[0].notes.indexOf('انتقال') !== -1, 'دلیل انتقال در یادداشت ثبت شود');
  ok(!(st.activities || []).some(a => a.backlogId === 'bl2'), 'فعالیت مشتق از برنامه بیرون رود');
} catch (e) { failures++; console.log('FAIL backlog defer: ' + e.message) }

// ---- ح) هشدار وقتی حجم کار از ظرفیت بیشتر است ----
try {
  const st0 = preview.getState();
  st0.backlogs = [
    { id:'bl3', title:'بزرگ', types:['study'], subject:'زیست‌شناسی', subjectName:'زیست‌شناسی',
      grade:10, chapter:1, section:1, estimate:1200, remaining:1200, volume:null, volumeDone:null,
      importance:5, due:'', notes:'', status:'open', history:[], createdAt:new Date().toISOString(),
      updatedAt:new Date().toISOString() }];
  st0.activities = []; st0.events = [];
  persistSilently(st0);
  clickNav('backlogs');
  const html = pageHtml();
  ok(html.includes('ظرفیت امروز'), 'ظرفیت در صفحه دیده شود');
  ok(html.includes('واقع‌بینانه') || html.includes('بیشتر است'),
     'وقتی حجم از ظرفیت بیشتر است هشدار واقع‌بینانه بدهد');
} catch (e) { failures++; console.log('FAIL backlog warning: ' + e.message) }

console.log(JSON.stringify({failures}));
process.exit(failures ? 1 : 0);
"""


@pytest.mark.skipif(NODE is None, reason="node برای اجرای پیش‌نمایش لازم است")
def test_backlog_management_is_durable_and_multi_type(preview_js, tmp_path):
    """عقب‌فتادگی سند پایدار است، چند نوع هم‌زمان می‌گیرد و بی‌صدا حذف نمی‌شود."""
    payload = tmp_path / "preview-bundle.js"
    payload.write_text(preview_js, encoding="utf-8")
    import json as _json

    m = re.search(r'id="syllabusData"[^>]*>(.*?)</script>', PREVIEW.read_text(encoding="utf-8"), re.S)
    syllabus_json = tmp_path / "syllabus.json"
    syllabus_json.write_text(m.group(1).replace("\\u003c", "<"), encoding="utf-8")
    seed = _seed_state()
    seed["backlogs"] = []
    harness = _harness(payload, seed, syllabus_json)
    body = Path(harness).read_text(encoding="utf-8")
    marker = "console.log(JSON.stringify({failures}));\nprocess.exit(failures ? 1 : 0);"
    assert marker in body, "backlog harness marker"
    body = body.replace(marker, _BACKLOG_SCRIPT.strip() + "\n", 1)
    Path(harness).write_text(body, encoding="utf-8")
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

_EXAMSERIES_SCRIPT = r"""
// ===== آزمون جامع دوره‌ای: تکرار ۱۴ روزه، آزمون و تحلیل مستقل =====
// تاریخ مرجع کاربر: ۱۴ آبان ۱۴۰۵. عددها در JS ساخته می‌شوند تا تست به ساعت
// واقعی sandbox وابسته نباشد.
const _TODAY = new Date().toISOString().slice(0, 10);

// ۱) تبدیل تقویم شمسی: ۱۴ آبان ۱۴۰۵ باید ۲۰۲۶-۱۱-۰۵ باشد
try {
  ok(preview.jalaliToIso(1405, 8, 14) === '2026-11-05',
     '۱۴ آبان ۱۴۰۵ به ۲۰۲۶-۱۱-۰۵ تبدیل شود، یافت: ' + preview.jalaliToIso(1405, 8, 14));
  ok(preview.jalaliLabel('2026-11-05') === '14 آبان 1405',
     'برچسب شمسی درست باشد، یافت: ' + preview.jalaliLabel('2026-11-05'));
  ok(preview.isoToJalali('2026-11-05').jm === 8, 'ماه آبان (۸) تشخیص داده شود');
  ok(preview.isoToJalali('2026-03-21').jm === 1, '۲۱ مارس اول فروردین باشد');
} catch (e) { failures++; console.log('FAIL jalali convert: ' + e.message) }

// ۲) وقوع‌ها با بازهٔ ۱۴ روزه از تاریخ شروع
try {
  const s = { enabled: true, startISO: '2026-11-05', intervalDays: 14,
              durationMinutes: 210, analysisMinutes: 60 };
  const occ = preview.examSeriesOccurrences(s, '2026-11-01', '2026-12-31');
  ok(occ[0] === '2026-11-05', 'نخستین نوبت ۱۴ آبان باشد، یافت: ' + occ[0]);
  ok(occ[1] === '2026-11-19', 'نوبت دوم ۱۴ روز بعد باشد، یافت: ' + occ[1]);
  ok(occ[2] === '2026-12-03', 'نوبت سوم ۲۸ روز بعد باشد، یافت: ' + occ[2]);
  ok(occ.every((v, i) => i === 0 || v > occ[i - 1]), 'وقوع‌ها صعودی و بی‌تکرار باشند');
  // بازهٔ مرزی: از نوبتی در میان چرخه شروع می‌شود، نه از تاریخ شروع
  const mid = preview.examSeriesOccurrences(s, '2026-11-20', '2026-12-31');
  ok(mid[0] === '2026-12-03', 'جست‌وجو از ۲۰ نوامبر به نوبت بعدی برسد، یافت: ' + mid[0]);
  ok(preview.examSeriesOccurrences({ ...s, enabled: false }, '2026-11-01', '2026-12-31').length === 0,
     'چرخهٔ غیرفعال نوبتی نسازد');
} catch (e) { failures++; console.log('FAIL occurrences: ' + e.message) }

// ۳) هر نوبت دو فعالیت مستقل می‌سازد: خود آزمون و تحلیل آن
try {
  const st0 = preview.getState();
  st0.examSeries = { enabled: true, startISO: _TODAY, intervalDays: 14,
                     durationMinutes: 210, analysisMinutes: 60, startNote: '' };
  st0.activities = [];
  persistSilently(st0);
  // بازهٔ افق همان چیزی است که ماژول استفاده می‌کند: امروز تا ۶۰ روز بعد
  const horizon = new Date(Date.now() + 60 * 86400000).toISOString().slice(0, 10);
  const expectedOcc = preview.examSeriesOccurrences(st0.examSeries, _TODAY, horizon).length;
  ok(expectedOcc >= 2, 'در بازهٔ ۶۰ روز چند نوبت باشد، یافت: ' + expectedOcc);
  const created = preview.syncExamSeries(_TODAY);
  const st = preview.getState();
  const acts = (st.activities || []).filter(a => a.origin === 'examSeries');
  ok(acts.length === 2 * expectedOcc,
     'هر نوبت دو فعالیت مستقل بسازد: ' + expectedOcc + ' نوبت، یافت: ' + acts.length);
  ok(created === 2 * expectedOcc, 'تعداد ساخته‌شده گزارش شود، یافت: ' + created);
  ok(new Set(acts.map(a => a.examRole)).size === 2, 'دوطرفهٔ نقش‌ها باشد');
  // نوبت امروز: هر دو فعالیت باید به همین تاریخ وصل باشند
  const examAct = acts.find(a => a.examRole === 'exam' && a.date === _TODAY);
  const anAct = acts.find(a => a.examRole === 'analysis' && a.date === _TODAY);
  ok(!!examAct && !!anAct, 'هر دو نقش آزمون و تحلیل ساخته شوند');
  // هر نوبت دقیقاً دو فعالیت دارد و نقش‌ها تکراری نیستند
  const perDate = {};
  for (const a of acts) perDate[a.date] = perDate[a.date] || new Set();
  for (const a of acts) perDate[a.date].add(a.examRole);
  ok(Object.keys(perDate).length === expectedOcc, 'هر تاریخ یک نوبت باشد');
  ok(Object.values(perDate).every(r => r.size === 2),
     'هر نوبت دقیقاً دو نقش مستقل داشته باشد');
  ok(examAct.type === 'exam', 'فعالیت آزمون نوع exam باشد، یافت: ' + examAct.type);
  ok(anAct.type === 'test_analysis', 'فعالیت تحلیل نوع test_analysis باشد، یافت: ' + anAct.type);
  ok(examAct.date === _TODAY && anAct.date === _TODAY, 'هر دو به تاریخ نوبت وصل باشند');
  ok(examAct.id !== anAct.id, 'شناسهٔ دو فعالیت متفاوت باشد');
  ok(num(examAct.remaining) === 210 && num(anAct.remaining) === 60,
     'مدت هر کدام جدا باشد: آزمون ۲۱۰، تحلیل ۶۰');
  // همگام‌سازی دوم نباید تکراری بسازد
  ok(preview.syncExamSeries(_TODAY) === 0, 'همگام‌سازی دوم فعالیت تکراری نسازد');
  ok(preview.getState().activities.filter(a => a.origin === 'examSeries').length === 2 * expectedOcc,
     'تعداد فعالیت‌ها پس از همگام‌سازی دوم ثابت بماند');
} catch (e) { failures++; console.log('FAIL sync pair: ' + e.message) }

// ۴) استقلال واقعی: پایان یکی، دیگری را تمام نمی‌کند
try {
  const st0 = preview.getState();
  const acts = (st0.activities || []).filter(a => a.origin === 'examSeries');
  const examAct = acts.find(a => a.examRole === 'exam');
  const anAct = acts.find(a => a.examRole === 'analysis');
  st0.activities = st0.activities.map(a => a.id === examAct.id
    ? { ...a, state: 'done', remaining: 0 } : a);
  persistSilently(st0);
  const st = preview.getState();
  const after = (st.activities || []).filter(a => a.origin === 'examSeries');
  ok(after.find(a => a.id === examAct.id).state === 'done', 'آزمون تمام‌شده ثبت بماند');
  ok(after.find(a => a.id === anAct.id).state !== 'done',
     'تحلیل با پایان آزمون تمام نشود؛ یافت: ' + after.find(a => a.id === anAct.id).state);
  ok(num(after.find(a => a.id === anAct.id).remaining) === 60, 'باقی‌ماندهٔ تحلیل دست‌نخورده بماند');
} catch (e) { failures++; console.log('FAIL independence: ' + e.message) }

// ۵) فعالیت آینده در برنامهٔ امروز نیاید؛ فعالیت امروز بیاید
try {
  const st0 = preview.getState();
  st0.examSeries = { enabled: true, startISO: _TODAY, intervalDays: 14,
                     durationMinutes: 210, analysisMinutes: 60, startNote: '' };
  st0.activities = [];
  persistSilently(st0);
  preview.syncExamSeries(_TODAY);
  const st = preview.getState();
  const future = (st.activities || []).filter(a => a.origin === 'examSeries' && a.date > _TODAY);
  ok(future.length >= 2, 'نوبت‌های آینده هم ساخته شوند، یافت: ' + future.length);
  const plan = preview.getPlan();
  const planTitles = (plan.placements || []).map(p => p.title);
  const todayTitles = (st.activities || [])
    .filter(a => a.origin === 'examSeries' && a.date <= _TODAY)
    .map(a => a.title);
  ok(planTitles.includes('آزمون جامع دوره‌ای · ' + preview.jalaliLabel(_TODAY)),
     'آزمون امروز در برنامه باشد؛ تیترها: ' + planTitles.join(' | '));
  ok(!planTitles.includes('آزمون جامع دوره‌ای · ' + preview.jalaliLabel(future[0].date)),
     'آزمون نوبت آینده در برنامهٔ امروز نیاید');
  const futurePlanned = future.filter(a => a.date > _TODAY && a.state === 'planned');
  ok(futurePlanned.length === future.length, 'نوبت‌های آینده در وضعیت برنامه‌ریزی‌شده بمانند');
} catch (e) { failures++; console.log('FAIL plan horizon: ' + e.message) }

// ۶) صفحهٔ آزمون‌های جامع چرخه را نشان می‌دهد و هشدار تاریخ رسمی را دارد
try {
  clickNav('comprehensive');
  const html = pageHtml();
  ok(html.includes('چرخهٔ آزمون جامع تکرارشونده'), 'کارت چرخه در صفحه دیده شود');
  ok(html.includes('مستقل'), 'استقلال آزمون و تحلیل در صفحه گفته شود');
  ok(html.includes('ابلاغ نشده'), 'هشدار «تاریخ رسمی ابلاغ نشده» بیاید');
  ok(html.includes(preview.jalaliLabel(_TODAY)) || html.includes('14'),
     'تاریخ نوبت با برچسب شمسی نمایش داده شود');
} catch (e) { failures++; console.log('FAIL series page: ' + e.message) }
"""


@pytest.mark.skipif(NODE is None, reason="node برای اجرای پیش‌نمایش لازم است")
def test_comprehensive_exam_series_recurs_and_splits_analysis(preview_js, tmp_path):
    """آزمون جامع هر ۱۴ روز از ۱۴ آبان ۱۴۰۵ تکرار شود و تحلیل مستقل باشد."""
    payload = tmp_path / "preview-bundle.js"
    payload.write_text(preview_js, encoding="utf-8")
    syllabus_json = tmp_path / "syllabus.json"
    import json as _json

    m = re.search(r'id="syllabusData"[^>]*>(.*?)</script>', PREVIEW.read_text(encoding="utf-8"), re.S)
    syllabus_json.write_text(m.group(1).replace("\\u003c", "<"), encoding="utf-8")
    seed = _seed_state()
    harness = _harness(payload, seed, syllabus_json)
    body = Path(harness).read_text(encoding="utf-8")
    marker = "console.log(JSON.stringify({failures}));\nprocess.exit(failures ? 1 : 0);"
    assert marker in body, "examseries harness marker"
    body = body.replace(marker, _EXAMSERIES_SCRIPT.strip() + "\n", 1)
    Path(harness).write_text(body, encoding="utf-8")
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

_PRIORITY_SCRIPT = r"""
// ===== منبع و اطمینان در اولویت‌بندی =====
// قاعدهٔ مرکزی: عدد وارد‌نشده «نامشخص» است، نه صفر. صفر یک ادعاست.

// ۱) مقدار نامشخص هرگز صفر نمایش داده نمی‌شود
try {
  const bare = { id: 't1', name: 'سلول', subjectName: 'زیست‌شناسی', stages: { konkur: 0, final: 0 } };
  const f = preview.topicFactor(bare, 'prerequisiteShare');
  ok(f.known === false, 'فاکتور وارد‌نشده نامشخص باشد');
  ok(f.value === null, 'مقدار نامشخص null بماند، نه ۰؛ یافت: ' + f.value);
  ok(f.source === 'unknown', 'منبع نامشخص «بدون منبع» باشد، یافت: ' + f.source);
  ok(f.confidence === 'none', 'اطمینان نامشخص «بدون اطمینان» باشد');
  ok(preview.factorValueText(f) === 'نامشخص', 'متن نمایشی «نامشخص» باشد، یافت: ' + preview.factorValueText(f));
  // صفرِ صریح با نامشخص یکی نیست
  const zero = preview.topicFactor({ ...bare, prerequisiteShare: 0 }, 'prerequisiteShare');
  ok(zero.known === true && zero.value === 0, 'صفرِ وارد‌شده با نامشخص تفاوت داشته باشد');
  ok(preview.factorValueText(zero) === '0.0', 'صفرِ صریح «۰٫۰» نمایش داده شود');
} catch (e) { failures++; console.log('FAIL unknown factor: ' + e.message) }

// ۲) منبع‌ها از هم قابل تشخیص‌اند
try {
  const base = { id: 't2', name: 'ژنتیک', subjectName: 'زیست‌شناسی', stages: { konkur: 0, final: 0 } };
  const mk = (source, confidence) => ({
    ...base,
    prerequisiteShare: 0.7,
    factorMeta: { prerequisiteShare: { source, confidence, overridden: false } }
  });
  const off = preview.topicFactor(mk('official', 'high'), 'prerequisiteShare');
  const his = preview.topicFactor(mk('historical', 'medium'), 'prerequisiteShare');
  const alg = preview.topicFactor(mk('algorithmic', 'medium'), 'prerequisiteShare');
  const per = preview.topicFactor(mk('personal', 'low'), 'prerequisiteShare');
  ok(off.source !== his.source && his.source !== alg.source && alg.source !== per.source,
     'چهار منبع رسمی/سوابق/محاسباتی/نظر شخصی متمایز باشند');
  ok(off.confidence === 'high' && his.confidence === 'medium' && per.confidence === 'low',
     'سطوح اطمینان جدا از منبع ثبت شوند');
  ok(preview.factorValueText(off) === '0.7', 'مقدار وارد‌شده نمایش داده شود');
  // بازنویسی علامت می‌خورد
  const ov = preview.topicFactor({ ...mk('official', 'high'), factorMeta: { prerequisiteShare: { source: 'official', confidence: 'high', overridden: true } } }, 'prerequisiteShare');
  ok(ov.overridden === true, 'بازنویسی کاربر ثبت شود');
} catch (e) { failures++; console.log('FAIL source distinguish: ' + e.message) }

// ۳) صفحهٔ بانک دروس منبع و اطمینان را نشان می‌دهد و صفرِ جعلی نمی‌سازد
try {
  const st0 = preview.getState();
  st0.topics = [
    { id: 't3', name: 'مبحث بدون فاکتور', subjectName: 'زیست‌شناسی', stages: { konkur: 0, final: 0 } },
    { id: 't4', name: 'مبحث با منبع رسمی', subjectName: 'زیست‌شناسی', stages: { konkur: 0, final: 0 },
      prerequisiteShare: 0.7, finalExamShare: 0.4,
      factorMeta: { prerequisiteShare: { source: 'official', confidence: 'high', overridden: false },
                    finalExamShare: { source: 'personal', confidence: 'low', overridden: false } } }
  ];
  persistSilently(st0);
  clickNav('courses');
  const html = pageHtml();
  ok(html.includes('منبع و اطمینان'), 'ستون منبع و اطمینان در جدول باشد');
  ok(html.includes('اطلاعیه رسمی'), 'برچسب منبع رسمی دیده شود');
  ok(html.includes('نظر یا برآورد خودت'), 'برچسب نظر شخصی دیده شود');
  ok(html.includes('اطمینان بالا'), 'سطح اطمینان دیده شود');
  ok(html.includes('نامشخص'), 'مقدار نامشخص صریحاً گفته شود');
  ok(html.includes('منبع هر عدد کجا می‌آید؟'), 'کارت توضیح منبع‌ها باشد');
  // مبحث بدون فاکتور نباید «۰٫۰» بگیرد
  const rowStart = html.indexOf('مبحث بدون فاکتور');
  const rowEnd = html.indexOf('</tr>', rowStart);
  const row = html.slice(rowStart, rowEnd);
  ok(row.includes('نامشخص'), 'سطر مبحث بدون فاکتور «نامشخص» داشته باشد');
  ok(!/0\.0/.test(row), 'سطر مبحث بدون فاکتور صفرِ جعلی نگیرد؛ سطر: ' + row.replace(/<[^>]*>/g, ' '));
} catch (e) { failures++; console.log('FAIL courses page: ' + e.message) }

// ۴) ذخیرهٔ فاکتورها: خالی = نامشخص، پر = با منبع و اطمینان
try {
  const st0 = preview.getState();
  st0.topics = [{ id: 't5', name: 'فتوسنتز', subjectName: 'زیست‌شناسی', stages: { konkur: 0, final: 0 } }];
  persistSilently(st0);
  const form = makeEl('form');
  form.id = 'modalForm';
  form.dataset.modalType = 'priorityFactors';
  global.__fd = new Map([
    ['topicId', 't5'],
    ['val_estimatedMinutes', ''],       // خالی = نامشخص
    ['src_estimatedMinutes', 'unknown'],
    ['conf_estimatedMinutes', 'none'],
    ['val_prerequisiteShare', '0.6'],
    ['src_prerequisiteShare', 'historical'],
    ['conf_prerequisiteShare', 'medium'],
    ['val_finalExamShare', ''],
    ['src_finalExamShare', 'unknown'],
    ['conf_finalExamShare', 'none']
  ]);
  preview.submitPriorityFactors(form);
  const st = preview.getState();
  const t = st.topics.find(x => x.id === 't5');
  ok(t.prerequisiteShare === 0.6, 'مقدار وارد‌شده ذخیره شود، یافت: ' + t.prerequisiteShare);
  ok(t.factorMeta.prerequisiteShare.source === 'historical', 'منبع ذخیره شود');
  ok(t.factorMeta.prerequisiteShare.confidence === 'medium', 'اطمینان ذخیره شود');
  ok(t.estimatedMinutes === null, 'مقدار خالی null شود نه صفر، یافت: ' + t.estimatedMinutes);
  ok(t.finalExamShare === null, 'سهم خالی null شود، یافت: ' + t.finalExamShare);
  ok(preview.topicFactor(t, 'estimatedMinutes').known === false, 'خالی همچنان نامشخص بماند');

  // بازنویسی: عوض کردن مقدار، پرچم بازنویسی را می‌سازد
  global.__fd = new Map([
    ['topicId', 't5'],
    ['val_estimatedMinutes', '90'],
    ['src_estimatedMinutes', 'personal'],
    ['conf_estimatedMinutes', 'medium'],
    ['val_prerequisiteShare', '0.3'],   // از ۰٫۶ به ۰٫۳ عوض شد
    ['src_prerequisiteShare', 'personal'],
    ['conf_prerequisiteShare', 'low'],
    ['val_finalExamShare', '0.5'],
    ['src_finalExamShare', 'algorithmic'],
    ['conf_finalExamShare', 'medium']
  ]);
  preview.submitPriorityFactors(form);
  const st2 = preview.getState();
  const t2 = st2.topics.find(x => x.id === 't5');
  ok(t2.estimatedMinutes === 90, 'مقدار تازه ذخیره شود');
  ok(t2.factorMeta.prerequisiteShare.overridden === true,
     'تغییر مقدار از ۰٫۶ به ۰٫۳ بازنویسی شمرده شود');
  ok(t2.factorMeta.finalExamShare.overridden === false,
     'پر کردن مقدار نامشخص بازنویسی نیست، یافت: ' + t2.factorMeta.finalExamShare.overridden);
} catch (e) { failures++; console.log('FAIL priority save: ' + e.message) }
"""


@pytest.mark.skipif(NODE is None, reason="node برای اجرای پیش‌نمایش لازم است")
def test_priority_factors_show_source_and_confidence(preview_js, tmp_path):
    """اولویت‌بندی منبع و اطمینان هر عدد را نشان می‌دهد و صفر جعلی نمی‌سازد."""
    payload = tmp_path / "preview-bundle.js"
    payload.write_text(preview_js, encoding="utf-8")
    syllabus_json = tmp_path / "syllabus.json"
    import json as _json

    m = re.search(r'id="syllabusData"[^>]*>(.*?)</script>', PREVIEW.read_text(encoding="utf-8"), re.S)
    syllabus_json.write_text(m.group(1).replace("\\u003c", "<"), encoding="utf-8")
    seed = _seed_state()
    harness = _harness(payload, seed, syllabus_json)
    body = Path(harness).read_text(encoding="utf-8")
    marker = "console.log(JSON.stringify({failures}));\nprocess.exit(failures ? 1 : 0);"
    assert marker in body, "priority harness marker"
    body = body.replace(marker, _PRIORITY_SCRIPT.strip() + "\n", 1)
    Path(harness).write_text(body, encoding="utf-8")
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

_SECTIONCOUNTS_SCRIPT = r"""
// ===== ورود تعداد گفتارهای درس نامشخص (مورد شیمی) =====
function g12Count() { return preview.syllabusChapters('شیمی', 12).length }
// چرا مهم است: شیمی ۱۰ فصل دارد و هیچ‌کدام عدد ندارند. اگر برنامه صفر
// بگذارد، کاربر فکر می‌کند ۱۰ گفتار بیشتر ندارد؛ اگر عددی حدس بزند، داده
// جعل شده است. راه حل: «نامشخص» صریح + ورود گروهی توسط کاربر.

try {
  // شیمی در سه پایه تقسیم است؛ پایهٔ دوازدهم ۴ فصل دارد و جمع کل ۱۰ فصل.
  const g12 = preview.syllabusChapters('شیمی', 12);
  ok(g12.length === 4, 'شیمی پایهٔ ۱۲ چهار فصل دارد، یافت: ' + g12.length);
  const counts = g12.map(c => preview.chapterSectionCount(c));
  ok(counts.every(c => c === null),
     'همهٔ فصل‌های شیمی نامشخص باشند (هیچ عدد جعلی)، یافت: ' + JSON.stringify(counts));
  const total = ['10', '11', '12']
    .reduce((n, g) => n + preview.syllabusChapters('شیمی', Number(g)).length, 0);
  ok(total === 10, 'جمع فصل‌های شیمی در سه پایه ۱۰ باشد، یافت: ' + total);
  // درسی که عدد دارد با شیمی فرق دارد
  const bio = preview.syllabusChapters('زیست‌شناسی', 10);
  ok(bio.length > 0 && bio.every(c => preview.chapterSectionCount(c) !== null),
     'زیست‌شناسی عدد دارد و با شیمی یکی نیست');
} catch (e) { failures++; console.log('FAIL chem unknown: ' + e.message) }

// ۱) نمای کلی برای درس نامشخص هشدار و دکمهٔ ورود می‌دهد
try {
  const st0 = preview.getState();
  st0.subjects = st0.subjects.map(s => ({ ...s, selected: true }));
  st0.syllabusEdits = {};
  persistSilently(st0);
  clickNav('topics');
  let html = pageHtml();
  if (!html.includes('تعداد گفتار نامشخص')) {
    // در صورت باز بودن نمای درخت، به فهرست برمی‌گردیم
    clickAction('syllabus-close');
    html = pageHtml();
  }
  ok(html.includes('تعداد گفتار نامشخص'), 'درس نامشخص با برچسب صریح دیده شود');
  ok(html.includes('ورود تعداد گفتارها'), 'دکمهٔ ورود تعداد گفتارها موجود باشد');
  ok(html.includes('هیچ عددی حدس نمی‌زند'), 'متن صداقت دربارهٔ حدس زدن عدد بیاید');
  ok(html.includes('شیمی'), 'درس شیمی در فهرست باشد');
} catch (e) { failures++; console.log('FAIL overview prompt: ' + e.message) }

// ۲) ورود گروهی: عددها ذخیره می‌شوند و خالی «نامشخص» می‌ماند
try {
  const st0 = preview.getState();
  st0.syllabusEdits = {};
  persistSilently(st0);
  // فرم گروهی باز می‌شود
  preview.sylCountsForm('شیمی', 12);
  const form = makeEl('form');
  form.id = 'modalForm';
  // کاربر ۶ فصل را وارد می‌کند و ۴ فصل را خالی می‌گذارد
  const N = g12Count();
  const fd = new Map();
  for (let i = 1; i <= N; i += 1) fd.set('sec_' + i, i <= 2 ? String(i * 3) : '');
  global.__fd = fd;
  preview.submitSylCounts(form);
  const st = preview.getState();
  const edits = st.syllabusEdits || {};
  const saved = [];
  for (let i = 1; i <= N; i += 1) saved.push(edits[`شیمی|12|${i}`]?.sections ?? null);
  ok(saved.slice(0, 2).every(v => v !== null), 'فصل‌های وارد‌شده عدد بگیرند، یافت: ' + JSON.stringify(saved));
  ok(saved[0] === 3 && saved[1] === 6, 'اعداد وارد‌شده درست ذخیره شوند، یافت: ' + JSON.stringify(saved));
  ok(saved.slice(2).every(v => v === null),
     'فصل‌های خالی null بمانند نه صفر، یافت: ' + JSON.stringify(saved.slice(2)));
  const after = preview.syllabusChapters('شیمی', 12).map(c => preview.chapterSectionCount(c));
  ok(after[0] === 3 && after[2] === null, 'خواندن پس از ذخیره درست باشد، یافت: ' + JSON.stringify(after));
  // ارزیابی گفتار برای فصل وارد‌شده ممکن است
  const secs = after.filter(c => c !== null).reduce((n, c) => n + c, 0);
  ok(secs > 0, 'گفتارهای فصل‌های وارد‌شده ساخته شوند: ' + secs);
} catch (e) { failures++; console.log('FAIL counts save: ' + e.message) }

// ۳) تغییر بعدی: مقدار قبلی عوض می‌شود و پاک‌کردن ممکن است
try {
  preview.sylCountsForm('شیمی', 12);
  const form = makeEl('form');
  form.id = 'modalForm';
  const N2 = g12Count();
  const fd = new Map();
  for (let i = 1; i <= N2; i += 1) fd.set('sec_' + i, i === 1 ? '5' : (i <= 2 ? String(i * 3) : ''));
  global.__fd = fd;
  preview.submitSylCounts(form);
  const st = preview.getState();
  ok((st.syllabusEdits['شیمی|12|1'] || {}).sections === 5,
     'تعداد فصل ۱ از ۲ به ۵ عوض شود، یافت: ' + (st.syllabusEdits['شیمی|12|1'] || {}).sections);
  // اکنون همه را خالی می‌کنیم: بازگشت به نامشخص، نه صفر
  const fd2 = new Map();
  for (let i = 1; i <= N2; i += 1) fd2.set('sec_' + i, '');
  global.__fd = fd2;
  preview.submitSylCounts(form);
  const st2 = preview.getState();
  const cleared = [];
  for (let i = 1; i <= N2; i += 1) cleared.push((st2.syllabusEdits[`شیمی|12|${i}`] || {}).sections ?? 'absent');
  ok(cleared.every(v => v === null || v === 'absent'),
     'خالی کردن همه، نامشخص شود نه صفر، یافت: ' + JSON.stringify(cleared));
} catch (e) { failures++; console.log('FAIL counts edit: ' + e.message) }
"""


@pytest.mark.skipif(NODE is None, reason="node برای اجرای پیش‌نمایش لازم است")
def test_unknown_section_counts_are_entered_not_invented(preview_js, tmp_path):
    """درس با تعداد گفتار نامشخص (شیمی) عدد جعلی نمی‌سازد و کاربر وارد می‌کند."""
    payload = tmp_path / "preview-bundle.js"
    payload.write_text(preview_js, encoding="utf-8")
    syllabus_json = tmp_path / "syllabus.json"
    import json as _json

    m = re.search(r'id="syllabusData"[^>]*>(.*?)</script>', PREVIEW.read_text(encoding="utf-8"), re.S)
    syllabus_json.write_text(m.group(1).replace("\\u003c", "<"), encoding="utf-8")
    seed = _seed_state()
    harness = _harness(payload, seed, syllabus_json)
    body = Path(harness).read_text(encoding="utf-8")
    marker = "console.log(JSON.stringify({failures}));\nprocess.exit(failures ? 1 : 0);"
    assert marker in body, "sectioncounts harness marker"
    body = body.replace(marker, _SECTIONCOUNTS_SCRIPT.strip() + "\n", 1)
    Path(harness).write_text(body, encoding="utf-8")
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

_REPORTS_SCRIPT = r"""
// ===== گزارش روزانه و هفتگی با دلیل تغییرها =====
// چیزی که باید تضمین شود: گزارش از دادهٔ واقعی ساخته شود، تفاوت برآورد و
// واقعی دیده شود، و دلیل هر تغییر وضعیت از دست نرود.
const _TODAY2 = new Date().toISOString().slice(0, 10);
const _DAYS_AGO = (n) => { const d = new Date(); d.setUTCDate(d.getUTCDate() - n); return d.toISOString().slice(0, 10) };

try {
  const st0 = preview.getState();
  const mkAct = (title, stateName, actual, estimate, updatedAt, reason) => ({
    id: 'a_' + title, title, type: 'independent_practice', subjectId: 's1', subjectName: 'زیست‌شناسی',
    estimate, remaining: 0, actual, state: stateName, minChunk: 20, maxChunk: 90, splittable: true,
    deadline: 'none', personalWeight: 1, updatedAt: updatedAt + 'T10:00:00.000Z', reason: reason || ''
  });
  st0.activities = [
    // امروز: دو تا تمام‌شده (یکی با دلیل)، یکی ناقص، یکی تعویق‌شده با دلیل
    mkAct('تمرین امروز الف', 'done', 70, 45, _TODAY2, 'سؤال سخت‌تر بود'),
    mkAct('تمرین امروز ب', 'done', 40, 40, _TODAY2, ''),
    mkAct('تمرین امروز ج', 'partial', 25, 60, _TODAY2, 'وقت نشد'),
    mkAct('تمرین امروز د', 'deferred', 0, 30, _TODAY2, 'کلاس اضافه شد'),
    // سه روز پیش
    mkAct('تمرین سه روز پیش', 'done', 90, 60, _DAYS_AGO(3), ''),
    // هفت روز پیش (بیرون از بازه)
    mkAct('تمرین هفت روز پیش', 'done', 30, 30, _DAYS_AGO(9), ''),
    // باز
    mkAct('تمرین باز', 'planned', 0, 50, _TODAY2, ''),
    // گذشته و هنوز باز
    { ...mkAct('تمرین گذشتهٔ باز', 'planned', 0, 40, _TODAY2, ''), date: _DAYS_AGO(2) }
  ];
  persistSilently(st0);
  clickNav('reports');
  const html = pageHtml();
  ok(html.includes('گزارش امروز'), 'بخش گزارش امروز باشد');
  ok(html.includes('گزارش هفت روز گذشته'), 'بخش گزارش هفتگی باشد');
  ok(html.includes('دلیل تغییرهای امروز'), 'جدول دلیل تغییرهای امروز باشد');
  ok(html.includes('دلیل تغییرهای هفته'), 'جدول دلیل تغییرهای هفته باشد');
  ok(html.includes('سؤال سخت‌تر بود'), 'دلیل ثبت‌شدهٔ امروز دیده شود');
  ok(html.includes('کلاس اضافه شد'), 'دلیل تعویق دیده شود');
  // هفت ردیف روزانه
  const dayRowCount = (html.match(/<tr><td>(امروز|[^<]*)<\/td><td>\d{4}-\d{2}-\d{2}<\/td>/g) || []).length;
  ok(dayRowCount === 7, 'هفت ردیف روزانه در گزارش هفتگی باشد، یافت: ' + dayRowCount);
  // برآورد و واقعی هفته: (45+40+60+90) برآورد، (70+40+90) واقعی
  ok(html.includes('اختلاف برآورد و واقعی'), 'شاخص اختلاف برآورد و واقعی باشد');
  ok(html.includes('فعالیت‌های باز'), 'فعالیت‌های باز گزارش شوند');
  ok(html.includes('هنوز باز است'), 'فعالیت گذشتهٔ باز هشدار بگیرد');
} catch (e) { failures++; console.log('FAIL reports: ' + e.message) }

// فعالیت بدون دلیل، برنامه را به ثبت دلیل reminder می‌کند
try {
  const st0 = preview.getState();
  st0.activities = [{
    id: 'a_noreason', title: 'تمرین بدون دلیل', type: 'independent_practice', subjectId: 's1',
    subjectName: 'زیست‌شناسی', estimate: 45, remaining: 0, actual: 45, state: 'done',
    minChunk: 20, maxChunk: 90, splittable: true, deadline: 'none', personalWeight: 1,
    updatedAt: _TODAY2 + 'T10:00:00.000Z', reason: ''
  }];
  persistSilently(st0);
  clickNav('reports');
  const html = pageHtml();
  ok(html.includes('دلیل خالی است'), 'وقتی دلیل ثبت نشده یادآوری شود');
} catch (e) { failures++; console.log('FAIL reports nudge: ' + e.message) }
"""


@pytest.mark.skipif(NODE is None, reason="node برای اجرای پیش‌نمایش لازم است")
def test_reports_show_daily_weekly_and_change_reasons(preview_js, tmp_path):
    """گزارش روزانه و هفتگی ساخته می‌شود و دلیل تغییرها را از دست نمی‌دهد."""
    payload = tmp_path / "preview-bundle.js"
    payload.write_text(preview_js, encoding="utf-8")
    syllabus_json = tmp_path / "syllabus.json"
    import json as _json

    m = re.search(r'id="syllabusData"[^>]*>(.*?)</script>', PREVIEW.read_text(encoding="utf-8"), re.S)
    syllabus_json.write_text(m.group(1).replace("\\u003c", "<"), encoding="utf-8")
    seed = _seed_state()
    harness = _harness(payload, seed, syllabus_json)
    body = Path(harness).read_text(encoding="utf-8")
    marker = "console.log(JSON.stringify({failures}));\nprocess.exit(failures ? 1 : 0);"
    assert marker in body, "reports harness marker"
    body = body.replace(marker, _REPORTS_SCRIPT.strip() + "\n", 1)
    Path(harness).write_text(body, encoding="utf-8")
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

_STORAGE_SCRIPT = r"""
// ===== توضیح محدودیت ذخیره‌سازی و نبود همگام‌سازی بین دستگاه‌ها =====

// ۱) دیالوگ حریم خصوصی باید مرزها را صریح بگوید
try {
  clickAction('privacy');
  const html = byId['#modalBody'].innerHTML || '';
  ok(html.includes('داده کجا ذخیره می‌شود؟'), 'بخش محل ذخیره‌سازی باشد');
  ok(html.includes('۵ مگابایت'), 'سقف تقریبی ذخیره‌سازی گفته شود');
  ok(html.includes('ذخیره') && html.includes('نمی‌شود'), 'پیامد پر شدن سقف گفته شود');
  ok(html.includes('همگام نمی‌شود'), 'نبود همگام‌سازی بین دستگاه‌ها صریح باشد');
  ok(html.includes('پشتیبان JSON'), 'راه انتقال با پشتیبان JSON گفته شود');
  ok(html.includes('HTML داده‌دار'), 'راه انتقال با HTML داده‌دار گفته شود');
  ok(html.includes('نمی‌خوانَد'), 'محدودیت پیوست (برنامه فایل را نمی‌خواند) گفته شود');
} catch (e) { failures++; console.log('FAIL privacy dialog: ' + e.message) }

// ۲) پر شدن سقف: پیام صریح می‌دهد، نه خطای خاموش
try {
  const st0 = preview.getState();
  st0.events = [];
  persistSilently(st0);
  const realSet = localStorage.setItem;
  localStorage.setItem = (k, v) => {
    const err = new Error('Quota exceeded');
    err.name = 'QuotaExceededError';
    err.code = 22;
    throw err;
  };
  let threw = false;
  try { clickAction('seed-classes'); } catch (e) { threw = true; }
  localStorage.setItem = realSet;
  ok(!threw, 'پر شدن سقف باعث خطای مدیریت‌نشده نشود');
  const state = byId['#storageState'].textContent || '';
  ok(state.includes('حافظهٔ مرورگر پر شد'),
     'وضعیت ذخیره‌سازی سقف پر شده را بگوید، یافت: ' + state);
  const toast = byId['#toast'].textContent || '';
  ok(toast.includes('پشتیبان JSON'), 'پیام سقف پر، راه نجات را بگوید، یافت: ' + toast);
  // پس از آزاد شدن سقف، ذخیره‌سازی دوباره کار کند
  clickAction('seed-classes');
  const after = byId['#storageState'].textContent || '';
  ok(after.includes('ذخیرهٔ خودکار فعال'), 'پس از رفع اشکال، ذخیره‌سازی برگردد، یافت: ' + after);
  ok((preview.getState().events || []).length > 0, 'دادهٔ ساخته‌شده حفظ شود');
} catch (e) { failures++; console.log('FAIL quota: ' + e.message) }
"""


@pytest.mark.skipif(NODE is None, reason="node برای اجرای پیش‌نمایش لازم است")
def test_storage_limits_and_no_sync_are_explained(preview_js, tmp_path):
    """محدودیت ذخیره‌سازی و نبود همگام‌سازی بین دستگاه‌ها توضیح داده می‌شود."""
    payload = tmp_path / "preview-bundle.js"
    payload.write_text(preview_js, encoding="utf-8")
    syllabus_json = tmp_path / "syllabus.json"
    import json as _json

    m = re.search(r'id="syllabusData"[^>]*>(.*?)</script>', PREVIEW.read_text(encoding="utf-8"), re.S)
    syllabus_json.write_text(m.group(1).replace("\\u003c", "<"), encoding="utf-8")
    seed = _seed_state()
    harness = _harness(payload, seed, syllabus_json)
    body = Path(harness).read_text(encoding="utf-8")
    marker = "console.log(JSON.stringify({failures}));\nprocess.exit(failures ? 1 : 0);"
    assert marker in body, "storage harness marker"
    body = body.replace(marker, _STORAGE_SCRIPT.strip() + "\n", 1)
    Path(harness).write_text(body, encoding="utf-8")
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

_REVIEW_SCRIPT = r"""
// ===== ردیابی مرور و فراموشی =====
// قانون: فاصله با عملکرد تغییر کند، فراموشی شمرده شود، و مرور یک پیشنهاد
// بماند نه قانون جعلی.

const mkReview = (id, label, interval, due, lapses) => ({
  id, label, subjectId: 's1', subjectName: 'زیست‌شناسی', type: 'مفهومی',
  interval, lapses: lapses || 0, due, status: interval > 1 ? 'مرور' : 'یادگیری مجدد',
  difficulty: 3, content: '', createdAt: new Date().toISOString()
});

// ۱) مرور درست: فاصله بلندتر، موعد دورتر، فراموشی زیاد نمی‌شود
try {
  const st0 = preview.getState();
  const today = new Date().toISOString().slice(0, 10);
  st0.reviews = [mkReview('r1', 'سلول و ساختارش', 2, today, 1)];
  st0.reviewLogs = [];
  persistSilently(st0);
  clickNav('review');
  let html = pageHtml();
  ok(html.includes('سلول و ساختارش'), 'مورد سررسیدشده در صفحه دیده شود');
  ok(html.includes('2.0 روز'), 'فاصلهٔ فعلی نمایش داده شود، یافت: ' + (html.match(/[\d.]+ روز/) || ['—'])[0]);
  clickAction('grade-review:r1');
  const st = preview.getState();
  const r = st.reviews.find(x => x.id === 'r1');
  ok(num(r.interval) > 2, 'فاصله پس از پاسخ درست بلندتر شود، یافت: ' + r.interval);
  ok(r.lapses === 1, 'فراموشی با پاسخ درست زیاد نشود، یافت: ' + r.lapses);
  ok(r.due > today, 'موعد بعدی جلو برود، یافت: ' + r.due);
  ok((st.reviewLogs || []).length === 1, 'نتیجهٔ مرور ثبت شود');
  ok(st.reviewLogs[0].grade === 4, 'نمرهٔ درست ثبت شود');
  // پس از درست، دیگر در فهرست سررسیدشده نیست
  clickNav('review');
  html = pageHtml();
  ok(!html.includes('سلول و ساختارش') || html.includes('موردی برای مرور سررسید نشده'),
     'مورد مرور‌شده از فهرست سررسید خارج شود');
} catch (e) { failures++; console.log('FAIL review grade ok: ' + e.message) }

// ۲) مرور غلط: فاصله به کمینه برگردد، فراموشی شمرده شود، وضعیت عوض شود
try {
  const st0 = preview.getState();
  const today = new Date().toISOString().slice(0, 10);
  st0.reviews = [mkReview('r2', 'چرخهٔ خون', 7, today, 0)];
  st0.reviewLogs = [];
  persistSilently(st0);
  clickAction('miss-review:r2');
  const st = preview.getState();
  const r = st.reviews.find(x => x.id === 'r2');
  ok(num(r.interval) === 1, 'فاصله پس از فراموشی به کمینه برگردد، یافت: ' + r.interval);
  ok(r.lapses === 1, 'فراموشی شمرده شود، یافت: ' + r.lapses);
  ok(r.status === 'یادگیری مجدد', 'وضعیت به یادگیری مجدد تغییر کند، یافت: ' + r.status);
  ok((st.reviewLogs || []).length === 1 && st.reviewLogs[0].grade === 1, 'نمرهٔ غلط ثبت شود');
} catch (e) { failures++; console.log('FAIL review grade miss: ' + e.message) }

// ۳) صفحه صداقت خود را حفظ کند: مرور پیشنهاد است نه قانون
try {
  clickNav('review');
  const html = pageHtml();
  ok(html.includes('یک پیشنهاد است، نه قانون علمی ثابت'),
     'صفحه بگوید برنامهٔ مرور پیشنهاد است نه قانون');
} catch (e) { failures++; console.log('FAIL review honesty: ' + e.message) }
"""


@pytest.mark.skipif(NODE is None, reason="node برای اجرای پیش‌نمایش لازم است")
def test_review_scheduling_tracks_forgetting(preview_js, tmp_path):
    """مرور فاصله‌دار با عملکرد به‌روز می‌شود و فراموشی را می‌شمارد."""
    payload = tmp_path / "preview-bundle.js"
    payload.write_text(preview_js, encoding="utf-8")
    syllabus_json = tmp_path / "syllabus.json"
    import json as _json

    m = re.search(r'id="syllabusData"[^>]*>(.*?)</script>', PREVIEW.read_text(encoding="utf-8"), re.S)
    syllabus_json.write_text(m.group(1).replace("\\u003c", "<"), encoding="utf-8")
    seed = _seed_state()
    harness = _harness(payload, seed, syllabus_json)
    body = Path(harness).read_text(encoding="utf-8")
    marker = "console.log(JSON.stringify({failures}));\nprocess.exit(failures ? 1 : 0);"
    assert marker in body, "review harness marker"
    body = body.replace(marker, _REVIEW_SCRIPT.strip() + "\n", 1)
    Path(harness).write_text(body, encoding="utf-8")
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

_EXAMDRAFT_SCRIPT = r"""
// ===== آزمون با ساعت، پیش‌نویس دادهٔ ناقص، و تشخیص تعارض =====
const wdOf = (iso) => ((new Date(iso + 'T00:00:00Z').getUTCDay() + 1) % 7);  // ۰ = شنبه
// نزدیک‌ترین تاریخ با روز هفتهٔ مورد نظر
const nextWithWeekday = (wd) => {
  for (let i = 0; i < 14; i += 1) {
    const d = new Date(); d.setUTCDate(d.getUTCDate() + i);
    const iso = d.toISOString().slice(0, 10);
    if (wdOf(iso) === wd) return iso;
  }
  return new Date().toISOString().slice(0, 10);
};
const submitExam = (fd) => {
  const form = makeEl('form');
  form.id = 'modalForm';
  form.dataset.modalType = 'exam';
  global.__fd = new Map(Object.entries(fd));
  preview.submitModal(form);
};

// ۱) آزمون با ساعت هم‌پوشان با کلاس ثابت → تعارض
try {
  const wd = 0;  // شنبه
  const date = nextWithWeekday(wd);
  const st0 = preview.getState();
  st0.events = [{ id: 'e1', title: 'کلاس زیست‌شناسی', kind: 'class', weekday: wd,
    start: '15:00', end: '19:00', recorded: false, needsConfirmation: false }];
  st0.attempts = [];
  st0.activities = [];
  persistSilently(st0);
  submitExam({ name: 'تست مبحثی', kind: 'teaching', date: date, time: '16:30',
    total: '40', correct: '20', wrong: '10', blank: '10', duration: '60',
    error: '', note: '', subject: '' });
  const c = preview.examConflicts();
  ok(c.length === 1, 'تعارض آزمون با کلاس شناسایی شود، یافت: ' + c.length);
  ok(c[0].exam === 'تست مبحثی' && c[0].other === 'کلاس زیست‌شناسی',
     'طرفین تعارض درست نام‌برده شوند، یافت: ' + JSON.stringify(c[0] || {}));
  // صفحهٔ تست هشدار تعارض را نشان می‌دهد
  clickNav('tests');
  ok(pageHtml().includes('تعارض زمان‌بندی'), 'هشدار تعارض در صفحه دیده شود');
} catch (e) { failures++; console.log('FAIL exam conflict: ' + e.message) }

// ۲) آزمون بیرون از ساعت کلاس → تعارض نیست
try {
  const wd = 0;
  const date = nextWithWeekday(wd);
  const st0 = preview.getState();
  st0.events = [{ id: 'e1', title: 'کلاس زیست‌شناسی', kind: 'class', weekday: wd,
    start: '15:00', end: '19:00', recorded: false, needsConfirmation: false }];
  st0.attempts = [];
  persistSilently(st0);
  submitExam({ name: 'تست بدون تعارض', kind: 'teaching', date: date, time: '09:00',
    total: '40', correct: '20', wrong: '10', blank: '10', duration: '60',
    error: '', note: '', subject: '' });
  ok(preview.examConflicts().length === 0, 'آزمون بیرون از کلاس تعارض نسازد');
} catch (e) { failures++; console.log('FAIL exam no conflict: ' + e.message) }

// ۳) آزمون بی‌ساعت بررسی نمی‌شود (ادعای تعارض روی دادهٔ ناقص درست نیست)
try {
  const wd = 0;
  const date = nextWithWeekday(wd);
  const st0 = preview.getState();
  st0.events = [{ id: 'e1', title: 'کلاس زیست‌شناسی', kind: 'class', weekday: wd,
    start: '00:00', end: '23:59', recorded: false, needsConfirmation: false }];
  st0.attempts = [];
  persistSilently(st0);
  submitExam({ name: 'آزمون بی‌ساعت', kind: 'teaching', date: date, time: '',
    total: '40', correct: '20', wrong: '10', blank: '10', duration: '60',
    error: '', note: '', subject: '' });
  ok(preview.examConflicts().length === 0, 'آزمون بی‌ساعت تعارض نسازد');
} catch (e) { failures++; console.log('FAIL exam no time: ' + e.message) }

// ۴) دادهٔ ناقص → پیش‌نویس، نه رد شدن و نه درصد جعلی
try {
  const date = new Date().toISOString().slice(0, 10);
  const st0 = preview.getState();
  st0.attempts = [];
  persistSilently(st0);
  // «کل» خالی: کاربر هنوز نمی‌داند چند سؤال بوده
  submitExam({ name: 'تست نیمه‌کاره', kind: 'teaching', date: date, time: '10:00',
    total: '', correct: '', wrong: '', blank: '', duration: '90',
    error: '', note: '', subject: '' });
  let st = preview.getState();
  let a = (st.attempts || [])[0];
  ok(!!a, 'آزمون با دادهٔ ناقص ذخیره شود');
  ok(a.draft === true, 'وضعیت پیش‌نویس بگیرد، یافت: ' + a.draft);
  ok(a.total === null, '«کل» نامشخص null بماند، یافت: ' + a.total);
  ok(a.percentage === null, 'درصد محاسبه نشود (عدد جعلی ساخته نشود)، یافت: ' + a.percentage);
  // صفحه‌ها با درصد null نمی‌شکنند
  clickNav('tests');
  let html = pageHtml();
  ok(html.includes('پیش‌نویس'), 'برچسب پیش‌نویس در صفحه تست دیده شود');
  ok(html.includes('کامل کردن'), 'راه کامل کردن پیش‌نویس داده شود');
  ok(html.includes('نامشخص'), 'تعداد کل نامشخص باشد');
  clickNav('comprehensive');
  html = pageHtml();
  ok(html.includes('چرخهٔ آزمون جامع تکرارشونده'),
     'صفحهٔ جامع با وجود پیش‌نویس در داده بدون خطا رندر شود');
  // یک پیش‌نویس جامع هم در صفحهٔ جامع دیده می‌شود
  submitExam({ name: 'آزمون جامع ناقص', kind: 'mock', date: date, time: '',
    total: '', correct: '', wrong: '', blank: '', duration: '180',
    error: '', note: '', subject: '' });
  st = preview.getState();
  ok((st.attempts || []).some(x => x.name === 'آزمون جامع ناقص' && x.draft === true),
     'پیش‌نویس جامع ذخیره شود');
  clickNav('comprehensive');
  html = pageHtml();
  ok(html.includes('آزمون جامع ناقص') && html.includes('پیش‌نویس'),
     'پیش‌نویس جامع در صفحه دیده شود');

  // ۵) پاسخ‌های متناقض با «کل» رد می‌شود (ناقص ≠ متناقض)
  submitExam({ name: 'تست متناقض', kind: 'teaching', date: date, time: '10:00',
    total: '40', correct: '30', wrong: '20', blank: '5', duration: '60',
    error: '', note: '', subject: '' });
  st = preview.getState();
  ok((st.attempts || []).every(x => x.name !== 'تست متناقض'),
     'دادهٔ متناقض ذخیره نشود، یافت: ' + (st.attempts || []).map(x => x.name).join('|'));

  // ۶) کامل کردن پیش‌نویس: درصد محاسبه و پیش‌نویس برداشته می‌شود
  submitExam({ name: 'تست نیمه‌کاره', kind: 'teaching', date: date, time: '10:00',
    total: '40', correct: '30', wrong: '6', blank: '4', duration: '90',
    error: '', note: '', subject: '' });
  st = preview.getState();
  a = (st.attempts || []).find(x => x.name === 'تست نیمه‌کاره');
  ok(a.draft === false, 'پس از کامل شدن، پیش‌نویس برداشته شود، یافت: ' + a.draft);
  ok(a.percentage === 75, 'درصد درست محاسبه شود، یافت: ' + a.percentage);
  ok(preview.examConflicts().length === 0, 'آزمون بی‌کلاس تعارض نسازد');
} catch (e) { failures++; console.log('FAIL exam draft: ' + e.message) }
"""


@pytest.mark.skipif(NODE is None, reason="node برای اجرای پیش‌نمایش لازم است")
def test_exams_have_time_draft_state_and_conflict_detection(preview_js, tmp_path):
    """آزمون‌ها ساعت دارند، دادهٔ ناقص پیش‌نویس می‌شود و تعارض تشخیص داده می‌شود."""
    payload = tmp_path / "preview-bundle.js"
    payload.write_text(preview_js, encoding="utf-8")
    syllabus_json = tmp_path / "syllabus.json"
    import json as _json

    m = re.search(r'id="syllabusData"[^>]*>(.*?)</script>', PREVIEW.read_text(encoding="utf-8"), re.S)
    syllabus_json.write_text(m.group(1).replace("\\u003c", "<"), encoding="utf-8")
    seed = _seed_state()
    harness = _harness(payload, seed, syllabus_json)
    body = Path(harness).read_text(encoding="utf-8")
    marker = "console.log(JSON.stringify({failures}));\nprocess.exit(failures ? 1 : 0);"
    assert marker in body, "examdraft harness marker"
    body = body.replace(marker, _EXAMDRAFT_SCRIPT.strip() + "\n", 1)
    Path(harness).write_text(body, encoding="utf-8")
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

_BACKUP_SCRIPT = r"""
// ===== پشتیبان JSON، بازگردانی و خروجی HTML داده‌دار =====
// چیزی که باید ثابت شود: داده واقعاً از دستگاه بیرون می‌آید و واقعاً
// برمی‌گردد — نه اینکه فقط دکمه‌ها وجود داشته باشند.

const _mkBackupState = () => {
  const st0 = preview.getState();
  st0.activities = [{
    id: 'bk1', title: 'تمرین پشتیبان', type: 'independent_practice', subjectId: 's1',
    subjectName: 'زیست‌شناسی', estimate: 45, remaining: 45, actual: 0, state: 'planned',
    minChunk: 20, maxChunk: 90, splittable: true, deadline: 'none', personalWeight: 1
  }];
  st0.events = [{ id: 'bk2', title: 'کلاس پشتیبان', kind: 'class', weekday: 2,
    start: '15:00', end: '17:00', recorded: false, needsConfirmation: false }];
  st0.attempts = [{ id: 'bk3', name: 'آزمون پشتیبان', kind: 'teaching', date: '2026-11-05',
    time: '09:00', total: 40, correct: 30, wrong: 6, blank: 4, duration: 90,
    percentage: 75, draft: false, subjectId: '', subjectName: '' }];
  persistSilently(st0);
  return st0;
};
const _lastBlobText = () => {
  const all = global.__blobs || [];
  if (!all.length) return null;
  const b = all[all.length - 1];
  const parts = b.parts || [];
  return parts.map(x => (typeof x === 'string' ? x : String(x))).join('');
};

// ۱) پشتیبان JSON: داده واقعاً در فایل می‌رود
(async () => {
  try {
    _mkBackupState();
    global.__blobs = [];
    preview.backupJSON();
    const text = _lastBlobText();
    ok(!!text, 'پشتیبان JSON something بسازد');
    const raw = JSON.parse(text);
    ok(raw.app === 'K2-preview', 'سرآیند پشتیبان درست باشد');
    ok(!!raw.exportedAt, 'زمان خروجی ثبت شود');
    ok(Array.isArray(raw.state.activities) && raw.state.activities.length === 1,
       'فعالیت‌ها در پشتیبان باشند');
    ok(raw.state.activities[0].title === 'تمرین پشتیبان', 'محتوای فعالیت درست باشد');
    ok(raw.state.events[0].title === 'کلاس پشتیبان', 'رویدادها در پشتیبان باشند');
    ok(raw.state.attempts[0].percentage === 75, 'نتیجهٔ آزمون در پشتیبان باشد');

    // ۲) بازگردانی از JSON: داده جایگزین می‌شود
    const wiped = preview.getState();
    wiped.activities = []; wiped.events = []; wiped.attempts = [];
    persistSilently(wiped);
    ok(preview.getState().activities.length === 0, 'داده پاک شود');
    await preview.restoreFile({ name: 'K2-backup.json', text: async () => text });
    const back = preview.getState();
    ok(back.activities.length === 1 && back.activities[0].title === 'تمرین پشتیبان',
       'بازگردانی JSON فعالیت‌ها را برگرداند');
    ok(back.events.length === 1 && back.events[0].title === 'کلاس پشتیبان',
       'بازگردانی JSON رویدادها را برگرداند');
    ok(back.attempts.length === 1 && back.attempts[0].percentage === 75,
       'بازگردانی JSON آزمون‌ها را برگرداند');

    // ۳) خروجی HTML داده‌دار: خودبسنده و شامل داده
    global.__blobs = [];
    await preview.saveHTML();
    const html = _lastBlobText();
    ok(!!html && html.startsWith('<!doctype html>'), 'خروجی HTML بسازد');
    ok(html.includes('id="embeddedState"'), 'تگ وضعیت جاسازی‌شده در خروجی باشد');
    const m = html.match(/<script id="embeddedState" type="application\/json">([\s\S]*?)<\/script>/);
    ok(!!m, 'الگوی تگ وضعیت پیدا شود');
    const embedded = JSON.parse(m[1]);
    ok(embedded.activities[0].title === 'تمرین پشتیبان',
       'داده در HTML جاسازی شود (خروجی خودبسنده)');
    ok(embedded.attempts[0].percentage === 75, 'دادهٔ آزمون هم جاسازی شود');

    // ۴) بازگردانی از همان HTML داده‌دار
    const wiped2 = preview.getState();
    wiped2.activities = []; wiped2.events = []; wiped2.attempts = [];
    persistSilently(wiped2);
    await preview.restoreFile({ name: 'K2-preview-with-data.html', text: async () => html });
    const back2 = preview.getState();
    ok(back2.activities.length === 1 && back2.activities[0].title === 'تمرین پشتیبان',
       'بازگردانی از HTML داده‌دار کار کند');
    ok(back2.events.length === 1 && back2.events[0].title === 'کلاس پشتیبان',
       'بازگردانی از HTML رویدادها را هم برگرداند');

    // ۵) فایل نامرتبط باید خطای روشن بدهد، نه خرابی خاموش
    let rejected = false;
    try { await preview.restoreFile({ name: 'junk.json', text: async () => '{"hello":1}' }); }
    catch (e) { rejected = true; }
    ok(rejected, 'فایل ناسازگار رد شود');

    console.log(JSON.stringify({failures}));
    process.exit(failures ? 1 : 0);
  } catch (e) { failures++; console.log('FAIL backup: ' + e.message);
    console.log(JSON.stringify({failures})); process.exit(1); }
})();
"""


@pytest.mark.skipif(NODE is None, reason="node برای اجرای پیش‌نمایش لازم است")
def test_backup_restore_and_html_export_round_trip(preview_js, tmp_path):
    """پشتیبان JSON، بازگردانی و خروجی HTML داده‌دار واقعاً داده را جابه‌جا می‌کنند."""
    payload = tmp_path / "preview-bundle.js"
    payload.write_text(preview_js, encoding="utf-8")
    syllabus_json = tmp_path / "syllabus.json"
    import json as _json

    m = re.search(r'id="syllabusData"[^>]*>(.*?)</script>', PREVIEW.read_text(encoding="utf-8"), re.S)
    syllabus_json.write_text(m.group(1).replace("\\u003c", "<"), encoding="utf-8")
    seed = _seed_state()
    harness = _harness(payload, seed, syllabus_json)
    body = Path(harness).read_text(encoding="utf-8")
    marker = "console.log(JSON.stringify({failures}));\nprocess.exit(failures ? 1 : 0);"
    assert marker in body, "backup harness marker"
    # این اسکریپت خودش پایان را چاپ می‌کند (async است) پس نشانگر پایانی حذف می‌شود
    body = body.replace(marker, _BACKUP_SCRIPT.strip() + "\n", 1)
    Path(harness).write_text(body, encoding="utf-8")
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

_SUGGESTION_SCRIPT = r"""
// ===== تعداد تست روزانه پیشنهاد است، نه سهمیه =====
const _mkTest = (title, type, stateName) => ({
  id: 'sg_' + title, title, type: type || 'timed_test', subjectId: 's1',
  subjectName: 'زیست‌شناسی', estimate: 45, remaining: 45, actual: 0,
  state: stateName || 'planned', minChunk: 20, maxChunk: 90, splittable: true,
  deadline: 'none', personalWeight: 1
});

try {
  const st0 = preview.getState();
  // دو تست زمان‌دار باز + یک مطالعه
  st0.activities = [_mkTest('تست زمان‌دار الف'), _mkTest('تست زمان‌دار ب'), _mkTest('مطالعه', 'processing')];
  st0.events = [];
  persistSilently(st0);
  const plan = preview.getPlan();
  const inPlan = (plan.placements || []).filter(x => x.type === 'timed_test').length;
  ok(inPlan === 2, 'دو تست در برنامهٔ امروز باشند، یافت: ' + inPlan);
  clickNav('today');
  let html = pageHtml();
  ok(html.includes('تست‌های پیشنهادی امروز'), 'کارت تست‌های پیشنهادی امروز باشد');
  ok(html.includes('پیشنهاد'), 'واژهٔ پیشنهاد بیاید');
  ok(html.includes('نه سهمیه'), 'صریحاً گفته شود سهمیه نیست');
  ok(html.includes('تست ابزار یادگیری است، نه هدف'), 'هدف تست روشن باشد');
  clickNav('tests');
  html = pageHtml();
  ok(html.includes('پیشنهاد'), 'صفحهٔ تست هم پیشنهاد را بگوید');
  ok(html.includes('نه سهمیه'), 'صفحهٔ تست هم سهمیه‌نبودن را بگوید');
} catch (e) { failures++; console.log('FAIL suggestion: ' + e.message) }
"""


@pytest.mark.skipif(NODE is None, reason="node برای اجرای پیش‌نمایش لازم است")
def test_daily_test_counts_are_suggestions_not_quotas(preview_js, tmp_path):
    """تعداد تست روزانه به‌عنوان پیشنهاد ارائه می‌شود، نه سهمیهٔ الزامی."""
    payload = tmp_path / "preview-bundle.js"
    payload.write_text(preview_js, encoding="utf-8")
    syllabus_json = tmp_path / "syllabus.json"
    import json as _json

    m = re.search(r'id="syllabusData"[^>]*>(.*?)</script>', PREVIEW.read_text(encoding="utf-8"), re.S)
    syllabus_json.write_text(m.group(1).replace("\\u003c", "<"), encoding="utf-8")
    seed = _seed_state()
    harness = _harness(payload, seed, syllabus_json)
    body = Path(harness).read_text(encoding="utf-8")
    marker = "console.log(JSON.stringify({failures}));\nprocess.exit(failures ? 1 : 0);"
    assert marker in body, "suggestion harness marker"
    body = body.replace(marker, _SUGGESTION_SCRIPT.strip() + "\n", 1)
    Path(harness).write_text(body, encoding="utf-8")
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
