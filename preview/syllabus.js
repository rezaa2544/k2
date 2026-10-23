/* ==========================================================================
   سرفصل درس‌ها، ارزیابی مرحله‌به‌مرحلهٔ گفتارها و بانک منابع مستقل
   ==========================================================================
   این ماژول روی ساختار موجود سوار می‌شود و چیزی را بازنویسی نمی‌کند:
   - سرفصل از ``window.K2_SYLLABUS`` خوانده می‌شود (دادهٔ اولیه تأییدنشده).
   - پاسخ هر سؤال مستقل و قابل ویرایش ذخیره می‌شود؛ گزینهٔ «نمی‌دانم» همیشه
     موجود است تا کاربر مجبور به پاسخ ساختگی نشود.
   - وضعیت یک گفتار به کل فصل تعمیم داده نمی‌شود.
   - پایان مطالعه به معنای پایان تثبیت یا تست‌زنی نیست.
   ========================================================================== */

/* ---------- ۱. هشت سؤال ارزیابی ---------- */

const ASSESS_QUESTIONS = [
  {
    key: 'teaching', title: 'سؤال ۱ از ۸ · تدریس',
    hint: 'وضعیت کلاس یا تدریس این گفتار',
    options: [
      ['not_taught', 'هنوز تدریس نشده'],
      ['taught', 'تدریس شده'],
      ['partial', 'بخشی از تدریس را از دست داده‌ام'],
      ['missed', 'کلاس را از دست داده‌ام و باید جبران کنم'],
      ['repair', 'نیاز به رفع اشکال از تدریس دارم'],
      ['unknown', 'نمی‌دانم / نیاز به ارزیابی'],
    ],
  },
  {
    key: 'study', title: 'سؤال ۲ از ۸ · مطالعه',
    hint: 'مطالعهٔ محتوای این گفتار',
    options: [
      ['not_started', 'هنوز مطالعه نکرده‌ام'],
      ['started', 'مطالعه را شروع کرده‌ام ولی کامل نیست'],
      ['complete', 'کامل خوانده‌ام'],
      ['read_unsure', 'قبلاً خوانده‌ام اما مطمئن نیستم همه‌اش را یادم باشد'],
      ['need_reread', 'نیاز دارم دوباره مطالعه کنم'],
      ['unknown', 'نمی‌دانم / نیاز به ارزیابی'],
    ],
    askPages: ['started', 'complete', 'read_unsure'],
  },
  {
    key: 'comprehension', title: 'سؤال ۳ از ۸ · فهم مطلب',
    hint: 'این با «تمام‌شدن مطالعه» یکی نیست',
    options: [
      ['not_understood', 'مطلب را نفهمیده‌ام'],
      ['partial', 'بخشی از مطلب را متوجه شده‌ام'],
      ['mostly', 'کلیت مطلب را فهمیده‌ام ولی نکات مبهم دارم'],
      ['well', 'مطلب را خوب فهمیده‌ام'],
      ['repair', 'نیاز به رفع اشکال دارم'],
      ['unknown', 'نمی‌دانم / نیاز به ارزیابی'],
    ],
  },
  {
    key: 'consolidation', title: 'سؤال ۴ از ۸ · تثبیت',
    hint: 'مرور و تثبیت؛ جدا از مطالعه',
    options: [
      ['not_reviewed', 'هنوز مرور نکرده‌ام'],
      ['initial', 'مرور اولیه انجام شده ولی تثبیت نشده'],
      ['consolidated', 'مرور و تثبیت انجام شده'],
      ['risk', 'قبلاً تثبیت شده ولی احتمال فراموشی وجود دارد'],
      ['unknown', 'نمی‌دانم به تثبیت رسیده‌ام یا نه'],
    ],
  },
  {
    key: 'testing', title: 'سؤال ۵ از ۸ · تست‌زنی',
    hint: 'تست مبحثی و زمان‌دار این گفتار',
    options: [
      ['not_tested', 'هنوز تست نزده‌ام'],
      ['few', 'تست کم زده‌ام'],
      ['topic_tested', 'تست مبحثی زده‌ام'],
      ['enough_errors', 'تست کافی زده‌ام ولی اشتباه زیاد دارم'],
      ['satisfactory', 'تست زده‌ام و عملکردم رضایت‌بخش بوده'],
      ['retake', 'باید تست‌های قبلی را دوباره بزنم'],
      ['unknown', 'نمی‌دانم / نیاز به ارزیابی'],
    ],
    askTests: ['few', 'topic_tested', 'enough_errors', 'satisfactory', 'retake'],
  },
  {
    key: 'analysis', title: 'سؤال ۶ از ۸ · تحلیل آزمون و اشتباهات',
    hint: 'تحلیل جداست از خود آزمون',
    options: [
      ['not_analyzed', 'هنوز تحلیل نکرده‌ام'],
      ['partial', 'بخشی از آزمون را تحلیل کرده‌ام'],
      ['full', 'تحلیل کامل شده'],
      ['known_not_fixed', 'اشتباهاتم را می‌دانم ولی هنوز اصلاح نکرده‌ام'],
      ['fixed', 'اشتباهاتم را بررسی و اصلاح کرده‌ام'],
    ],
  },
  {
    key: 'essay', title: 'سؤال ۷ از ۸ · آمادگی تشریحی',
    hint: 'برای امتحانات نهایی؛ مستقل از وضعیت کنکور',
    options: [
      ['not_done', 'سؤال تشریحی حل نکرده‌ام'],
      ['flawed', 'پاسخ‌نویسی را تمرین کرده‌ام ولی اشکال دارم'],
      ['practiced', 'تمرین تشریحی انجام داده‌ام'],
      ['ready', 'پاسخ‌هایم را بررسی کرده‌ام و آمادگی مناسبی دارم'],
      ['unknown', 'نمی‌دانم / نیاز به ارزیابی'],
    ],
  },
  {
    key: 'speed', title: 'سؤال ۸ از ۸ · سرعت پاسخ‌دهی زمان‌دار',
    hint: 'مهارت در شرایط زمان‌دار؛ جدا از درست یا غلط بودن',
    options: [
      ['slow', 'درست حل می‌کنم ولی زمان زیادی می‌برد'],
      ['partial_time', 'بعضی سؤال‌ها را در زمان لازم حل می‌کنم'],
      ['timed_ok', 'در زمان لازم پاسخ می‌دهم'],
      ['panic', 'زمان‌دار بودن استرس می‌سازد و کار را خراب می‌کند'],
      ['unknown', 'نمی‌دانم / نیاز به ارزیابی'],
    ],
  },
];

