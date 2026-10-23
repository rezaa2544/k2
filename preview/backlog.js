/* ==========================================================================
   مدیریت عقب‌افتادگی‌ها — سند پایدار، نه فهرست موقت
   ==========================================================================
   اصل طراحی: عقب‌افتادگی **حذف نمی‌شود**. با ساخت برنامهٔ جدید هم پاک
   نمی‌شود؛ یا انجام می‌شود، یا به روز دیگر منتقل می‌شود، یا با تصمیم
   آگاهانهٔ کاربر وضعیتش عوض می‌شود.

   برای همین عقب‌افتادگی سند پایدار است (state.backlogs) و فعالیت زمان‌بندی
   از آن **مشتق** می‌شود (activity.backlogId). تکمیل فعالیت، باقی‌ماندهٔ
   عقب‌افتادگی را کم می‌کند ولی خودش را حذف نمی‌کند.
   ========================================================================== */

/* ---------- ۱. دوازده نوع عقب‌افتادگی ---------- */

//: (کلید، برچسب، مدت تخمینی پیش‌فرض به دقیقه)
//: مدت‌ها **فرضیهٔ محصول [H]** هستند و در فرم قابل ویرایشند؛ عدد سؤال یا
//: صفحه ساخته نمی‌شود.
const BACKLOG_TYPES = [
  ['class', 'عقب‌افتادگی کلاس یا جلسهٔ آموزشی', 60],
  ['video', 'فیلم آموزشی دیده‌نشده', 45],
  ['study', 'مطالعه ناقص', 40],
  ['concept', 'نفهمیدن یا نیاز به رفع اشکال', 50],
  ['review', 'مرور انجام‌نشده', 25],
  ['consolidation', 'تثبیت ناقص', 30],
  ['testing', 'تست‌نزدن', 45],
  ['analysis', 'تحلیل‌نکردن آزمون', 40],
  ['essay', 'تمرین تشریحی انجام‌نشده', 45],
  ['homework', 'تکلیف انجام‌نشده', 35],
  ['multiple', 'چند مورد هم‌زمان', 0],
  ['other', 'مورد دیگر (با توضیح دلخواه)', 30],
];

const BACKLOG_TYPE_LABEL = Object.fromEntries(BACKLOG_TYPES);
const BACKLOG_TYPE_ESTIMATE = Object.fromEntries(BACKLOG_TYPES.map(([k, , e]) => [k, e]));

const BACKLOG_STATUS = {
  open: 'باز · انجام نشده',
  scheduled: 'در برنامهٔ امروز',
  in_progress: 'در حال انجام',
  partial: 'ناقص انجام شده',
  done: 'انجام شده',
  deferred: 'به روز دیگر منتقل شد',
};

const BACKLOG_IMPORTANCE = { 1: 'کم', 2: 'متوسط', 3: 'زیاد', 4: 'بسیار زیاد', 5: 'حیاتی' };

/** مدت تخمینی کل بر اساس نوع‌های انتخاب‌شده. */
function backlogEstimate(types) {
  return (types || []).reduce((n, t) => n + BACKLOG_TYPE_ESTIMATE[t], 0);
}

/** برچسب خوانا برای فهرست نوع‌ها. */
function backlogTypesLabel(types) {
  const list = (types || []).filter((t) => t !== 'multiple');
  const hasMulti = (types || []).includes('multiple');
  const parts = list.map((t) => BACKLOG_TYPE_LABEL[t] || t);
  if (hasMulti) parts.unshift('چند مورد هم‌زمان');
  return parts.join(' · ') || '—';
}

/** برچسب انواع برای نمایش کوتاه در جدول. */
function backlogTypePills(types) {
  return (types || [])
    .map((t) => `<span class="pill ${t === 'multiple' ? 'warn' : 'info'}">${esc(BACKLOG_TYPE_LABEL[t] || t)}</span>`)
    .join(' ');
}

/* ---------- ۲. فرم ثبت عقب‌افتادگی (انتخاب چندگانه) ---------- */

