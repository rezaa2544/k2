
  // ---- ماژول آزمون‌های جامع دوره‌ای ----
  // چرا این ماژول جدا است: آزمون جامع و تحلیل آن دو کار مستقل‌اند. آزمون
  // رویداد سنجش است، تحلیل کار شناخنی روی نتیجه. اگر یکی شوند، «آزمون دادم»
  // به‌جای «دانستم چه کردی» ثبت می‌شود و برنامه عوض نمی‌شود.
  //
  // قاعدهٔ صداقت: بازهٔ ۱۴ روزه و تاریخ شروع ۱۴ آبان ۱۴۰۵ ورودی کاربر است،
  // نه ادعای رسمی. تاریخ رسمی آزمون ابلاغ نشده و اینجا چیزی جعل نمی‌شود.

  const EXAM_SERIES_DEFAULTS = {
    enabled: true,
    startISO: '2026-11-05',   // ۱۴ آبان ۱۴۰۵ (تقویم شمسی)
    intervalDays: 14,
    durationMinutes: 210,     // برآورد خود کاربر؛ قابل ویرایش
    analysisMinutes: 60,      // تحلیل جدا و مستقل از خود آزمون
    startNote: 'تاریخ شروع و بازهٔ تکرار را خودت تعیین می‌کنی؛ هیچ تاریخ رسمی ابلاغ نشده است.'
  };

  // تقسیم صحیح به سمت صفر، مثل div استاندارد جلالی. Math.floor اینجا غلط
  // است: div(3-8, 6) باید 0 شود نه 1- و کل تاریخ یک ماه و دو سال جابه‌جا می‌شود.
  function jDiv(a, b) { return Math.trunc(a / b) }
  function jMod(a, b) { return a - jDiv(a, b) * b }

  // تبدیل تقویم: الگوریتم استاندارد جلالی (بدون وابستگی بیرونی)
  function jalBreaks() {
    return [-61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210, 1635, 2060, 2097, 2192, 2262, 2324, 2394, 2456, 3178];
  }
  function jG2D(gy, gm, gd) {
    let d = jDiv((gy + jDiv(gm - 8, 6) + 100100) * 1461, 4) + jDiv(153 * jMod(gm + 9, 12) + 2, 5) + gd - 34840408;
    d = d - jDiv(jDiv(gy + 100100 + jDiv(gm - 8, 6), 100) * 3, 4) + 752;
    return d;
  }
  function jD2G(jdn) {
    let j = 4 * jdn + 139361631;
    j = j + jDiv(jDiv(4 * jdn + 183187720, 146097) * 3, 4) * 4 - 3908;
    const i = jDiv(jMod(j, 1461), 4) * 5 + 308;
    const gd = jDiv(jMod(i, 153), 5) + 1;
    const gm = jDiv(i, 153) + 1;
    const gy = jDiv(j, 1461) - 100100 + jDiv(8 - gm, 6);
    return { gy, gm, gd };
  }
  function jalCal(jy) {
    const breaks = jalBreaks(), bl = breaks.length;
    const gy = jy + 621;
    let leapJ = -14, jp = breaks[0], jm = 0, jump = 0, leap = 0, n = 0;
    for (let i = 1; i < bl; i += 1) {
      jm = breaks[i]; jump = jm - jp;
      if (jy < jm) break;
      leapJ = leapJ + jDiv(jump, 33) * 8 + jDiv(jMod(jump, 33), 4);
      jp = jm;
    }
    n = jy - jp;
    leapJ = leapJ + jDiv(n, 33) * 8 + jDiv(jMod(n, 33) + 3, 4);
    if (jMod(jump, 33) === 4 && jump - n === 4) leapJ += 1;
    const leapG = jDiv(gy, 4) - jDiv((jDiv(gy, 100) + 1) * 3, 4) - 150;
    const march = 20 + leapJ - leapG;
    if (jump - n < 6) n = n - jump + jDiv(jump + 4, 33) * 33;
    leap = jMod(jMod(n + 1, 33) - 1, 4);
    if (leap === -1) leap = 4;
    return { gy, march, leap };
  }
  function jJ2D(jy, jm, jd) {
    const r = jalCal(jy);
    return jG2D(r.gy, 3, r.march) + (jm - 1) * 31 - jDiv(jm, 7) * (jm - 7) + jd - 1;
  }
  function jD2J(jdn) {
    const gy = jD2G(jdn).gy;
    let jy = gy - 621;
    let r = jalCal(jy);
    let k = jdn - jG2D(gy, 3, r.march);
    if (k >= 0) {
      if (k <= 185) return { jy, jm: 1 + jDiv(k, 31), jd: jMod(k, 31) + 1 };
      k -= 186;
    } else {
      jy -= 1; k += 179; if (r.leap === 1) k += 1;
      r = jalCal(jy);
    }
    return { jy, jm: 7 + jDiv(k, 30), jd: jMod(k, 30) + 1 };
  }
  const JALALI_MONTHS = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
    'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'];

  // 'YYYY-MM-DD' → {jy,jm,jd}
  function isoToJalali(iso) {
    const m = String(iso || '').match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!m) return null;
    return jD2J(jG2D(Number(m[1]), Number(m[2]), Number(m[3])));
  }
  // {jy,jm,jd} → 'YYYY-MM-DD'
  function jalaliToIso(jy, jm, jd) {
    const g = jD2G(jJ2D(jy, jm, jd));
    return `${String(g.gy).padStart(4, '0')}-${String(g.gm).padStart(2, '0')}-${String(g.gd).padStart(2, '0')}`;
  }
  // برچسب خوانا: «۱۴ آبان ۱۴۰۵»
  function jalaliLabel(iso) {
    const j = isoToJalali(iso);
    if (!j) return String(iso || '—');
    return `${j.jd} ${JALALI_MONTHS[j.jm - 1]} ${j.jy}`;
  }
  function isoAddDays(iso, days) {
    const d = new Date(`${iso}T00:00:00Z`);
    d.setUTCDate(d.getUTCDate() + days);
    return d.toISOString().slice(0, 10);
  }
  function isoBetween(iso, from, to) { return iso >= from && iso <= to }

  function ensureExamSeries() {
    // ادغام نرم پیش‌فرض‌ها: state ذخیره‌شدهٔ کاربر بازنویسی نمی‌شود.
    const cur = state.examSeries || {};
    state.examSeries = { ...EXAM_SERIES_DEFAULTS, ...cur };
    if (state.examSeries.intervalDays < 1) state.examSeries.intervalDays = 1;
    return state.examSeries;
  }

  // تاریخ‌های وقوع در بازهٔ [from, to] — مرزها هم شاملند.
  function examSeriesOccurrences(series, from, to) {
    if (!series || series.enabled === false) return [];
    const start = String(series.startISO || '');
    if (!start) return [];
    const step = Math.max(1, Math.round(num(series.intervalDays, 14)));
    const out = [];
    // نخستین وقوع بزرگ‌تر یا مساوی از
    let first = start;
    if (from > start) {
      const diff = Math.round((new Date(`${from}T00:00:00Z`) - new Date(`${start}T00:00:00Z`)) / 86400000);
      const k = Math.floor(diff / step);
      first = isoAddDays(start, k * step);
      // اگر نزدیک‌ترین وقوع پیش از بازه افتاد، تا رسیدن به آن جلو می‌رویم.
      while (first < from) first = isoAddDays(first, step);
    }
    for (let iso = first; iso <= to; iso = isoAddDays(iso, step)) {
      if (iso >= start) out.push(iso);
      if (out.length > 200) break; // محافظ: حلقهٔ بی‌پایان نشود
    }
    return out;
  }

  // وقوع‌ها را به دو فعالیت مستقل تبدیل می‌کند: خود آزمون و تحلیل آن.
  function syncExamSeries(todayIso) {
    ensureExamSeries();
    const s = state.examSeries;
    if (!s.enabled) return 0;
    const today = todayIso || todayISO();
    const horizon = isoAddDays(today, 60);
    let created = 0;
    for (const iso of examSeriesOccurrences(s, today, horizon)) {
      const label = jalaliLabel(iso);
      const has = role => (state.activities || []).some(a => a.examOccurrence === iso && a.examRole === role);
      const base = {
        date: iso, examOccurrence: iso, origin: 'examSeries',
        deadline: 'hard', deadlineDate: iso, subjectId: '', subjectName: '',
        topicId: null, topicName: '', state: 'planned', splittable: false,
        minChunk: 15, maxChunk: Math.max(15, Math.min(90, num(s.durationMinutes, 210))),
        personalWeight: 1, reason: ''
      };
      if (!has('exam')) {
        const est = Math.max(1, Math.round(num(s.durationMinutes, 210)));
        state.activities.unshift({
          ...base, id: id(), title: `آزمون جامع دوره‌ای · ${label}`, type: 'exam', examRole: 'exam',
          estimate: est, remaining: est,
          reason: `چرخهٔ ${Math.round(num(s.intervalDays, 14))} روزه؛ این نوبت ${label}. آزمون رویداد سنجش است، نه خودِ یادگیری.`
        });
        created += 1;
      }
      if (!has('analysis')) {
        const est = Math.max(1, Math.round(num(s.analysisMinutes, 60)));
        state.activities.unshift({
          ...base, id: id(), title: `تحلیل آزمون جامع · ${label}`, type: 'test_analysis', examRole: 'analysis',
          estimate: est, remaining: est,
          reason: `تحلیل مستقل از آزمون ${label}: گلوگاه درس، کد خطای غالب و اقدام اصلاحی. بدون تحلیل، نوبت بعدی همان اشتباه را تکرار می‌کند.`
        });
        created += 1;
      }
    }
    return created;
  }

  function examSeriesForm() {
    const s = ensureExamSeries();
    dialog('تنظیم چرخهٔ آزمون جامع', `<form id="modalForm"><p class="card-body">آزمون و تحلیل آن دو فعالیت مستقل می‌شوند. بازهٔ تکرار و تاریخ شروع را خودت تعیین می‌کنی؛ تاریخ رسمی آزمون ابلاغ نشده و اینجا چیزی جعل نمی‌شود.</p><div class="form-grid"><label>تاریخ اولین نوبت (میلادی)<input type="date" name="startISO" value="${esc(s.startISO)}" required></label><label>بازهٔ تکرار (روز)<input type="number" name="intervalDays" min="1" max="90" value="${Math.round(num(s.intervalDays, 14))}" required></label><label>مدت خودِ آزمون (دقیقه)<input type="number" name="durationMinutes" min="15" max="600" value="${Math.round(num(s.durationMinutes, 210))}" required></label><label>مدت تحلیل (دقیقه)<input type="number" name="analysisMinutes" min="5" max="600" value="${Math.round(num(s.analysisMinutes, 60))}" required></label><label class="check-label"><input type="checkbox" name="enabled" ${s.enabled !== false ? 'checked' : ''}> چرخه فعال باشد</label></div><p class="card-body">تاریخ میلادی برای دقت ذخیره می‌شود؛ معادل شمسی همان روز: <strong>${esc(jalaliLabel(s.startISO))}</strong></p><div class="modal-actions"><button class="btn" type="button" data-action="close">انصراف</button><button class="btn primary" type="submit">ذخیرهٔ چرخه</button></div></form>`);
    setModalType('examSeries');
  }

  function submitExamSeries(form) {
    const d = new FormData(form), v = n => d.get(n);
    const start = String(v('startISO') || '').trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(start)) { notify('تاریخ شروع معتبر نیست'); return; }
    const intervalDays = Math.max(1, Math.min(90, Math.round(num(v('intervalDays'), 14))));
    const durationMinutes = Math.max(15, Math.min(600, Math.round(num(v('durationMinutes'), 210))));
    const analysisMinutes = Math.max(5, Math.min(600, Math.round(num(v('analysisMinutes'), 60))));
    const enabled = d.has('enabled');
    state.examSeries = { ...ensureExamSeries(), startISO: start, intervalDays, durationMinutes, analysisMinutes, enabled };
    // نوبت‌های آینده با مدت تازه ساخته می‌شوند؛ نوبت‌های گذشته دست‌نخورده می‌مانند.
    const created = syncExamSeries();
    saveAndRender(created > 0
      ? `چرخه ذخیره شد · ${created} فعالیت مستقل برای نوبت‌های پیش‌رو ساخته شد`
      : 'چرخه ذخیره شد؛ نوبت پیش‌رو همین حالا در برنامه است');
  }

  // کارت نمایش چرخه در صفحهٔ آزمون‌های جامع
  function examSeriesCard() {
    const s = ensureExamSeries();
    const today = todayISO();
    const next = examSeriesOccurrences(s, today, isoAddDays(today, 60)).slice(0, 6);
    const registered = (state.attempts || []).filter(a => a.kind === 'official' || a.kind === 'mock');
    const occ = iso => {
      const done = registered.some(a => String(a.date || '').slice(0, 10) === iso);
      const acts = (state.activities || []).filter(a => a.examOccurrence === iso);
      const examAct = acts.find(a => a.examRole === 'exam');
      const anAct = acts.find(a => a.examRole === 'analysis');
      return { iso, done, examAct, anAct };
    };
    const rows = next.map(o => {
      const r = occ(o);
      const status = r.done ? 'ثبت‌شده' : (r.examAct?.state === 'done' ? 'انجام‌شده' : 'در انتظار');
      const analysis = r.anAct ? (r.anAct.state === 'done' ? 'تحلیل انجام شد' : 'تحلیل مستقل در برنامه') : '—';
      return `<tr><td>${esc(jalaliLabel(o))}</td><td>${esc(o)}</td><td>${esc(DAYS[weekdayOfIso(o)])}</td><td>${esc(Math.round(num(s.durationMinutes, 210)))}</td><td>${esc(Math.round(num(s.analysisMinutes, 60)))}</td><td>${esc(status)}</td><td>${esc(analysis)}</td></tr>`;
    }).join('');
    return `<article class="card tone-exam"><div class="section-row"><h3 class="card-title">چرخهٔ آزمون جامع تکرارشونده</h3>${actionBtn('ویرایش چرخه', 'exam-series-edit')}</div><p class="card-body">هر نوبت دو فعالیت <strong>مستقل</strong> می‌سازد: خودِ آزمون و تحلیل آن. یکی می‌تواند انجام شود و دیگری نه؛ وضعیت یکی به دیگری سرریز نمی‌شود.${s.enabled === false ? '<br><strong>چرخه در حال حاضر غیرفعال است.</strong>' : ''}</p><div class="metrics"><article class="metric tone-exam"><p class="metric-label">نخستین نوبت</p><p class="metric-value">${esc(jalaliLabel(s.startISO))}</p><p class="metric-hint">${esc(s.startISO)}</p></article><article class="metric tone-exam"><p class="metric-label">بازهٔ تکرار</p><p class="metric-value">${esc(Math.round(num(s.intervalDays, 14)))} روز</p><p class="metric-hint">قابل ویرایش</p></article><article class="metric tone-exam"><p class="metric-label">مدت آزمون / تحلیل</p><p class="metric-value">${esc(Math.round(num(s.durationMinutes, 210)))} / ${esc(Math.round(num(s.analysisMinutes, 60)))}</p><p class="metric-hint">دقیقه</p></article></div>${next.length ? `<div class="table-wrap"><table><thead><tr><th>نوبت</th><th>تاریخ</th><th>روز</th><th>آزمون</th><th>تحلیل</th><th>وضعیت</th><th>تحلیل مستقل</th></tr></thead><tbody>${rows}</tbody></table></div>` : emptyState('نوبتی در بازهٔ ۶۰ روز آینده نیست', 'چرخه غیرفعال است یا تاریخ شروع گذشتهٔ دور است.')}<div class="advice"><span class="advice-mark">i</span><span>تاریخ رسمی آزمون کنکور ابلاغ نشده؛ بازهٔ ۱۴ روزه انتخاب خودِ شماست و هر وقت خواستید عوض می‌شود. تحلیل نوبت‌های گذشته را حتماً با کد خطا ثبت کنید تا چرخهٔ بعدی قابل مقایسه باشد.</span></div></article>`;
  }

  function weekdayOfIso(iso) {
    // شمارهٔ روز هفتهٔ این پروژه: ۰ = شنبه
    const d = new Date(`${iso}T00:00:00Z`);
    return ((d.getUTCDay() + 1) % 7);
  }