/* ---------- ۲. نگاشت پاسخ به نوع عقب‌افتادگی ---------- */

const ASSESS_TO_BACKLOG = [
  ['teaching', ['missed', 'repair'], 'class', 'عقب‌افتادگی کلاس یا جلسهٔ آموزشی'],
  ['study', ['not_started', 'started', 'need_reread'], 'study', 'مطالعه ناقص'],
  ['comprehension', ['not_understood', 'partial', 'repair'], 'concept', 'نفهمیدن یا نیاز به رفع اشکال'],
  ['consolidation', ['not_reviewed', 'initial', 'risk', 'unknown'], 'consolidation', 'تثبیت ناقص'],
  ['testing', ['not_tested', 'few', 'enough_errors', 'retake'], 'testing', 'تست‌نزدن'],
  ['analysis', ['not_analyzed', 'partial', 'known_not_fixed'], 'analysis', 'تحلیل‌نکردن آزمون'],
  ['essay', ['not_done', 'flawed'], 'essay', 'تمرین تشریحی انجام‌نشده'],
  // «درست ولی کند» و «استرس زمان‌دار» نیاز واقعی‌اند و به تست زمان‌دار می‌روند؛
  // «زمان کافی دارم» عمداً فهرست نشده چون چیزی برای جبران ندارد.
  ['speed', ['slow', 'partial_time', 'panic'], 'testing', 'تمرین زمان‌دار ناکافی'],
];

/* ---------- ۳. ابزارهای کلید و وضعیت ---------- */

const sylKey = (subject, grade, chapter) => `${subject}|${grade}|${chapter}`;
const secKey = (subject, grade, chapter, section) => `${subject}|${grade}|${chapter}|${section}`;

/** فصل‌های یک درس/پایه با ادغام ویرایش‌های کاربر. */
function syllabusChapters(subject, grade) {
  const base = (window.K2_SYLLABUS?.[subject]?.[String(grade)]) || [];
  const edits = state.syllabusEdits || {};
  return base.map((ch) => {
    const e = edits[sylKey(subject, grade, ch.no)] || {};
    return {
      no: ch.no,
      title: e.title ?? ch.title,
      sections: e.sections ?? ch.sections,
      confirmed: e.confirmed === true,
    };
  });
}

/** تعداد گفتارهای شناخته‌شدهٔ یک فصل؛ ``null`` یعنی نامشخص. */
function chapterSectionCount(ch) {
  return ch.sections === null || ch.sections === undefined ? null : Number(ch.sections);
}

/** رکورد ارزیابی یک گفتار (بدون ساخت خودکار). */
function sectionRecord(subject, grade, chapter, section) {
  return (state.sections || {})[secKey(subject, grade, chapter, section)] || null;
}

/** آیا این گفتار نیازمند جبران است؟ فهرست نوع عقب‌افتادگی‌ها را برمی‌گرداند. */
function sectionNeeds(rec) {
  if (!rec) return [];
  const out = [];
  for (const [qkey, values, backlogType, label] of ASSESS_TO_BACKLOG) {
    if (values.includes(rec[qkey])) out.push({ type: backlogType, label, question: qkey });
  }
  return out;
}

/** تسلط خوداظهاری یا ``null`` اگر کاربر مطمئن نیست. */
function sectionMastery(rec) {
  if (!rec || rec.mastery === null || rec.mastery === undefined || rec.mastery === '') return null;
  const n = Number(rec.mastery);
  return Number.isFinite(n) ? Math.max(0, Math.min(100, n)) : null;
}

/** برچسب کوتاه وضعیت گفتار برای نمایش در جدول. */
function sectionBadge(rec) {
  if (!rec || !rec.updatedAt) return { text: 'ارزیابی نشده', tone: 'warn' };
  const needs = sectionNeeds(rec);
  if (!needs.length) return { text: 'نیازی باز نیست', tone: 'ok' };
  if (needs.length >= 3) return { text: `${needs.length} نیاز باز`, tone: 'danger' };
  return { text: `${needs.length} نیاز باز`, tone: 'backlog' };
}

/** درصد تکمیل ارزیابی (برای نمایش پیشرفت). */
function sectionAnswered(rec) {
  if (!rec) return 0;
  let n = 0;
  for (const q of ASSESS_QUESTIONS) if (rec[q.key]) n += 1;
  return n;
}

/* ---------- ۴. فرم ارزیابی مرحله‌ای (هشت سؤال) ---------- */

let assessDraft = null;

function assessStart(subject, grade, chapter, section) {
  const existing = sectionRecord(subject, grade, chapter, section) || {};
  assessDraft = {
    subject, grade, chapter, section, step: 0,
    // پاسخ‌های قبلی از خودِ فهرست سؤال‌ها خوانده می‌شوند تا «ویرایش پاسخ»
    // برای هر سؤالی کار کند — با فهرست دستی، سؤال تازه بی‌جواب باز می‌شد.
    answers: Object.fromEntries(
      ASSESS_QUESTIONS.map(q => [q.key, existing[q.key] ?? null])),
    mastery: existing.mastery ?? null,
    masteryUnknown: existing.mastery === null || existing.mastery === undefined || existing.mastery === '',
    pagesTotal: existing.pagesTotal ?? null,
    pagesDone: existing.pagesDone ?? null,
    testsTotal: existing.testsTotal ?? null,
    testsCorrect: existing.testsCorrect ?? null,
    testsWrong: existing.testsWrong ?? null,
    testsBlank: existing.testsBlank ?? null,
    minutesSpent: existing.minutesSpent ?? null,
    notes: existing.notes ?? '',
  };
  assessRender();
}