function addBacklogForm(backlog) {
  const subjects = selectedSubjects();
  const b = backlog || {};
  const types = b.types || [];
  const subject = b.subject || subjects[0]?.name || '';
  const chapters = subject ? syllabusChapters(subject, num(b.grade, gradeOfSubject(subject))) : [];
  const estimate = b.estimate ?? backlogEstimate(types);
  let body = `<form id="modalForm" data-modal-type="backlog" ${backlog ? `data-backlog-id="${b.id}"` : ''}>`;
  body += `<p class="card-body">نوع‌های عقب‌افتادگی را <strong>هم‌زمان</strong> می‌توانی انتخاب کنی. مثلاً اگر گفتاری را نخوانده‌ای، نفهمیده‌ای و تست هم نزده‌ای، هر سه را علامت بزن؛ زمان هر کدام جدا برآورد می‌شود.</p>`;
  body += `<div class="form-grid">`;
  body += `<label>درس<select name="subject">${subjects.map((s) => `<option value="${esc(s.name)}" ${s.name === subject ? 'selected' : ''}>${esc(s.name)}</option>`).join('')}</select></label>`;
  body += `<label>عنوان / مبحث<input name="title" required value="${esc(b.title || '')}" placeholder="مثلاً گفتار ۳ فصل ۲ زیست"></label>`;
  body += `<label>فصل<select name="chapter"><option value="">— بدون فصل —</option>${chapters.map((c) => `<option value="${c.no}" ${String(b.chapter) === String(c.no) ? 'selected' : ''}>فصل ${c.no} · ${esc(c.title)}</option>`).join('')}</select></label>`;
  body += `<label>گفتار<input name="section" type="number" min="0" inputmode="numeric" value="${b.section ?? ''}" placeholder="اختیاری"></label>`;
  body += `</div>`;

  body += `<fieldset style="border:1px solid var(--border);border-radius:10px;padding:10px;margin:10px 0"><legend style="font-size:12px;font-weight:800;color:var(--muted);padding:0 6px">نوع عقب‌افتادگی (چند مورد مجاز است)</legend>`;
  for (const [key, label] of BACKLOG_TYPES) {
    const on = types.includes(key);
    body += `<label class="check-label" style="margin:5px 0"><input type="checkbox" name="types" value="${key}" ${on ? 'checked' : ''}> ${esc(label)}${BACKLOG_TYPE_ESTIMATE[key] ? ` <small style="color:var(--muted)">(~${BACKLOG_TYPE_ESTIMATE[key]} دقیقه)</small>` : ''}</label>`;
  }
  body += `</fieldset>`;

  body += `<div class="form-grid">`;
  body += `<label>مدت تخمینی کل (دقیقه)<input name="estimate" type="number" min="0" inputmode="numeric" value="${estimate ?? ''}"></label>`;
  body += `<label>باقی‌مانده (دقیقه)<input name="remaining" type="number" min="0" inputmode="numeric" value="${b.remaining ?? ''}"></label>`;
  body += `<label>حجم کار (تعداد صفحه/فیلم/تست — اختیاری)<input name="volume" type="number" min="0" inputmode="numeric" value="${b.volume ?? ''}"></label>`;
  body += `<label>انجام‌شده از حجم (اختیاری)<input name="volumeDone" type="number" min="0" inputmode="numeric" value="${b.volumeDone ?? ''}"></label>`;
  body += `<label>اهمیت<select name="importance">${[1, 2, 3, 4, 5].map((i) => `<option value="${i}" ${num(b.importance, 3) === i ? 'selected' : ''}>${BACKLOG_IMPORTANCE[i]}</option>`).join('')}</select></label>`;
  body += `<label>موعد (اختیاری)<input name="due" type="date" value="${esc(b.due || '')}"></label>`;
  body += `</div>`;
  body += `<label>توضیحات<input name="notes" value="${esc(b.notes || '')}" placeholder="مثلاً جزئیات مورد دیگر یا دلیل عقب‌افتادگی"></label>`;
  body += `<div class="modal-actions">${actionBtn('انصراف', 'close-dialog')}${actionBtn(backlog ? 'ذخیرهٔ تغییرات' : 'ثبت عقب‌افتادگی', 'save-backlog', 'primary')}</div>`;
  body += `</form>`;
  dialog(backlog ? 'ویرایش عقب‌افتادگی' : 'ثبت عقب‌افتادگی', body);
}