function assessRender() {
  if (!assessDraft) return;
  const d = assessDraft;
  const title = `گفتار ${d.section} · فصل ${d.chapter} · ${d.subject}`;
  if (d.step < ASSESS_QUESTIONS.length) {
    const q = ASSESS_QUESTIONS[d.step];
    const picked = d.answers[q.key];
    // عنوان خود سؤال («سؤال ۳ از ۸ · فهم مطلب») هم نمایش داده می‌شود؛
    // پیش‌تر فقط راهنما دیده می‌شد و کاربر نمی‌دانست کدام سؤال چندم است.
    let body = `<h3 class="card-title">${esc(q.title)}</h3><p class="card-body">${esc(q.hint)}</p><div class="button-row" style="flex-direction:column;align-items:stretch">`;
    for (const [val, label] of q.options) {
      body += `<button type="button" class="btn ${picked === val ? 'primary' : ''}" data-action="assess-pick:${q.key}:${val}">${esc(label)}</button>`;
    }
    body += `</div>`;
    if (q.askPages?.includes(picked)) {
      body += `<div class="form-grid"><label>تعداد صفحه/بخش خوانده‌شده<input name="pagesDone" type="number" min="0" inputmode="numeric" value="${d.pagesDone ?? ''}"></label><label>تعداد کل صفحه/بخش<input name="pagesTotal" type="number" min="0" inputmode="numeric" value="${d.pagesTotal ?? ''}"></label></div>`;
    }
    if (q.askTests?.includes(picked)) {
      body += `<div class="form-grid"><label>تست درست<input name="testsCorrect" type="number" min="0" inputmode="numeric" value="${d.testsCorrect ?? ''}"></label><label>تست غلط<input name="testsWrong" type="number" min="0" inputmode="numeric" value="${d.testsWrong ?? ''}"></label><label>تست نزده<input name="testsBlank" type="number" min="0" inputmode="numeric" value="${d.testsBlank ?? ''}"></label><label>زمان صرف‌شده (دقیقه)<input name="minutesSpent" type="number" min="0" inputmode="numeric" value="${d.minutesSpent ?? ''}"></label></div>`;
    }
    body += `<div class="modal-progress"><i style="width:${Math.round((d.step + 1) / (ASSESS_QUESTIONS.length + 1) * 100)}%"></i></div>`;
    body += `<div class="modal-actions">${d.step ? actionBtn('قبلی', 'assess-back') : ''}${actionBtn('بعدی', 'assess-next', 'primary')}${actionBtn('ذخیره و بستن', 'assess-save')}</div>`;
    dialog(title, body);
    return;
  }
  // گام آخر: میزان تسلط
  let body = `<h3 class="card-title">گام پایانی · میزان تسلط</h3><p class="card-body">میزان تسلط خودت را از ۰ تا ۱۰۰ مشخص کن. اگر مطمئن نیستی، گزینهٔ «مطمئن نیستم» را انتخاب کن؛ عدد ساختگی ثبت نمی‌شود.</p>`;
  body += `<div class="form-grid"><label>میزان تسلط (۰ تا ۱۰۰)<input name="mastery" type="number" min="0" max="100" inputmode="numeric" value="${d.masteryUnknown ? '' : (d.mastery ?? '')}" ${d.masteryUnknown ? 'disabled' : ''}></label></div>`;
  body += `<label class="check-label"><input type="checkbox" name="masteryUnknown" ${d.masteryUnknown ? 'checked' : ''} data-action="assess-mastery-unknown"> مطمئن نیستم / نیاز به ارزیابی</label>`;
  body += `<label>یادداشت (اختیاری)<textarea name="notes">${esc(d.notes || '')}</textarea></label>`;
  body += `<div class="modal-actions">${actionBtn('قبلی', 'assess-back')}${actionBtn('ذخیره ارزیابی', 'assess-save', 'primary')}${actionBtn('ذخیره و ساخت کارهای جبران', 'assess-backlog')}</div>`;
  dialog(title, body);
}

function assessCollect() {
  if (!assessDraft) return;
  const form = $('#modalForm');
  const d = assessDraft;
  if (form) {
    const data = new FormData(form);
    const g = (n) => { const v = data.get(n); return v === null || v === '' ? null : v; };
    d.pagesDone = g('pagesDone'); d.pagesTotal = g('pagesTotal');
    d.testsCorrect = g('testsCorrect'); d.testsWrong = g('testsWrong');
    d.testsBlank = g('testsBlank'); d.minutesSpent = g('minutesSpent');
    if (d.step >= ASSESS_QUESTIONS.length) {
      const mk = data.get('mastery');
      d.masteryUnknown = data.has('masteryUnknown') || mk === null || mk === '';
      d.mastery = d.masteryUnknown ? null : Math.max(0, Math.min(100, num(mk)));
      d.notes = String(data.get('notes') || '');
    }
  }
}

function assessSave(closeAfter = true) {
  assessCollect();
  const d = assessDraft;
  if (!d) return;
  const key = secKey(d.subject, d.grade, d.chapter, d.section);
  state.sections = state.sections || {};
  const prev = state.sections[key] || {};
  // پاسخ‌ها از خودِ فهرست سؤال‌ها ساخته می‌شوند، نه از فهرست دستی کلیدها.
  // چرا: پیش‌تر هر سؤال تازه در سه جا باید ثبت می‌شد و اگر جا می‌ماند،
  // بی‌صدا ذخیره نمی‌شد — کاربر پاسخ می‌داد و هیچ اتفاقی نمی‌افتاد.
  const answers = Object.fromEntries(
    ASSESS_QUESTIONS.map(q => [q.key, d.answers[q.key] ?? null]));
  state.sections[key] = {
    ...prev,
    ...answers,
    mastery: d.masteryUnknown ? null : d.mastery,
    pagesTotal: d.pagesTotal === null || d.pagesTotal === undefined ? null : num(d.pagesTotal),
    pagesDone: d.pagesDone === null || d.pagesDone === undefined ? null : num(d.pagesDone),
    testsTotal: d.testsTotal === null || d.testsTotal === undefined ? null : num(d.testsTotal),
    testsCorrect: d.testsCorrect === null || d.testsCorrect === undefined ? null : num(d.testsCorrect),
    testsWrong: d.testsWrong === null || d.testsWrong === undefined ? null : num(d.testsWrong),
    testsBlank: d.testsBlank === null || d.testsBlank === undefined ? null : num(d.testsBlank),
    minutesSpent: d.minutesSpent === null || d.minutesSpent === undefined ? null : num(d.minutesSpent),
    notes: d.notes || '',
    updatedAt: new Date().toISOString(),
  };
  if (closeAfter) {
    assessDraft = null;
    closeDialog();
    persist('ارزیابی گفتار ذخیره شد');
    render();
  }
}

/** از وضعیت ثبت‌شدهٔ گفتار، فعالیت‌های جبران می‌سازد (پیشنهادی، نه انجام‌شده). */
function assessCreateBacklog() {
  assessSave(false);
  const d = assessDraft;
  if (!d) return;
  const needs = sectionNeeds(state.sections[secKey(d.subject, d.grade, d.chapter, d.section)]);
  if (!needs.length) { notify('برای این گفتار نیاز بازهایی ثبت نشده است'); return; }
  const subject = (state.subjects || []).find((s) => s.name === d.subject);
  let created = 0;
  for (const need of needs) {
    state.activities = state.activities || [];
    state.activities.unshift({
      id: id(),
      title: `${need.label} · گفتار ${d.section} فصل ${d.chapter} ${d.subject}`,
      type: need.type,
      subjectId: subject?.id || '',
      subjectName: d.subject,
      examCoefficient: subject?.examCoefficient ?? null,
      estimate: 30,
      actual: 0,
      remaining: 30,
      minChunk: 15,
      maxChunk: 45,
      splittable: true,
      deadline: '',
      deadlineDate: '',
      state: 'open',
      reason: `section:${secKey(d.subject, d.grade, d.chapter, d.section)}`,
      createdAt: new Date().toISOString(),
    });
    created += 1;
  }
  assessDraft = null;
  closeDialog();
  persist(`${created} کار جبران به‌صورت «برنامه‌ریزی‌شده» ثبت شد`);
  render();
}

/* ---------- ۵. بانک منابع مستقل ---------- */

const RESOURCE_TYPES = [
  ['textbook', 'کتاب درسی'],
  ['notes', 'جزوهٔ دبیر'],
  ['video', 'فیلم آموزشی'],
  ['homework', 'تکلیف کلاسی'],
  ['topic_test', 'تست مبحثی'],
  ['small_exam', 'آزمون کوچک'],
  ['comprehensive_exam', 'آزمون جامع'],
  ['answer_key', 'پاسخ‌نامه'],
  ['exam_analysis', 'تحلیل آزمون'],
  ['review_summary', 'مرور و خلاصه‌نویسی'],
  ['essay_question', 'سؤال تشریحی امتحان نهایی'],
  ['custom', 'منبع دلخواه'],
];

const RESOURCE_TYPE_LABEL = Object.fromEntries(RESOURCE_TYPES);

function resourceStatusLabel(s) {
  return ({ not_started: 'شروع نشده', in_progress: 'در جریان', done: 'انجام‌شده', unknown: 'نامشخص' })[s] || s || 'نامشخص';
}

/** فهرست منابع با امکان فیلتر بر اساس درس/فصل/گفتار. */
function resourcesFor(subject, chapter, section) {
  return (state.resources || []).filter((r) => {
    if (subject && r.subject !== subject) return false;
    if (chapter !== undefined && chapter !== null && String(r.chapter) !== String(chapter)) return false;
    if (section !== undefined && section !== null && String(r.section) !== String(section)) return false;
    return true;
  });
}

function resourceForm(resourceId, prefill = null) {
  const r = resourceId ? (state.resources || []).find((x) => x.id === resourceId) : null;
  const subjects = selectedSubjects();
  const subject = r?.subject || prefill?.subject || subjects[0]?.name || '';
  const grade = r?.grade ?? prefill?.grade ?? gradeOfSubject(subject);
  const chapterDefault = r?.chapter ?? prefill?.chapter ?? null;
  const sectionDefault = r?.section ?? prefill?.section ?? null;
  const chapters = subject ? syllabusChapters(subject, grade) : [];
  resourceEditId = r ? r.id : null;
  let body = `<form id="modalForm" data-modal-type="resource">`;
  body += `<div class="form-grid">`;
  body += `<label>نوع منبع<select name="type">${RESOURCE_TYPES.map(([v, l]) => `<option value="${v}" ${r?.type === v ? 'selected' : ''}>${l}</option>`).join('')}</select></label>`;
  body += `<label>عنوان منبع<input name="title" required value="${esc(r?.title || '')}" placeholder="مثلاً جزوهٔ فصل ۳ دبیرستان"></label>`;
  body += `<label>درس<select name="subject">${subjects.map((s) => `<option value="${esc(s.name)}" ${s.name === subject ? 'selected' : ''}>${esc(s.name)}</option>`).join('')}</select></label>`;
  body += `<label>پایه<select name="grade">${[10, 11, 12].map((g) => `<option value="${g}" ${Number(grade) === g ? 'selected' : ''}>${g}</option>`).join('')}</select></label>`;
  body += `<label>فصل<select name="chapter"><option value="">— بدون فصل —</option>${chapters.map((c) => `<option value="${c.no}" ${String(chapterDefault) === String(c.no) ? 'selected' : ''}>فصل ${c.no} · ${esc(c.title)}</option>`).join('')}</select></label>`;
  body += `<label>گفتار<input name="section" type="number" min="0" inputmode="numeric" value="${sectionDefault ?? ''}" placeholder="نامشخص = خالی"></label>`;
  body += `</div>`;
  body += `<div class="form-grid">`;
  body += `<label>تعداد کل<input name="total" type="number" min="0" inputmode="numeric" value="${r?.total ?? ''}" placeholder="نامشخص = خالی"></label>`;
  body += `<label>تعداد انجام‌شده<input name="done" type="number" min="0" inputmode="numeric" value="${r?.done ?? ''}"></label>`;
  body += `<label>مدت تخمینی هر مورد (دقیقه)<input name="estimateMin" type="number" min="0" inputmode="numeric" value="${r?.estimateMin ?? ''}"></label>`;
  body += `<label>وضعیت<select name="status">${[['not_started', 'شروع نشده'], ['in_progress', 'در جریان'], ['done', 'انجام‌شده'], ['unknown', 'نامشخص']].map(([v, l]) => `<option value="${v}" ${r?.status === v ? 'selected' : ''}>${l}</option>`).join('')}</select></label>`;
  body += `<label>موعد احتمالی<input name="deadline" type="date" value="${esc(r?.deadline || '')}"></label>`;
  body += `</div>`;
  body += `<label>توضیحات<input name="notes" value="${esc(r?.notes || '')}"></label>`;
  body += `<p class="card-body">تعداد باقی‌مانده خودکار از «کل منهای انجام‌شده» حساب می‌شود. اگر کل را خالی بگذاری، بدهی قطعی ثبت نمی‌شود و منبع «نامشخص» می‌ماند.</p>`;
  body += `<div class="modal-actions">${actionBtn('انصراف', 'close-dialog')}${actionBtn('ذخیره منبع', 'save-resource', 'primary')}</div>`;
  body += `</form>`;
  dialog(r ? 'ویرایش منبع' : 'افزودن منبع', body);
}