function submitBacklog(form) {
  const d = new FormData(form);
  const v = (n) => { const x = d.get(n); return x === null || x === '' ? null : x; };
  const title = String(v('title') || '').trim();
  const types = d.getAll('types').map(String);
  if (!title) { notify('عنوان یا مبحث عقب‌افتادگی لازم است'); return; }
  if (!types.length) { notify('حداقل یک نوع عقب‌افتادگی را انتخاب کن'); return; }
  if (types.includes('other') && !String(v('notes') || '').trim()) {
    notify('برای «مورد دیگر» توضیح دلخواه لازم است'); return;
  }
  const estimate = v('estimate') === null ? backlogEstimate(types) : num(v('estimate'));
  const remaining = v('remaining') === null ? estimate : num(v('remaining'));
  if (remaining > estimate && estimate > 0) { notify('باقی‌مانده از مدت تخمینی کل بیشتر است'); return; }
  const backlogId = form.dataset.backlogId || id();
  const existing = (state.backlogs || []).find((x) => x.id === backlogId);
  const obj = {
    id: backlogId,
    title,
    types,
    subject: v('subject') || '',
    subjectName: v('subject') || '',
    grade: num(v('grade'), gradeOfSubject(v('subject') || '')),
    chapter: v('chapter') === null ? null : num(v('chapter')),
    section: v('section') === null ? null : num(v('section')),
    estimate,
    remaining,
    volume: v('volume') === null ? null : num(v('volume')),
    volumeDone: v('volumeDone') === null ? null : num(v('volumeDone')),
    importance: num(v('importance'), 3),
    due: v('due') || '',
    notes: v('notes') || '',
    status: existing?.status || 'open',
    history: existing?.history || [{ at: new Date().toISOString(), action: 'ثبت شد' }],
    createdAt: existing?.createdAt || new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
  if (!existing) obj.history = [{ at: new Date().toISOString(), action: 'ثبت شد' }];
  state.backlogs = state.backlogs || [];
  const i = state.backlogs.findIndex((x) => x.id === obj.id);
  if (i >= 0) state.backlogs[i] = obj; else state.backlogs.unshift(obj);
  closeDialog();
  persist(existing ? 'عقب‌افتادگی به‌روزرسانی شد' : 'عقب‌افتادگی ثبت شد');
  render();
}

/* ---------- ۳. مشتق‌سازی فعالیت زمان‌بندی از عقب‌افتادگی ---------- */

/** فعالیت زمان‌بندی‌شدهٔ مربوط به یک عقب‌افتادگی (اگر باشد). */
function backlogActivity(backlogId) {
  return (state.activities || []).find((a) => a.backlogId === backlogId);
}

/** عقب‌افتادگی را در برنامهٔ امروز قرار می‌دهد (فعالیت مشتق می‌سازد). */
function scheduleBacklog(backlogId) {
  const b = (state.backlogs || []).find((x) => x.id === backlogId);
  if (!b) return;
  if (b.status === 'done') { notify('این عقب‌افتادگی انجام شده است'); return; }
  state.activities = state.activities || [];
  const existing = backlogActivity(backlogId);
  const minutes = Math.max(15, num(b.remaining) || num(b.estimate) || 30);
  if (existing) {
    existing.remaining = minutes;
    existing.estimate = minutes;
    existing.state = 'open';
    existing.reason = 'از عقب‌افتادگی به برنامه برگشت';
  } else {
    state.activities.unshift({
      id: id(),
      title: `${backlogTypesLabel(b.types)} · ${b.title}`,
      type: 'consolidation',
      backlogId,
      subjectId: '', subjectName: b.subjectName || b.subject || '',
      examCoefficient: null,
      estimate: minutes, remaining: minutes,
      minChunk: 15, maxChunk: 60, splittable: true,
      deadline: b.due ? 'hard' : '', deadlineDate: b.due || '',
      state: 'open', reason: 'مشتق از عقب‌افتادگی',
      createdAt: new Date().toISOString(),
    });
  }
  b.status = 'scheduled';
  b.history.push({ at: new Date().toISOString(), action: 'در برنامهٔ امروز قرار گرفت' });
  persist('عقب‌افتادگی در برنامهٔ امروز قرار گرفت');
  render();
}

/** تکمیل/پیشرفت فعالیت مشتق، باقی‌ماندهٔ عقب‌افتادگی را کم می‌کند. */
function syncBacklog(backlogId, doneMinutes) {
  const b = (state.backlogs || []).find((x) => x.id === backlogId);
  if (!b) return;
  const before = num(b.remaining);
  b.remaining = Math.max(0, before - num(doneMinutes));
  b.volumeDone = b.volume !== null && b.volume !== undefined
    ? Math.min(num(b.volume), num(b.volumeDone) + 1) : b.volumeDone;
  b.status = b.remaining > 0 ? 'partial' : 'done';
  b.history.push({
    at: new Date().toISOString(),
    action: b.remaining > 0
      ? `${num(doneMinutes)} دقیقه انجام شد · ${b.remaining} دقیقه باقی مانده`
      : 'انجام شد',
  });
  b.updatedAt = new Date().toISOString();
}

/** انتقال عقب‌افتادگی به روز دیگر با تصمیم آگاهانهٔ کاربر. */
function deferBacklog(backlogId) {
  const b = (state.backlogs || []).find((x) => x.id === backlogId);
  if (!b) return;
  const reason = prompt('دلیل انتقال به روز دیگر را بنویسید:');
  if (!reason || !reason.trim()) return;
  b.status = 'deferred';
  b.notes = `${b.notes ? b.notes + ' · ' : ''}انتقال: ${reason.trim()}`;
  b.history.push({ at: new Date().toISOString(), action: `به روز دیگر منتقل شد · ${reason.trim()}` });
  b.updatedAt = new Date().toISOString();
  // فعالیت مشتق حذف نمی‌شود؛ از برنامه بیرون می‌رود ولی عقب‌افتادگی می‌ماند.
  state.activities = (state.activities || []).filter((a) => a.backlogId !== backlogId);
  persist('عقب‌افتادگی به روز دیگر منتقل شد');
  render();
}

/* ---------- ۴. صفحهٔ عقب‌افتادگی‌ها ---------- */

function backlogsPage() {
  const list = state.backlogs || [];
  const open = list.filter((b) => !['done'].includes(b.status));
  const done = list.filter((b) => b.status === 'done');
  const totalRemaining = open.reduce((n, b) => n + num(b.remaining), 0);
  const overdue = open.filter((b) => b.due && b.due < todayISO());
  const plan = makePlan();
  const capacity = plan.capacity;
  const over = totalRemaining > capacity;

  const rows = open.map((b) => {
    const act = backlogActivity(b.id);
    const inPlan = act && !['done', 'dropped'].includes(act.state);
    return `<tr>
<td>${esc(b.title)}</td>
<td>${esc(b.subjectName || '—')}${b.chapter ? ` · فصل ${b.chapter}` : ''}${b.section ? ` · گفتار ${b.section}` : ''}</td>
<td>${backlogTypePills(b.types)}</td>
<td>${b.volume === null || b.volume === undefined ? '—' : `${num(b.volumeDone)}/${b.volume}`}</td>
<td>${fmtMin(num(b.remaining))}</td>
<td>${fmtMin(num(b.estimate))}</td>
<td>${esc(b.due || '—')}${b.due && b.due < todayISO() ? ' <span class="pill danger">از موعد گذشته</span>' : ''}</td>
<td>${BACKLOG_IMPORTANCE[num(b.importance, 3)] || '—'}</td>
<td>${esc(BACKLOG_STATUS[b.status] || b.status)}${inPlan ? ' <span class="pill ok">در برنامهٔ امروز</span>' : ''}</td>
<td>${actionBtn('در برنامهٔ امروز', `backlog-schedule:${b.id}`, 'primary')} ${actionBtn('ویرایش', `backlog-edit:${b.id}`)} ${actionBtn('انتقال به روز دیگر', `backlog-defer:${b.id}`)}</td>
</tr>`;
  }).join('');

  const suggestion = over
    ? `حجم باقی‌مانده (${fmtMin(totalRemaining)}) از ظرفیت امروز (${fmtMin(capacity)}) بیشتر است. سه راه واقع‌بینانه: (۱) فقط مهم‌ترین‌ها را در برنامه بگذار و بقیه را با «انتقال به روز دیگر» آگاهانه جابه‌جا کن؛ (۲) حجم کار را کم کن؛ (۳) بازبینی اولویت را عوض کن. هیچ‌کدام به‌صورت خودکار انجام نمی‌شود.`
    : 'حجم باقی‌مانده با ظرفیت امروز سازگار است.';

  return `<div class="page-scroll">${pageHeader('عقب‌افتادگی‌ها', `${open.length} مورد باز · ${fmtMin(totalRemaining)} باقی‌مانده`, actionBtn('＋ ثبت عقب‌افتادگی', 'add-backlog', 'primary'))}
${overdue.length ? `<div class="advice warning"><span class="advice-mark">!</span><span>${overdue.length} عقب‌افتادگی از موعدش گذشته است. برای هر کدام تصمیم بگیر: انجام، انتقال آگاهانه، یا تغییر اولویت.</span></div>` : ''}
<div class="advice ${over ? 'warning' : ''}"><span class="advice-mark">${over ? '!' : 'i'}</span><span>${esc(suggestion)}</span></div>
<div class="metrics">
<article class="metric tone-backlog"><p class="metric-label">باقی‌مانده</p><p class="metric-value">${fmtMin(totalRemaining)}</p><p class="metric-hint">${open.length} مورد باز</p></article>
<article class="metric tone-timer"><p class="metric-label">ظرفیت امروز</p><p class="metric-value">${fmtMin(capacity)}</p><p class="metric-hint">پس از تعهدها</p></article>
<article class="metric tone-ok"><p class="metric-label">انجام‌شده</p><p class="metric-value">${done.length}</p><p class="metric-hint">از ${list.length} مورد</p></article>
<article class="metric tone-review"><p class="metric-label">از موعد گذشته</p><p class="metric-value">${overdue.length}</p><p class="metric-hint">نیازمند تصمیم</p></article>
</div>
${open.length ? `<div class="table-wrap"><table><thead><tr><th>عنوان</th><th>درس و مکان</th><th>نوع</th><th>حجم</th><th>باقی‌مانده</th><th>تخمین</th><th>موعد</th><th>اهمیت</th><th>وضعیت</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>` : emptyState('عقب‌افتادگی‌ای ثبت نشده', 'وقتی کاری را کامل نکردی یا نفهمیدی، همین‌جا ثبتش کن؛ در برنامهٔ روزهای بعد دیده می‌شود و بی‌صدا حذف نمی‌شود.', actionBtn('ثبت عقب‌افتادگی', 'add-backlog', 'primary'))}
${done.length ? `<article class="card tone-ok"><h3 class="card-title">انجام‌شده‌ها</h3><div class="table-wrap"><table><thead><tr><th>عنوان</th><th>نوع</th><th>تکمیل</th></tr></thead><tbody>${done.map((b) => `<tr><td>${esc(b.title)}</td><td>${backlogTypePills(b.types)}</td><td>${esc(b.history?.at(-1)?.action || 'انجام شد')}</td></tr>`).join('')}</tbody></table></div></article>` : ''}
<div class="advice"><span class="advice-mark">i</span><span>عقب‌افتادگی با ساخت برنامهٔ جدید حذف نمی‌شود. کار انجام‌نشده می‌ماند، به روز دیگر منتقل می‌شود یا با تصمیم خودت وضعیتش عوض می‌شود. مدت‌های تخمینی فرضیهٔ محصول [H] هستند و قابل ویرایشند.</span></div>
</div>`;
}