/** پایهٔ پیش‌فرض یک درس از روی کتاب‌های انتخاب‌شدهٔ کاربر. */
function gradeOfSubject(subjectName) {
  const b = (state.books || []).find((x) => x.subject === subjectName && x.selected !== false && x.grade);
  return b?.grade ?? 12;
}

function resourceRemaining(r) {
  if (r.total === null || r.total === undefined || r.total === '') return null;
  const total = num(r.total);
  const done = num(r.done);
  return Math.max(0, total - done);
}

function submitResource(form) {
  const d = new FormData(form);
  const v = (n) => { const x = d.get(n); return x === null || x === '' ? null : x; };
  const title = String(v('title') || '').trim();
  if (!title) { notify('عنوان منبع لازم است'); return; }
  const total = v('total') === null ? null : num(v('total'));
  const done = v('done') === null ? null : num(v('done'));
  if (total !== null && done !== null && done > total) { notify('تعداد انجام‌شده از کل بیشتر است'); return; }
  const obj = {
    id: resourceEditId || id(),
    type: v('type'),
    title,
    subject: v('subject') || '',
    grade: num(v('grade'), 12),
    chapter: v('chapter') === null ? null : num(v('chapter')),
    section: v('section') === null ? null : num(v('section')),
    total,
    done,
    remaining: total === null ? null : Math.max(0, num(total) - num(done)),
    estimateMin: v('estimateMin') === null ? null : num(v('estimateMin')),
    status: v('status') || 'unknown',
    deadline: v('deadline') || '',
    notes: v('notes') || '',
    updatedAt: new Date().toISOString(),
  };
  state.resources = state.resources || [];
  const i = state.resources.findIndex((x) => x.id === obj.id);
  if (i >= 0) state.resources[i] = obj; else state.resources.unshift(obj);
  closeDialog();
  persist('منبع ذخیره شد');
  render();
}

/* ---------- ۶. نمای درخت سرفصل ---------- */

function syllabusSectionRow(subject, grade, ch, sec) {
  const rec = sectionRecord(subject, grade, ch.no, sec);
  const badge = sectionBadge(rec);
  const answered = sectionAnswered(rec);
  const mastery = sectionMastery(rec);
  const res = resourcesFor(subject, ch.no, sec);
  const remaining = res.reduce((n, r) => n + (resourceRemaining(r) ?? 0), 0);
  const needs = sectionNeeds(rec);
  return `<tr>
<td>${sec}</td>
<td>${esc(ch.title)}</td>
<td>${rec?.updatedAt ? `${answered}/۸ سؤال` : '—'}</td>
<td>${mastery === null ? 'نامشخص' : mastery + '٪'}</td>
<td>${res.length ? `${res.length} منبع${remaining ? ` · ${remaining} باقی‌مانده` : ''}` : '—'}</td>
<td>${needs.length ? esc(needs.map((n) => n.label).join(' · ')) : '—'}</td>
<td><span class="pill ${badge.tone === 'ok' ? 'ok' : badge.tone === 'danger' ? 'danger' : 'warn'}">${esc(badge.text)}</span></td>
<td>${actionBtn(rec?.updatedAt ? 'ویرایش ارزیابی' : 'ارزیابی گفتار', `assess:${subject}:${grade}:${ch.no}:${sec}`, rec?.updatedAt ? '' : 'primary')} ${actionBtn('منابع', `resources:${subject}:${ch.no}:${sec}`)}</td>
</tr>`;
}

function syllabusTree(subject, grade) {
  const chapters = syllabusChapters(subject, grade);
  if (!chapters.length) return emptyState('سرفصلی برای این پایه ثبت نشده', 'در تنظیمات یا بانک دروس، فصل‌ها را اضافه یا اصلاح کنید.');
  let out = '';
  for (const ch of chapters) {
    const count = chapterSectionCount(ch);
    const secs = count === null ? [] : Array.from({ length: count }, (_, i) => i + 1);
    const recs = secs.map((s) => sectionRecord(subject, grade, ch.no, s)).filter(Boolean);
    const open = recs.reduce((n, r) => n + sectionNeeds(r).length, 0);
    const done = recs.filter((r) => sectionNeeds(r).length === 0).length;
    out += `<article class="card tone-study"><div class="section-row"><h3 class="card-title">فصل ${ch.no} · ${esc(ch.title)}</h3><span class="pill ${count === null ? 'gray' : open ? 'warn' : 'ok'}">${count === null ? 'تعداد گفتار نامشخص' : `${done}/${count} گفتار بدون نیاز باز`}</span></div>`;
    if (count === null) {
      out += `<p class="card-body">تعداد گفتارهای این فصل در اطلاعات اولیه ثبت نشده است. خودت تعداد را وارد کن تا گفتارها ساخته شوند — عددی ساخته نمی‌شود.</p>`;
      out += `<div class="button-row">${actionBtn('＋ افزودن گفتار به این فصل', `syl-add-section:${subject}:${grade}:${ch.no}`)} ${actionBtn('ویرایش عنوان فصل', `syl-edit-chapter:${subject}:${grade}:${ch.no}`)}</div>`;
    } else {
      out += `<div class="table-wrap"><table><thead><tr><th>گفتار</th><th>فصل</th><th>ارزیابی</th><th>تسلط</th><th>منابع</th><th>نیازهای باز</th><th>وضعیت</th><th></th></tr></thead><tbody>${secs.map((s) => syllabusSectionRow(subject, grade, ch, s)).join('')}</tbody></table></div>`;
      out += `<div class="button-row">${actionBtn('＋ گفتار', `syl-add-section:${subject}:${grade}:${ch.no}`)} ${actionBtn('ویرایش فصل', `syl-edit-chapter:${subject}:${grade}:${ch.no}`)}</div>`;
    }
    if (open) out += `<div class="advice warning"><span class="advice-mark">!</span><span>${open} نیاز باز در این فصل. این‌ها از پاسخ‌های خودت ساخته شده‌اند و در «عقب‌افتادگی‌ها» به‌صورت کار قابل برنامه‌ریزی در دسترس‌اند.</span></div>`;
    out += `</article>`;
  }
  return out;
}

/* ---------- ۷. ویرایش ساختار سرفصل ---------- */

let sylDraft = null;

function sylEditChapterForm(subject, grade, chapterNo) {
  sylDraft = { subject, grade, chapter: chapterNo };
  const edits = state.syllabusEdits || {};
  const cur = edits[sylKey(subject, grade, chapterNo)] || {};
  const base = (window.K2_SYLLABUS?.[subject]?.[String(grade)] || []).find((c) => c.no === chapterNo) || {};
  const title = cur.title ?? base.title ?? '';
  const count = cur.sections ?? base.sections ?? '';
  dialog(`ویرایش فصل ${chapterNo}`, `<form id="modalForm" data-modal-type="syl-chapter">
<label>عنوان فصل<input name="title" value="${esc(title)}"></label>
<label>تعداد گفتار<input name="sections" type="number" min="0" inputmode="numeric" value="${count === null ? '' : count}" placeholder="نامشخص = خالی"></label>
<p class="card-body">این اطلاعات اولیه و تأییدنشده‌اند. اگر کتاب سال ۱۴۰۶ را داری و با آن تطبیق کرده‌ای، همین‌جا اصلاح کن.</p>
<div class="modal-actions">${actionBtn('انصراف', 'close-dialog')}${actionBtn('ذخیره', 'save-syl-chapter', 'primary')}</div></form>`);
}

function sylAddSectionForm(subject, grade, chapterNo) {
  sylDraft = { subject, grade, chapter: chapterNo };
  const ch = syllabusChapters(subject, grade).find((c) => c.no === chapterNo) || { sections: 0 };
  const next = (chapterSectionCount(ch) ?? 0) + 1;
  dialog('افزودن گفتار', `<form id="modalForm" data-modal-type="syl-section">
<label>شمارهٔ گفتار<input name="section" type="number" min="1" value="${next}"></label>
<p class="card-body">با ذخیره، گفتار به فصل اضافه می‌شود و ارزیابی مستقل خودش را می‌گیرد. وضعیت آن به بقیهٔ گفتارهای فصل تعمیم داده نمی‌شود.</p>
<div class="modal-actions">${actionBtn('انصراف', 'close-dialog')}${actionBtn('افزودن', 'save-syl-section', 'primary')}</div></form>`);
}

/* ---------- ۸. صفحهٔ بانک منابع ---------- */

function resourceBankPage(subject) {
  const all = resourcesFor(subject);
  const unknown = all.filter((r) => r.total === null || r.total === undefined);
  const rows = all.map((r) => {
    const rem = resourceRemaining(r);
    return `<tr><td>${esc(RESOURCE_TYPE_LABEL[r.type] || r.type)}</td><td>${esc(r.title)}</td><td>${esc(r.subject || '—')}</td><td>${r.chapter ? `فصل ${r.chapter}` : '—'}${r.section ? ` · گفتار ${r.section}` : ''}</td><td>${r.total === null || r.total === undefined ? 'نامشخص' : `${r.done ?? 0}/${r.total}`}</td><td>${rem === null ? 'نامشخص' : rem}</td><td>${r.estimateMin ? fmtMin(r.estimateMin) : '—'}</td><td>${esc(resourceStatusLabel(r.status))}</td><td>${esc(r.deadline || '—')}</td><td>${actionBtn('ویرایش', `resource-edit:${r.id}`)} ${actionBtn('حذف', `resource-delete:${r.id}`, 'danger')}</td></tr>`;
  }).join('');
  const subjects = selectedSubjects();
  const tabs = subjects.map((s) => `<button type="button" class="btn ${s.name === subject ? 'primary' : ''}" data-action="resource-subject:${esc(s.name)}">${esc(s.name)}</button>`).join('');
  const unknownNote = unknown.length ? `<div class="advice"><span class="advice-mark">i</span><span>${unknown.length} منبع «تعداد کل نامشخص» دارند. این‌ها به‌عنوان بدهی قطعی وارد برنامه نمی‌شوند؛ خودت مقدار واقعی را وارد کن.</span></div>` : '';
  return `<article class="card tone-study"><div class="section-row"><h3 class="card-title">منابع ${esc(subject || '')}</h3>${actionBtn('＋ افزودن منبع', 'add-resource', 'primary')}</div>${unknownNote}
<div class="button-row">${tabs}</div>
${all.length ? `<div class="table-wrap"><table><thead><tr><th>نوع</th><th>عنوان</th><th>درس</th><th>مکان</th><th>انجام‌شده/کل</th><th>باقی‌مانده</th><th>مدت هر مورد</th><th>وضعیت</th><th>موعد</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>` : emptyState('منبعی برای این درس ثبت نشده', 'کتاب درسی، جزوهٔ دبیر، فیلم آموزشی، تست، آزمون، پاسخ‌نامه یا تحلیل آزمون را اضافه کن.', actionBtn('افزودن منبع', 'add-resource', 'primary'))}
<p class="card-body">هر منبع مستقل است و به گفتار مشخص متصل می‌شود. اگر کل یا انجام‌شده را اصلاح کنی، باقی‌مانده خودکار به‌روز می‌شود.</p></article>`;
}

/* ---------- ۹. ذخیرهٔ ساختار سرفصل ---------- */

let resourceSubject = null;
let resourceEditId = null;

function submitSylChapter(form) {
  const d = new FormData(form);
  const { subject, grade, chapter } = sylDraft;
  const title = String(d.get('title') || '').trim();
  const raw = d.get('sections');
  if (!title) { notify('عنوان فصل لازم است'); return; }
  state.syllabusEdits = state.syllabusEdits || {};
  state.syllabusEdits[sylKey(subject, grade, chapter)] = {
    ...(state.syllabusEdits[sylKey(subject, grade, chapter)] || {}),
    title,
    sections: raw === null || raw === '' ? null : Math.max(0, num(raw)),
    confirmed: true,
  };
  closeDialog();
  persist('فصل به‌روزرسانی شد');
  render();
}

function submitSylSection(form) {
  const d = new FormData(form);
  const { subject, grade, chapter } = sylDraft;
  const section = Math.max(1, num(d.get('section')));
  const ch = (state.syllabusEdits[sylKey(subject, grade, chapter)] || {});
  const base = (window.K2_SYLLABUS?.[subject]?.[String(grade)] || []).find((c) => c.no === chapter) || {};
  const current = ch.sections ?? base.sections ?? 0;
  state.syllabusEdits = state.syllabusEdits || {};
  state.syllabusEdits[sylKey(subject, grade, chapter)] = {
    ...ch, sections: Math.max(num(current), section), confirmed: true,
  };
  closeDialog();
  persist(`گفتار ${section} به فصل ${chapter} اضافه شد`);
  render();
}

/* ---------- ۶ب. ورود گروهی تعداد گفتارها ---------- */

let sylCountsDraft = null;

/**
 * فرم گروهی تعداد گفتارها.
 *
 * چرا لازم است: دروسی مثل شیمی ۱۰ فصل دارند و هیچ‌کدام تعداد گفتار
 * ثبت‌نشده‌اند. اگر کاربر مجبور باشد فصل‌به‌فصل وارد کند، عملاً هیچ‌وقت
 * وارد نمی‌کند و برنامه روی دادهٔ خالی کار می‌کند. اینجا همهٔ فصل‌ها یک‌جا
 * دیده می‌شوند و خالی گذاشتن یعنی «نامشخص»، نه صفر.
 */
function sylCountsForm(subject, grade) {
  const chapters = syllabusChapters(subject, grade);
  if (!chapters.length) { notify('برای این پایه فصلی ثبت نشده است'); return; }
  sylCountsDraft = { subject, grade };
  const rows = chapters.map((ch) => {
    const count = chapterSectionCount(ch);
    return `<tr><td>${ch.no}</td><td>${esc(ch.title)}</td>`
      + `<td><input type="number" name="sec_${ch.no}" min="0" inputmode="numeric" value="${count === null ? '' : count}" placeholder="نامشخص = خالی"></td>`
      + `<td>${count === null ? '<span class="pill warn">نامشخص</span>' : count}</td></tr>`;
  }).join('');
  const unknown = chapters.filter((c) => chapterSectionCount(c) === null).length;
  dialog(`تعداد گفتارهای ${esc(subject)} · پایهٔ ${grade}`, `<form id="modalForm" data-modal-type="syl-counts">
<p class="card-body">${unknown ? `${unknown} فصل از ${chapters.length} فصل عدد ثبت‌نشده دارند. این‌ها «نامشخص» می‌مانند و برنامه هیچ عددی حدس نمی‌زند.` : 'همهٔ فصل‌ها عدد دارند؛ اگر کتاب ۱۴۰۶ را تطبیق داده‌ای همین‌جا اصلاح کن.'}</p>
<div class="table-wrap"><table><thead><tr><th>#</th><th>عنوان فصل</th><th>تعداد گفتار (خالی = نامشخص)</th><th>فعلی</th></tr></thead><tbody>${rows}</tbody></table></div>
<p class="card-body">تعداد را از روی کتاب سال ۱۴۰۶ خودت بخوان. اگر مطمئن نیستی، خالی بگذار؛ «نامشخص» صادقانه‌تر از یک عدد غلط است.</p>
<div class="modal-actions">${actionBtn('انصراف', 'close-dialog')}${actionBtn('ذخیرهٔ تعدادها', 'save-syl-counts', 'primary')}</div></form>`);
}

function submitSylCounts(form) {
  const d = new FormData(form);
  const { subject, grade } = sylCountsDraft;
  const chapters = syllabusChapters(subject, grade);
  state.syllabusEdits = state.syllabusEdits || {};
  let entered = 0, stillUnknown = 0;
  for (const ch of chapters) {
    const raw = d.get(`sec_${ch.no}`);
    const key = sylKey(subject, grade, ch.no);
    const prev = state.syllabusEdits[key] || {};
    if (raw === null || raw === undefined || String(raw).trim() === '') {
      // خالی = نامشخص. اگر قبلاً تعدادی ثبت شده بود، همان می‌ماند.
      stillUnknown += 1;
      if (prev.sections !== undefined) {
        state.syllabusEdits[key] = { ...prev, sections: null, confirmed: true };
      }
      continue;
    }
    state.syllabusEdits[key] = { ...prev, sections: Math.max(0, num(raw)), confirmed: true };
    entered += 1;
  }
  closeDialog();
  persist(entered
    ? `${entered} فصل با تعداد گفتار ثبت شد${stillUnknown ? ` · ${stillUnknown} فصل نامشخص ماند` : ''}`
    : 'هیچ تعدادی وارد نشد؛ همه «نامشخص» ماندند');
  render();
}

/* ---------- ۱۰. نمای یکپارچهٔ سرفصل در صفحهٔ مباحث ---------- */

function syllabusOverview() {
  const subjects = selectedSubjects();
  const meta = window.K2_SYLLABUS_META || {};
  const statusNote = `<div class="advice"><span class="advice-mark">i</span><span>سرفصل‌های زیر <strong>${esc(meta.statusLabel || 'اطلاعات اولیه · تأییدنشده')}</strong> هستند. با نسخهٔ معتبر کتاب‌های ۱۴۰۶ تطبیق نشده‌اند؛ عنوان فصل، تعداد گفتار و هر چیزی را خودت اصلاح کن. هیچ بخش جدیدی بی‌اطلاع تو جایگزین نمی‌شود.</span></div>`;
  if (!subjects.length) return statusNote + emptyState('اول درس‌ها را انتخاب کن', 'در «بانک دروس» درس‌های خودت را انتخاب کن تا سرفصل‌ها نمایش داده شود.', actionBtn('رفتن به بانک دروس', 'go-courses'));
  let out = statusNote;
  for (const s of subjects) {
    const grade = gradeOfSubject(s.name);
    const chapters = syllabusChapters(s.name, grade);
    if (!chapters.length) continue;
    const known = chapters.filter((c) => chapterSectionCount(c) !== null);
    const totalSec = known.reduce((n, c) => n + chapterSectionCount(c), 0);
    const assessed = (state.sections ? Object.keys(state.sections) : []).filter((k) => k.startsWith(`${s.name}|${grade}|`)).length;
    const allUnknown = chapters.length > 0 && known.length === 0;
    out += `<article class="card tone-exam"><div class="section-row"><h3 class="card-title">${esc(s.name)} · پایهٔ ${grade}</h3><span class="pill ${totalSec ? (assessed < totalSec ? 'warn' : 'ok') : 'gray'}">${totalSec ? `${assessed} از ${totalSec} گفتار ارزیابی‌شده` : 'تعداد گفتار نامشخص'}</span></div>`;
    out += `<div class="button-row">${actionBtn('نمایش گفتارها', `syllabus-open:${esc(s.name)}:${grade}`, 'primary')} ${actionBtn('منابع این درس', `resource-subject:${esc(s.name)}`)}${allUnknown ? ` ${actionBtn('ورود تعداد گفتارها', `syl-counts:${esc(s.name)}:${grade}`, 'primary')}` : ''}</div>`;
    if (allUnknown) out += `<div class="advice warning"><span class="advice-mark">!</span><span>تعداد گفتارهای این درس در اطلاعات اولیه ثبت نشده (${chapters.length} فصل، همه نامشخص). برنامه هیچ عددی حدس نمی‌زند و صفر فرض نمی‌کند؛ تا وقتی خودت از کتاب سال ۱۴۰۶ بخوانی و وارد کنی، ارزیابی گفتاربه‌گفتار برای این درس ممکن نیست.</span></div>`;
    out += `</article>`;
  }
  return out;
}

function syllabusDetail(subject, grade) {
  return `<div class="button-row">${actionBtn('← بازگشت به فهرست سرفصل‌ها', 'syllabus-close')}</div>` + syllabusTree(subject, grade);
}

let syllabusOpen = null;

/* ---------- ۱۲. کلاس‌های ثابت اولیه (نیازمند تأیید) ---------- */

//: برنامهٔ هفتگی اولیه که کاربر داده است. هرجا ساعت داده نشده یا نامطمئن
//: بوده، ``start``/``end`` تهی است تا اپ ساعت قطعی نسازد؛ کاربر خودش وارد
//: می‌کند. ``needsConfirmation`` یعنی پیش از استفاده باید تأیید شود.
const FIXED_CLASSES_SEED = [
  { weekday: 0, title: 'زیست‌شناسی', start: '15:00', end: '19:00', kind: 'class' },
  { weekday: 0, title: 'فیزیک', start: '19:30', end: '22:45', kind: 'class' },
  { weekday: 1, title: 'شیمی', start: '15:00', end: '19:00', kind: 'class' },
  { weekday: 1, title: 'دینی و زبان', start: null, end: null, kind: 'class',
    note: 'ساعت طبق تصمیم نهاییٔ کاربر — نامشخص' },
  { weekday: 2, title: 'ریاضی', start: '19:30', end: '23:00', kind: 'class' },
  { weekday: 2, title: 'زمین‌شناسی', start: null, end: null, kind: 'class',
    note: 'حدود دو ساعت — ساعت نامشخص' },
  { weekday: 3, title: 'زیست‌شناسی', start: '15:00', end: '19:00', kind: 'class' },
  { weekday: 3, title: 'عربی', start: '19:15', end: '21:15', kind: 'class' },
  { weekday: 4, title: 'فیزیک', start: '15:00', end: '19:15', kind: 'class' },
  { weekday: 4, title: 'شیمی', start: '19:30', end: '22:45', kind: 'class' },
  { weekday: 5, title: 'فارسی', start: '13:15', end: '14:45', kind: 'class' },
  { weekday: 5, title: 'هویت اجتماعی', start: '15:00', end: '16:30', kind: 'class' },
  { weekday: 6, title: 'ریاضی', start: '12:00', end: '15:00', kind: 'class' },
  { weekday: 6, title: 'سلامت و بهداشت', start: null, end: null, kind: 'class',
    note: 'حدود دو ساعت — ساعت نامشخص' },
];

/** کلاس‌های ثابت اولیه را با علامت «نیازمند تأیید» اضافه می‌کند. */
function seedFixedClasses() {
  state.events = state.events || [];
  let added = 0;
  for (const c of FIXED_CLASSES_SEED) {
    const dup = state.events.some((e) => e.title === c.title && Number(e.weekday) === c.weekday);
    if (dup) continue;
    state.events.push({
      id: id(), title: c.title, kind: c.kind, weekday: c.weekday,
      start: c.start, end: c.end, recorded: false,
      subjectId: '', subjectName: c.title,
      note: c.note || 'ساعت اولیهٔ اعلام‌شده؛ پیش از استفاده تأیید کنید',
      fromSeed: true, needsConfirmation: true,
    });
    added += 1;
  }
  persist(added
    ? `${added} کلاس با علامت «نیازمند تأیید» اضافه شد`
    : 'همهٔ کلاس‌های اولیه از قبل ثبت شده‌اند');
  render();
}

/** برچسب وضعیت تأیید یک رویداد. */
function eventConfirmBadge(e) {
  if (!e.needsConfirmation) return '';
  const unknownTime = !e.start || !e.end;
  return `<span class="pill warn">${unknownTime ? 'ساعت نامشخص · نیازمند تأیید' : 'نیازمند تأیید'}</span>`;
}

/** هشدار کلاس‌های ساعت‌نامشخص: تا وارد نشوند اشغال‌شده شمرده نمی‌شوند. */
function unknownClassNote() {
  const unknown = (state.events || []).filter((e) => e.needsConfirmation && (!e.start || !e.end));
  if (!unknown.length) return '';
  return `<div class="advice warning"><span class="advice-mark">!</span><span>${unknown.length} کلاس «ساعت نامشخص» دارد. تا وارد نکنی، در برنامه اشغال‌شده شمرده نمی‌شود؛ ساعت قطعی از خودت ساخته نشده است.</span></div>`;
}
