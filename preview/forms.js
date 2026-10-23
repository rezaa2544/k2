
  function addActivityForm(a=null){dialog(a?'ویرایش فعالیت':'افزودن فعالیت',`<form id="modalForm"><label>عنوان فعالیت<input name="title" required value="${esc(a?.title||'')}"></label><div class="form-grid"><label>نوع<select name="type">${Object.entries(ACT_TYPES).map(([k,v])=>`<option value="${k}" ${a?.type===k?'selected':''}>${v}</option>`).join('')}</select></label><label>درس<select name="subject">${subjectOptions()}</select></label><label>برآورد (دقیقه)<input type="number" name="estimate" min="1" max="600" value="${num(a?.estimate,45)}" required></label><label>حداقل بخش<input type="number" name="minChunk" min="5" max="120" value="${num(a?.minChunk,20)}"></label><label>حداکثر بخش<input type="number" name="maxChunk" min="10" max="180" value="${num(a?.maxChunk,90)}"></label><label>مهلت<select name="deadline"><option value="none">بدون مهلت</option><option value="soft" ${a?.deadline==='soft'?'selected':''}>نرم</option><option value="hard" ${a?.deadline==='hard'?'selected':''}>سخت</option></select></label><label>تاریخ مهلت<input type="date" name="deadlineDate" value="${esc(a?.deadlineDate||'')}"></label><label>وزن شخصی (۰٫۵ تا ۲)<input type="number" name="weight" min="0.5" max="2" step="0.1" value="${num(a?.personalWeight,1)}"></label><label class="check-label"><input type="checkbox" name="splittable" ${a?.splittable!==false?'checked':''}> قابل تقسیم</label></div><div class="modal-actions"><button class="btn" type="button" data-action="close">انصراف</button><button class="btn primary" type="submit">ذخیره فعالیت</button></div></form>`);if(a){$('#modalForm').dataset.edit=a.id;$('#modalForm [name=subject]').value=a.subjectId||''}setModalType('activity')}
  function addExamForm(a=null){dialog(a?'ویرایش نوبت آزمون':'ثبت نوبت آزمون',`<form id="modalForm"><label>نام آزمون<input name="name" required value="${esc(a?.name||'')}"></label><div class="form-grid"><label>نوع<select name="kind">${Object.entries(EXAM_KINDS).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></label><label>درس<select name="subject">${subjectOptions()}</select></label><label>تاریخ<input type="date" name="date" value="${todayISO()}" required></label><label>ساعت شروع (برای تشخیص تعارض)<input type="time" name="time" value="${esc(a?.time||'')}" placeholder="اختیاری"></label><label>کل سؤال<input type="number" name="total" min="1" max="500" placeholder="خالی = پیش‌نویس"></label><label>درست<input type="number" name="correct" min="0" value="${a?.correct ?? 0}" placeholder="خالی = ۰"></label><label>غلط<input type="number" name="wrong" min="0" value="${a?.wrong ?? 0}" placeholder="خالی = ۰"></label><label>نزده<input type="number" name="blank" min="0" value="${a?.blank ?? 0}" placeholder="خالی = ۰"></label><label>مدت (دقیقه)<input type="number" name="duration" min="0" value="${a?.duration ?? 0}"></label><label>کد خطا<select name="error"><option value="">ثبت نشده</option>${Object.entries(ERRORS).map(([k,v])=>`<option value="${k}">${k} · ${v}</option>`).join('')}</select></label><label>یادداشت<textarea name="note"></textarea></label></div><label>پیوست نتیجهٔ آزمون (اختیاری)<input type="file" name="attachment" accept="image/*,.pdf,.txt,.csv"></label><p class="card-body">برنامه تصویر را <strong>نمی‌خوانَد</strong>؛ فقط نام و حجم فایل به‌عنوان منبع اعدادی که خودت وارد کرده‌ای ثبت می‌شود. در نسخهٔ دسکتاپ فایل در پوشهٔ محلی برنامه کپی می‌شود.</p><div class="modal-actions"><button class="btn" type="button" data-action="close">انصراف</button><button class="btn primary" type="submit">ثبت آزمون</button></div></form>`);setModalType('exam')}
  function addReviewForm(){dialog('افزودن مورد مرور',`<form id="modalForm"><label>عنوان مورد<input name="label" required></label><div class="form-grid"><label>درس<select name="subject">${subjectOptions()}</select></label><label>مبحث مرتبط (اختیاری)<select name="topicId"><option value="">بدون اتصال</option>${(state.topics||[]).map(t=>`<option value="${esc(t.id)}">${esc(t.subjectName)} · ${esc(t.name)}</option>`).join('')}</select></label><label>نوع<select name="type"><option>مفهومی</option><option>حفظی</option><option>محاسباتی</option><option>واژگانی</option><option>نموداری</option></select></label><label>موعد<input type="date" name="due" value="${todayISO()}"></label><label>دشواری ۱ تا ۵<input type="number" name="difficulty" min="1" max="5" value="3"></label><label>یادداشت<textarea name="content"></textarea></label></div><div class="modal-actions"><button class="btn" type="button" data-action="close">انصراف</button><button class="btn primary" type="submit">ذخیره</button></div></form>`);setModalType('review')}
  function eventForm(e=null){dialog(e?'ویرایش رویداد':'افزودن کلاس یا تعهد',`<form id="modalForm"><label>عنوان<input name="title" required value="${esc(e?.title||'')}"></label><div class="form-grid"><label>نوع<select name="kind">${Object.entries(EVENT_KINDS).map(([k,v])=>`<option value="${k}" ${e?.kind===k?'selected':''}>${v}</option>`).join('')}</select></label>${weekdaySelect('weekday',e?.weekday??weekday())}<label>درس<select name="subject">${subjectOptions()}</select></label>${timeInputs(e?.start||'09:00',e?.end||'10:00')}<label class="check-label"><input name="recorded" type="checkbox" ${e?.recorded?'checked':''}> ضبط‌شده/غیرهم‌زمان</label><label>یادداشت<input name="note" value="${esc(e?.note||'')}"></label></div><div class="modal-actions"><button class="btn" type="button" data-action="close">انصراف</button><button class="btn primary" type="submit">ذخیره</button></div></form>`);if(e){$('#modalForm').dataset.edit=e.id;$('#modalForm [name=subject]').value=e.subjectId||''}setModalType('event')}
  function routineForm(r=null){dialog(r?'ویرایش روال':'افزودن روال ثابت',`<form id="modalForm"><label>عنوان روال<input name="title" required value="${esc(r?.title||'')}"></label><div class="form-grid"><label>نوع<select name="kind">${Object.entries(ROUTINE_KINDS).map(([k,v])=>`<option value="${k}" ${r?.kind===k?'selected':''}>${v}</option>`).join('')}</select></label>${timeInputs(r?.start||'12:00',r?.end||'12:30')}<label>تکرار<select name="repeat"><option value="daily">روزانه</option><option value="alternate" ${r?.repeat==='alternate'?'selected':''}>یک‌روزدرمیان</option></select></label><fieldset class="day-picker"><legend>روزهای تکرار</legend>${DAYS.map((d,i)=>`<label><input type="checkbox" name="days" value="${i}" ${(r?.days||[0,1,2,3,4,5,6]).includes(i)?'checked':''}>${d}</label>`).join('')}</fieldset></div><div class="modal-actions"><button class="btn" type="button" data-action="close">انصراف</button><button class="btn primary" type="submit">ذخیره روال</button></div></form>`);if(r)$('#modalForm').dataset.edit=r.id;setModalType('routine')}
  // ---- راه‌اندازی: گام‌های جمع‌وجور ----
  // مرجع نیازمندی‌ها: docs/USER_SCHEDULE_AND_ONBOARDING.md §3،
  // docs/MASTER_PRODUCT_BLUEPRINT.md بخش A و UNIFIED_REQUIREMENTS_CATALOG.md
  // (ONB-01..05، EST-02). هیچ گامی دادهٔ نمونه نیست؛ عدد پیش‌فرض فرضیهٔ قابل
  // تنظیم است و تعارض فقط از رویداد واقعی کاربر ساخته می‌شود (D-023).
  const SETUP_TITLES = ['پروفایل آزمون', 'درس و کتاب', 'کلاس‌ها و تعهدات',
    'خواب، غذا و روال‌ها', 'آزمون جامع', 'سطح مبحثی و برآورد زمان',
    'اولویت و تأیید نهایی'];
  const SETUP_TOTAL = SETUP_TITLES.length;
  // گام‌های اختیاری قابل رد کردن‌اند؛ بقیه بدون پاسخ جلو نمی‌روند.
  const SETUP_OPTIONAL = [false, false, false, false, true, true, false];
  const ESTIMATE_DEFAULT_KEYS = [
    ['testing', 'تست زمان‌دار'], ['analysis', 'تحلیل تست'],
    ['consolidation', 'تثبیت'], ['homework', 'تکلیف'], ['review', 'مرور فعال']];

  /** تعارض واقعی بین رویدادهایی که خود کاربر در همین راه‌اندازی وارد کرده. */
  function setupConflicts() {
    const o = state.onboarding.values || {};
    const items = [];
    (o.attend === 'yes' ? (o.classes || []) : []).forEach((e, i) => items.push({ e, i, key: 'class' }));
    (o.commitments || []).forEach((e, i) => items.push({ e, i, key: 'commitment' }));
    const live = items.filter(x => !x.e.recorded);
    const hits = [];
    for (let i = 0; i < live.length; i++) {
      for (let j = i + 1; j < live.length; j++) {
        const x = live[i], y = live[j];
        if (x.e.weekday === y.e.weekday && minOf(x.e.start) < minOf(y.e.end)
          && minOf(y.e.start) < minOf(x.e.end)) hits.push({ x, y });
      }
    }
    return hits;
  }

  /** بلوک پرسش تعارض: کدام‌یک ضبط‌شده/غیرهم‌زمان است؟ */
  function setupConflictBlock() {
    const hits = setupConflicts();
    if (!hits.length) return '';
    const rows = hits.map(({ x, y }) => {
      const day = DAYS[x.e.weekday];
      const label = (it) => esc(it.e.title) + ' ' + esc(it.e.start) + '–' + esc(it.e.end);
      return `<li>${day}: ${label(x)} با ${label(y)} هم‌پوشانی دارد.</li>`;
    }).join('');
    const marks = hits.map(({ x, y }) =>
      `${actionBtn('«' + esc(x.e.title) + '» ضبط‌شده است', 'wizard-recorded:' + x.key + ':' + x.i)}
       ${actionBtn('«' + esc(y.e.title) + '» ضبط‌شده است', 'wizard-recorded:' + y.key + ':' + y.i)}`
    ).join('');
    return `<div class="advice warning"><span class="advice-mark">!</span><span>
      <strong>تعارض حل‌نشده.</strong> ${rows}<br>
      کدام‌یک ضبط‌شده/غیرهم‌زمان است؟ با علامت‌زدن آن، بازه آزاد می‌شود و برنامه
      قطعی ساخته می‌شود. تا حل این تعارض، پایان راه‌اندازی باز است.<br>${marks}</span></div>`;
  }

  function setupPage() {
    const o = state.onboarding.values || {}, step = num(state.onboarding.step),
      group = o.group || profileGroup(), catalog = window.K2_CATALOG || {},
      courses = catalog[group] || [];
    let body = '';
    if (step === 0) body = `<div class="form-grid">`
      + `<label>نام پروفایل<input data-flow="name" value="${esc(o.name || state.profile?.name || '')}" placeholder="اختیاری"></label>`
      + `<label>رشته<select data-flow="group"><option value="">انتخاب رشته</option>${Object.keys(catalog).map(g => `<option value="${esc(g)}" ${g === group ? 'selected' : ''}>${esc(g)}</option>`).join('')}</select></label>`
      + `<label>سال آزمون<input data-flow="year" value="${esc(o.year || state.profile?.year || '۱۴۰۶')}"></label>`
      + `<label>نام آزمون<input data-flow="examName" value="${esc(o.examName || state.profile?.examName || 'کنکور سراسری')}"></label>`
      + `<label>تاریخ آزمون<input type="date" data-flow="date" value="${esc(o.date || state.profile?.date || '')}"></label>`
      + `<label>وضعیت تاریخ<select data-flow="dateStatus"><option value="unknown">نامشخص</option><option value="official" ${o.dateStatus === 'official' ? 'selected' : ''}>رسمی با منبع</option><option value="estimated" ${o.dateStatus === 'estimated' ? 'selected' : ''}>تخمینی</option></select></label>`
      + `<label>منبع تاریخ<input data-flow="source" value="${esc(o.source || '')}" placeholder="در حالت «رسمی» لازم است"></label>`
      + `</div><p class="card-body">تاریخ رسمی ابلاغ نشده؛ خالی گذاشتن مجاز است و حدس زده نمی‌شود.</p>`;
    else if (step === 1) {
      if (!group) body = '<p class="card-body">ابتدا رشته را در گام قبل انتخاب کنید.</p>';
      else {
        const year = String(o.year || state.profile?.year || '').replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d));
        const share = year === '1406' ? window.K2_GROUP_WEIGHTS?.[group] : null;
        const shareNote = share
          ? `سهم بازنشرشدهٔ ۱۴۰۶: آزمون اختصاصی ${share.exam}٪ و سوابق ${share.transcript}٪. ضرایب تک‌درس سوابقه جدا و هنوز بارگذاری نشده‌اند.`
          : 'سهم کلی برای این سال/گروه در این پیش‌نمایش تأیید نشده است.';
        body = `<p class="card-body">${esc(shareNote)}</p>`
          + `<div class="button-row">${actionBtn('انتخاب همهٔ درس‌ها', 'select-all-courses')}${actionBtn('پاک‌کردن درس‌ها', 'clear-courses')}${actionBtn('انتخاب همهٔ کتاب‌ها', 'select-all-books')}${actionBtn('پاک‌کردن کتاب‌ها', 'clear-books')}</div>`
          + `<div class="setup-course-list">` + courses.map(c => {
            const key = group + '|' + c.name, sel = (o.subjects || []).includes(key);
            return `<article class="card catalog-course"><label class="course-select">`
              + `<input type="checkbox" data-course="${esc(key)}" ${sel ? 'checked' : ''}>`
              + `<strong>${esc(c.name)}</strong>`
              + `<span class="pill ${c.examCoefficient !== null ? 'info' : 'gray'}">${esc(c.type)}${c.examCoefficient !== null ? ' · ضریب آزمون ' + c.examCoefficient : ' · ضریب تک‌درس نامشخص'}</span>`
              + `</label><div class="book-list">` + c.books.map(b => {
                const bk = key + '|' + b.code, checked = (o.books || []).includes(bk);
                return `<label class="book-row"><input type="checkbox" data-book="${esc(bk)}" ${checked ? 'checked' : ''}><span>${esc(b.title)} · پایهٔ ${b.grade} · کد ${esc(b.code)}</span></label>`;
              }).join('') + `</div></article>`;
          }).join('') + `</div>`
          + `<div class="advice"><span class="advice-mark">i</span><span>دروس عمومی دفترچهٔ آزمون اختصاصی نیستند؛ اثر آن‌ها از مسیر سوابق تحصیلی است. منبع اعداد آزمون، بازنشر متن اطلاعیه است.</span></div>`;
      }
    }
    else if (step === 2) {
      body = `<p class="card-body">اگر کلاس کنکوری مؤسسه دارید، جلسه‌ها را وارد کنید. رویداد ضبط‌شده غیرهم‌زمان است و در همان بازه ظرفیت نمی‌گیرد.</p>`
        + `<div class="button-row"><label class="setup-inline"><input type="radio" name="attend" data-flow="attend" value="yes" ${o.attend === 'yes' ? 'checked' : ''}> کلاس دارم</label>`
        + `<label class="setup-inline"><input type="radio" name="attend" data-flow="attend" value="no" ${o.attend === 'no' ? 'checked' : ''}> کلاس ندارم</label></div>`
        + (o.attend === 'yes'
          ? `<div class="button-row">${actionBtn('＋ افزودن جلسه', 'wizard-add-class')}</div>`
            + ((o.classes || []).map((e, i) => `<div class="list-row"><span>${DAYS[e.weekday]} ${esc(e.start)}–${esc(e.end)} · ${esc(e.title)}${e.subjectName ? ' · ' + esc(e.subjectName) : ''}${e.recorded ? ' · ضبط‌شده' : ''}</span><span>${actionBtn('حذف', 'wizard-delete-class:' + i, 'danger')}</span></div>`).join('') || '<p class="card-body">جلسه‌ای ثبت نشده است.</p>')
          : '')
        + `<p class="card-body">رفت‌وآمد، آزمون آزمایشی و دیگر تعهدهای ثابت هفتگی:</p>`
        + `<div class="button-row">${actionBtn('＋ افزودن تعهد/آزمون', 'wizard-add-event')}</div>`
        + ((o.commitments || []).map((e, i) => `<div class="list-row"><span>${DAYS[e.weekday]} ${esc(e.start)}–${esc(e.end)} · ${esc(e.title)}${e.recorded ? ' · ضبط‌شده' : ''}</span><span>${actionBtn('حذف', 'wizard-delete-event:' + i, 'danger')}</span></div>`).join('') || '<p class="card-body">تعهدی ثبت نشده است.</p>')
        + setupConflictBlock();
    }
    else if (step === 3) {
      body = `<div class="form-grid">`
        + `<label>بیداری<input type="time" data-flow="wake" value="${esc(o.wake || state.settings.wake)}"></label>`
        + `<label>خواب<input type="time" data-flow="sleep" value="${esc(o.sleep || state.settings.sleep)}"></label>`
        + `<label>حداقل خواب مورد نظر (دقیقه)<input type="number" min="180" max="720" step="15" data-flow="sleepTarget" value="${esc(o.sleepTarget ?? num(state.settings.sleepTargetMinutes, 480))}"></label>`
        + `<label>انرژی<select data-flow="energy"><option value="1" ${num(o.energy, 2) === 1 ? 'selected' : ''}>کم</option><option value="2" ${num(o.energy, 2) === 2 ? 'selected' : ''}>متوسط</option><option value="3" ${num(o.energy, 2) === 3 ? 'selected' : ''}>خوب</option></select></label>`
        + `<label>ساعت‌های پربازده<input data-flow="peak" value="${esc(o.peak || '')}" placeholder="۱۶:۰۰–۱۸:۰۰"></label>`
        + `</div>`
        + `<p class="card-body">وعدهٔ غذا، استراحت، بهداشت/حمام یک‌روزدرمیان و رفت‌وآمد را با بازه و روزهای تکرار اضافه کنید؛ این بازه‌ها از ساعت مطالعه کم می‌شوند.</p>`
        + `<div class="button-row">${actionBtn('＋ افزودن روال', 'wizard-add-routine')}</div>`
        + ((o.routines || []).map((r, i) => `<div class="list-row"><span>${esc(r.title)} · ${esc(r.start)}–${esc(r.end)} · ${(r.days || []).map(d => DAYS[d]).join('، ')}</span><span>${actionBtn('حذف', 'wizard-delete-routine:' + i, 'danger')}</span></div>`).join('') || '<p class="card-body">روال اضافی ثبت نشده است.</p>');
    }
    else if (step === 4) {
      const s = ensureExamSeries();
      const on = s.enabled !== false;
      body = `<p class="card-body">آزمون جامع و تحلیل آن دو فعالیت مستقل‌اند. تاریخ رسمی ابلاغ نشده؛ بازه و تاریخ شروع را خودت تأیید کن. اگر نمی‌خواهی حالا ثبت کنی، این گام را رد کن.</p>`
        + `<div class="form-grid">`
        + `<label class="check-label"><input type="checkbox" data-flow="examEnabled" ${on ? 'checked' : ''}> چرخهٔ آزمون جامع فعال باشد</label>`
        + `<label>بازهٔ تکرار (روز)<input type="number" min="1" max="90" data-flow="examInterval" value="${Math.round(num(s.intervalDays, 14))}"></label>`
        + `<label>تاریخ اولین نوبت<input type="date" data-flow="examStart" value="${esc(s.startISO)}"></label>`
        + `<label>مدت خودِ آزمون (دقیقه)<input type="number" min="15" max="600" data-flow="examDuration" value="${Math.round(num(s.durationMinutes, 210))}"></label>`
        + `<label>مدت تحلیل (دقیقه)<input type="number" min="5" max="600" data-flow="examAnalysis" value="${Math.round(num(s.analysisMinutes, 60))}"></label>`
        + `<label>یادداشت منبع تاریخ<input data-flow="examNote" value="${esc(s.startNote || '')}" placeholder="مثلاً اطلاعیهٔ مرکز سنجش"></label>`
        + `</div>`
        + `<p class="card-body">معادل شمسی تاریخ انتخابی: <strong>${esc(jalaliLabel(s.startISO))}</strong>. اگر «۳۰ مهر» را داری، سال آن را از تقویم خودت تأیید کن؛ سال حدس زده نمی‌شود.</p>`;
    }
    else if (step === 5) {
      const topics = state.topics || [];
      const est = state.settings.estimateDefaults || {};
      // جدول سطح فقط وقتی ساخته می‌شود که مبحث واقعی وجود داشته باشد؛ هیچ
      // مبحثی از پیش ساخته نمی‌شود (D-023).
      const levelRows = topics.length
        ? `<div class="table-wrap"><table><thead><tr><th>مبحث</th><th>درس</th><th>سطح اولیه (۰ تا ۴)</th></tr></thead><tbody>`
          + topics.map(t => `<tr><td>${esc(t.name)}</td><td>${esc(t.subjectName || '—')}</td>`
            + `<td><select data-flow="topicLevel:${esc(t.id)}"><option value="">هنوز سنجش نشده</option>`
            + [0, 1, 2, 3, 4].map(v => `<option value="${v}" ${num(t.selfAssessed, -1) === v ? 'selected' : ''}>${v} از ۴</option>`).join('')
            + `</select></td></tr>`).join('') + `</tbody></table></div>`
        : `<p class="card-body">هنوز مبحثی ثبت نشده. مبحث/مهارت واقعی را در صفحهٔ «مباحث و تسلط» اضافه کن؛ این گام اختیاری است و بعداً تکمیل می‌شود.</p>`;
      body = `<p class="card-body">سطح در سطح <strong>مبحث</strong> ثبت می‌شود، نه یک برچسب کلی برای همهٔ درس. خودسنجی به‌تنهایی کافی نیست و اطمینان پایین می‌گیرد.</p>`
        + levelRows
        // این گام عمداً اختیاری است: پاسخ ندادن به آن راه‌اندازی را متوقف نمی‌کند.
        + `<div class="advice"><span class="advice-mark">i</span><span>این گام را می‌توانی رد کنی و بعداً در «مباحث و تسلط» تکمیل کنی؛ سطح هر مبحث جدا ذخیره می‌شود.</span></div>`
        + `<p class="card-body">طول معمول هر نوع کار را هم تعیین کن. این اعداد <strong>فرضیهٔ محافظه‌کارانه</strong> هستند و بعد از نمونه‌های واقعی‌ات کالیبره می‌شوند.</p>`
        + `<div class="form-grid">` + ESTIMATE_DEFAULT_KEYS.map(([k, label]) =>
          `<label>${label} (دقیقه)<input type="number" min="5" max="600" step="5" data-flow="est:${k}" value="${esc(est[k] ?? 30)}"></label>`).join('') + `</div>`;
    }
    else {
      body = `<div class="form-grid">`
        + `<label>اولویت‌بندی<select data-flow="priority"><option value="auto" ${o.priority !== 'personal' ? 'selected' : ''}>خودکار؛ ضریب آزمون تعدیل‌گر</option><option value="personal" ${o.priority === 'personal' ? 'selected' : ''}>فقط وزن شخصی</option></select></label>`
        + `<label>شدت تعدیل‌گر (۰٫۵ تا ۱٫۵)<input type="number" min="0.5" max="1.5" step="0.1" data-flow="coefficientFactor" value="${esc(o.coefficientFactor || 1)}"></label>`
        + `</div>`
        + `<article class="card"><h3 class="card-title">بازبینی پیش از ذخیره</h3><p class="card-body">`
        + `رشته: ${esc(group || '—')} · درس: ${(o.subjects || []).length} · کتاب: ${(o.books || []).length}<br>`
        + `کلاس: ${(o.attend === 'yes' ? (o.classes || []).length : 0)} · تعهد: ${(o.commitments || []).length} · روال: ${(o.routines || []).length}<br>`
        + `مبحث سنجش‌شده: ${Object.keys(o.topicLevels || {}).length} · حداقل خواب: ${esc(o.sleepTarget ?? num(state.settings.sleepTargetMinutes, 480))} دقیقه<br>`
        + `ضرایب سوابق تحصیلی حدس زده نمی‌شوند.</p></article>`
        + setupConflictBlock()
        + `<label class="check-label"><input type="checkbox" data-flow="confirm" ${o.confirm ? 'checked' : ''}> اطلاعات را بررسی کرده و ذخیره می‌کنم.</label>`;
    }
    const nav = `<div class="setup-actions">`
      + (step > 0 ? actionBtn('مرحلهٔ قبل', 'wizard-back') : '<span></span>')
      + (SETUP_OPTIONAL[step] ? actionBtn('رد کردن این گام', 'wizard-skip') : '<span></span>')
      + (step < SETUP_TOTAL - 1
        ? actionBtn('ذخیره و ادامه', 'wizard-next', 'primary')
        : actionBtn('ذخیره و ورود', 'wizard-finish', 'primary'))
      + `</div>`;
    return `<div class="page-scroll"><div class="setup-shell">`
       + `<div class="setup-head"><div><h2 class="page-heading">راه‌اندازی · گام ${faNum(step + 1)} از ${faNum(SETUP_TOTAL)}</h2>`
      + `<p class="page-intro">پیشرفت ذخیره می‌شود؛ هر وقت خواستی ادامه بده.</p></div>`
      + `${actionBtn('داشبورد', 'go-dashboard')}</div>`
      + `<div class="modal-progress"><i style="width:${(step + 1) / SETUP_TOTAL * 100}%"></i></div>`
      + `<article class="card setup-card"><h3 class="card-title">${SETUP_TITLES[step]}</h3>${body}${nav}</article>`
      + `</div></div>`;
  }

  function updateFlow(key, value) {
    const o = state.onboarding.values;
    // سطح اولیهٔ هر مبحث: در سطح مبحث ثبت می‌شود، نه برچسب کلی درس.
    if (key.startsWith('topicLevel:')) {
      const tid = key.split(':')[1];
      o.topicLevels = o.topicLevels || {};
      if (value === null || value === undefined || value === '') delete o.topicLevels[tid];
      else o.topicLevels[tid] = num(value);
      persist('');
      return;
    }
    // برآورد زمان هر نوع کار؛ فرضیهٔ محافظه‌کارانه و قابل کالیبراسیون.
    if (key.startsWith('est:')) {
      const kind = key.split(':')[1];
      o.estimates = o.estimates || {};
      const n = num(value, 0);
      if (n > 0) o.estimates[kind] = n; else delete o.estimates[kind];
      persist('');
      return;
    }
    if (key.startsWith('exam')) {
      // گام آزمون جامع: مقادیر روی state.examSeries ذخیره می‌شوند تا همان
      // چیزی باشد که صفحهٔ آزمون‌های جامع می‌خواند.
      const s2 = ensureExamSeries();
      if (key === 'examEnabled') s2.enabled = !!value;
      if (key === 'examInterval') s2.intervalDays = Math.max(1, Math.round(num(value, 14)));
      if (key === 'examStart') s2.startISO = String(value || '');
      if (key === 'examDuration') s2.durationMinutes = Math.max(15, Math.round(num(value, 210)));
      if (key === 'examAnalysis') s2.analysisMinutes = Math.max(5, Math.round(num(value, 60)));
      if (key === 'examNote') s2.startNote = String(value || '');
      persist('');
      return;
    }
    o[key] = value;
    persist('');
  }

  function pushWizardItem(type){if(type==='class'||type==='event'){dialog(type==='class'?'افزودن جلسهٔ کلاس':'افزودن آزمون/تعهد',`<form id="modalForm"><label>عنوان<input name="title" required></label><div class="form-grid"><label>نوع<select name="kind">${Object.entries(EVENT_KINDS).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></label>${weekdaySelect()}<label>درس<select name="subject">${subjectOptions()}</select></label>${timeInputs()}</div><div class="modal-actions"><button class="btn" type="button" data-action="close">انصراف</button><button class="btn primary" type="submit">افزودن</button></div></form>`);$('#modalForm').dataset.wizard=type;return}routineForm();$('#modalForm').dataset.wizard='routine'}
  function advanceWizard(finish = false) {
    const step = num(state.onboarding.step), o = state.onboarding.values;
    if (step === 0 && (!o.group || !o.year)) { notify('رشته و سال آزمون را انتخاب کنید'); return; }
    if (step === 1 && !(o.subjects || []).length) { notify('حداقل یک درس انتخاب کنید'); return; }
    if (step === 2 && !o.attend) { notify('پاسخ حضور در کلاس را مشخص کنید'); return; }
    if (step === 2 && o.attend === 'yes' && !(o.classes || []).length) {
      notify('گفتید کلاس دارید؛ دست‌کم یک جلسه وارد کنید'); return;
    }
    if (step === 4) {
      const s2 = ensureExamSeries();
      if (s2.enabled !== false && (!s2.startISO || s2.intervalDays < 1)) {
        notify('تاریخ اولین نوبت و بازهٔ تکرار را وارد کنید یا چرخه را خاموش کنید'); return;
      }
    }
    if (finish) {
      // تعارض حل‌نشده = برنامهٔ قطعی ساخته نمی‌شود (D-023: فقط رویداد واقعی).
      const conflicts = setupConflicts();
      if (conflicts.length) {
        notify('تعارض زمانی حل نشده؛ یکی را ضبط‌شده علامت بزنید یا زمان را اصلاح کنید');
        return;
      }
      if (!o.confirm) { notify('تأیید نهایی را علامت بزنید'); return; }
      const group = o.group, catalog = window.K2_CATALOG[group] || [];
      const normalizedYear = String(o.year || '').replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d));
      const contribution = normalizedYear === '1406' ? window.K2_GROUP_WEIGHTS?.[group] : null;
      const subjectMap = new Map(state.subjects.map(s => [`${s.group || state.profile?.group || ''}|${s.name}`, { ...s, selected: false }]));
      for (const k of (o.subjects || []).filter(x => x.startsWith(group + '|'))) {
        const [, name] = k.split('|'), c = catalog.find(x => x.name === name), key = `${group}|${name}`, old = subjectMap.get(key) || {};
        subjectMap.set(key, {
          id: old.id || id(), group, name, kind: c?.type || 'درس',
          examCoefficient: c?.examCoefficient ?? null, selected: true,
          personalWeight: old.personalWeight || 1,
          coefficientSource: 'گزارش بازنشرشدهٔ اطلاعیه'
        });
      }
      state.subjects = [...subjectMap.values()];
      const bookMap = new Map(state.books.map(b => [`${b.group}|${b.code}`, { ...b, selected: false }]));
      for (const k of (o.books || []).filter(x => x.startsWith(group + '|'))) {
        const [g, n, code] = k.split('|'), c = (window.K2_CATALOG[g] || []).find(x => x.name === n),
          b = c?.books.find(x => x.code === code), key = `${g}|${code}`, old = bookMap.get(key) || {};
        bookMap.set(key, {
          ...old, id: old.id || id(), group: g, subject: n,
          title: b?.title || old.title || '', code, grade: b?.grade || (old.grade ?? null), selected: true
        });
      }
      state.books = [...bookMap.values()];
      state.profile = {
        id: state.profile?.id || id(), name: o.name || 'آزمون هدف',
        examName: o.examName || 'کنکور سراسری', group, year: o.year,
        date: o.date || '', dateStatus: o.dateStatus || 'unknown', source: o.source || '',
        examShare: contribution?.exam ?? null, transcriptShare: contribution?.transcript ?? null,
        contributionSource: contribution?.source || 'not_loaded'
      };
      state.settings = {
        ...state.settings,
        wake: o.wake || state.settings.wake, sleep: o.sleep || state.settings.sleep,
        // حداقل خواب مورد نظر؛ خواب هرگز قربانی جبران عقب‌افتادگی نمی‌شود.
        sleepTargetMinutes: Math.max(180, Math.round(num(o.sleepTarget, num(state.settings.sleepTargetMinutes, 480)))),
        energy: num(o.energy, 2), peak: o.peak || '',
        useExamCoefficients: o.priority !== 'personal',
        coefficientFactor: Math.max(.5, Math.min(1.5, num(o.coefficientFactor, 1))),
        // برآورد زمان هر نوع کار؛ فرضیهٔ محافظه‌کارانه تا کالیبراسیون.
        estimateDefaults: {
          ...(state.settings.estimateDefaults || {}),
          ...(o.estimates || {})
        }
      };
      state.events = [...state.events.filter(e => !e.fromWizard),
        ...((o.attend === 'yes' ? o.classes : []) || []).map(e => ({ ...e, id: id(), fromWizard: true })),
        ...(o.commitments || []).map(e => ({ ...e, id: id(), fromWizard: true }))];
      state.events.forEach(e => {
        const s = state.subjects.find(x => x.id === e.subjectId || x.name === e.subjectId || x.name === e.subjectName);
        if (s) { e.subjectId = s.id; e.subjectName = s.name; }
      });
      state.routines = [...state.routines.filter(r => !r.fromWizard),
        ...(o.routines || []).map(r => ({ ...r, id: id(), fromWizard: true }))];
      // سطح اولیهٔ مبحث‌ها: خودسنجی جدا از شاهد عملکردی می‌ماند.
      const levels = o.topicLevels || {};
      for (const t of state.topics) {
        if (t.id in levels) t.selfAssessed = num(levels[t.id]);
      }
      state.onboarding.completed = true;
      state.profile.savedAt = new Date().toISOString();
      persist('راه‌اندازی ذخیره شد');
      currentPage = 'dashboard';
      render();
      return;
    }
    state.onboarding.step = Math.min(SETUP_TOTAL - 1, step + 1);
    persist('گام ذخیره شد');
    render();
  }


  const CONTENT_METHODS={
    memorization:['بازیابی فعال بدون نگاه‌کردن','پرسش‌سازی و پاسخ کوتاه','مرور فاصله‌دار بر مبنای عملکرد'],
    conceptual:['توضیح با زبان خود','مثال و ضد‌مثال','پرسش «چرا/چگونه؟» و آزمون انتقال'],
    calculational:['مثال حل‌شدهٔ درست','مثال نیمه‌کامل سپس حل مستقل','تمرین ترکیبی پس از یادگیری اولیه'],
    textual:['تحلیل متن و رابطهٔ گزاره‌ها','قاعده با مثال و پاسخ تشریحی کوتاه','بازیابی نکته از متن تازه'],
    vocabulary:['بازیابی واژه در هر دو جهت','کاربرد در جملهٔ تازه','درک مطلب زمان‌دار پس از دقت پایه'],
    diagram:['برچسب‌گذاری تصویر از حافظه','تمایز نمونه‌های نزدیک با بیان دلیل','تفسیر نمودار/تصویر تازه'],
    practical:['تمرین مهارتی کوتاه با خروجی قابل مشاهده','بازخورد با معیار روشن و سپس تلاش اصلاح‌شده','تمرین در چند نوبت جدا؛ زمان‌دار فقط پس از پایه']
  };
  const SPECIAL_METHODS={
    'درک عمومی هنر':['تصویر را بدون برچسب ببین؛ ویژگی و نشانه را از حافظه بازیابی کن','نمونه‌های نزدیک را مقایسه و دلیل تمایز را بگو','اثر تازه را با شواهد دیداری تشخیص بده'],
    'خلاقیت تصویری و تجسمی':['تمرین تولیدی کوتاه با خروجی قابل مشاهده','بازبینی هر خروجی با rubric/معیار روشن','یک اصلاح مشخص را در تلاش بعدی اجرا کن'],
    'زبان تخصصی':['واژگان را در هر دو جهت و در بافت جمله بازیابی کن','ساختار را در متن به کار ببر، نه فقط با بازخوانی قاعده','متن تازه را بخوان؛ خطای واژگان/استنباط را جدا تحلیل کن'],
    'درک عمومی ریاضی و فیزیک':['با مثال درست و مرحله‌به‌مرحله شروع کن','مثال نیمه‌حل‌شده را کامل و سپس سؤال مستقل حل کن','بعد از یادگیری اولیه، انواع نزدیک را ترکیب کن']
  };
  function assessTopic(topic){
    const ev=(state.learningEvidence||[]).filter(e=>e.topicId===topic.id&&e.source!=='self_report'),dates=[...new Set(ev.map(e=>e.date))].sort();
    const ordered=ev.slice().sort((a,b)=>String(a.date).localeCompare(String(b.date))),weights=ordered.map((_,i)=>1+.35*i),score=ordered.length?ordered.reduce((s,e,i)=>s+num(e.score)*weights[i],0)/weights.reduce((a,b)=>a+b,0):topic.selfAssessed==null?0:Math.max(0,Math.min(1,num(topic.selfAssessed)/4));
    let level=score<=.4?(score>0?1:0):score<=.7?2:score<=.85?3:4;const delayed=ev.some(e=>['delayed','review','delayed_exam'].includes(e.source)&&num(e.score)>=num(state.settings.masteryConfirmingScore,.8));const transfer=ev.some(e=>['transfer','mixed_exam','novel_item'].includes(e.source)&&num(e.score)>=num(state.settings.masteryConfirmingScore,.8));const span=dates.length>1?Math.round((Date.parse(dates.at(-1))-Date.parse(dates[0]))/86400000):0;const enough=dates.length>=Math.max(2,num(state.settings.masteryMinSpacedDays,2))&&span>=Math.max(1,num(state.settings.masteryMinSpacingDays,3));let reason='';if(level===4&&!(enough&&delayed&&transfer)){level=3;reason='برای وضعیت L4 هنوز بازیابی تأخیری، انتقال و/یا فاصلهٔ کافی بین جلسه‌ها لازم است.'}else if(level===4)reason='L4 عملکردی با شواهد فعلی تأیید شد؛ تضمین حافظه یا نمره نیست.';else if(!ev.length&&topic.selfAssessed!=null){level=Math.min(level,2);reason='تنها خودسنجی موجود است؛ اطمینان پایین و L4 مجاز نیست.'}else if(!ev.length)reason='هنوز شاهد عملکردی ثبت نشده است.';return{score,level,sessions:dates.length,delayed,transfer,reason};
  }
  function topicMethods(topic){const subject=String(topic.subjectName||'');const hit=Object.entries(SPECIAL_METHODS).find(([key])=>subject.includes(key));const generic=CONTENT_METHODS[topic.contentType]||CONTENT_METHODS.conceptual;return [...new Set([...(hit?hit[1]:[]),...generic.slice(0,2)])]}
  function masteryLabel(level){return ['L0 — نیازمند تشخیص','L1 — آغازین','L2 — در حال شکل‌گیری','L3 — عملکرد خوب؛ نیازمند پیگیری','L4 — شواهد عملکردی فعلی'][level]||'نامشخص'}
  function topicsPage(){const topics=state.topics||[];const selected=topics.find(t=>t.id===state.activeTopicId)||topics[0];if(selected)state.activeTopicId=selected.id;const rows=topics.map(t=>{const a=assessTopic(t),last=(state.learningEvidence||[]).filter(e=>e.topicId===t.id).at(-1);return `<tr data-topic-row="${esc(t.id)}" class="${selected?.id===t.id?'selected-row':''}"><td><button class="topic-select" type="button" data-action="select-topic:${esc(t.id)}">${esc(t.name)}</button></td><td>${esc(t.subjectName||'—')}</td><td>${esc(t.contentType||'conceptual')}</td><td>${masteryLabel(a.level)} · ${(a.score*100).toFixed(0)}٪</td><td>${a.sessions}</td><td>${last?esc(last.date)+' · '+esc(last.source):'بدون شاهد'}</td></tr>`}).join('');const methods=selected?topicMethods(selected).map(x=>`<li>${esc(x)}</li>`).join(''):'<li>مبحثی ثبت نشده است.</li>';const status=selected?assessTopic(selected):null;return `<div class="page-scroll">${pageHeader('مباحث و تسلط','روش مطالعه را با نوع هدف و عملکرد واقعی تنظیم کنید.',actionBtn('＋ افزودن مبحث','add-topic','primary'))}<div class="advice warning">نقشهٔ رسمی فصل‌های همهٔ گروه‌ها هنوز در این نسخه کامل راستی‌آزمایی نشده؛ مبحث واقعی را خودتان اضافه کنید. آستانه‌های L4 فرضیهٔ قابل تنظیم‌اند و تضمین تثبیت نیستند.</div>${syllabusOpen?syllabusDetail(syllabusOpen.subject,syllabusOpen.grade):syllabusOverview()}${topics.length?`<div class="table-wrap"><table><thead><tr><th>مبحث</th><th>درس</th><th>نوع</th><th>وضعیت</th><th>جلسه جدا</th><th>آخرین شاهد</th></tr></thead><tbody>${rows}</tbody></table></div><div class="button-row">${actionBtn('ثبت آزمون / بازیابی','add-topic-evidence','primary')}${actionBtn('ساخت مسیر پیشنهادی','generate-topic-pathway')}${actionBtn('تازه‌سازی','refresh-plan')}</div><article class="card"><h3 class="card-title">چرا این روش؟ · ${esc(selected?.name||'')}</h3><p class="card-body">${status?`${masteryLabel(status.level)} · اطمینان تنها برآوردی است، نه احتمال علمی.<br>${esc(status.reason)}<br>شواهد تأخیری: ${status.delayed?'بله':'خیر'} · انتقال/ترکیبی: ${status.transfer?'بله':'خیر'}`:''}</p><ul>${methods}</ul><p class="card-body">روش پیشنهادی آغازین است؛ پس از مشاهدهٔ پاسخ، زمان و نوع خطا باید بازتنظیم شود.</p></article>`:emptyState('هنوز مبحثی ثبت نشده','مبحث/مهارت واقعی را به یک درس وصل کنید؛ برنامه سرفصل تأییدنشده جعل نمی‌کند.',actionBtn('افزودن مبحث','add-topic','primary'))}</div>`}
  function addTopicForm(){const types={memorization:'حفظی/یادآوری',conceptual:'مفهومی',calculational:'محاسباتی',textual:'متنی/تشریحی',vocabulary:'واژگانی/زبان',diagram:'تصویری/نموداری',practical:'عملی/مهارتی'};dialog('افزودن مبحث یا مهارت',`<form id="modalForm"><label>عنوان خروجی قابل سنجش<input name="topicName" required placeholder="مثلاً حل معادله درجه‌دو"></label><div class="form-grid"><label>درس<select name="topicSubject">${subjectOptions(false)}</select></label><label>نوع محتوا<select name="contentType">${Object.entries(types).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></label><label>خودسنجی اختیاری<select name="selfAssessed"><option value="">هنوز خودسنجی نشده</option>${[0,1,2,3,4].map(v=>`<option value="${v}">${v} از ۴</option>`).join('')}</select></label><label>پیش‌نیاز/منبع<input name="topicNote" placeholder="اختیاری؛ فصل رسمی را حدس نزنید"></label></div><div class="modal-actions"><button class="btn" type="button" data-action="close">انصراف</button><button class="btn primary" type="submit">ذخیره</button></div></form>`);setModalType('topic')}
  function addTopicEvidenceForm(){const topic=state.topics.find(t=>t.id===state.activeTopicId)||state.topics[0];if(!topic){notify('ابتدا یک مبحث ثبت کنید');return}const sources={diagnostic:'تشخیصی',delayed:'بازیابی تأخیری',transfer:'سؤال تازه/انتقال',mixed_exam:'آزمون ترکیبی',review:'مرور فعال'};dialog(`ثبت شاهد عملکرد · ${esc(topic.name)}`,`<form id="modalForm"><div class="form-grid"><label>نوع سنجش<select name="evidenceSource">${Object.entries(sources).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></label><label>تاریخ سنجش<input type="date" name="evidenceDate" value="${todayISO()}" required></label><label>درصد درست<input type="number" name="evidenceScore" min="0" max="100" step="0.1" value="0" required></label><label>تعداد آیتم<input type="number" name="evidenceCount" min="0" max="500" value="0"></label><label>اطمینان پیش از بازخورد (۱–۴)<input type="number" name="evidenceConfidence" min="1" max="4" value="2"></label><label>مدت پاسخ (ثانیه)<input type="number" name="evidenceDuration" min="0" value="0"></label></div><label>منبع/یادداشت<input name="evidenceNote"></label><div class="modal-actions"><button class="btn" type="button" data-action="close">انصراف</button><button class="btn primary" type="submit">ذخیرهٔ شاهد</button></div></form>`);$('#modalForm').dataset.topicId=topic.id;setModalType('evidence')}
  function generateTopicPathway(){const topic=state.topics.find(t=>t.id===state.activeTopicId)||state.topics[0];if(!topic){notify('ابتدا مبحث ثبت کنید');return}const a=assessTopic(topic),level=a.level;const templates=level<=1?[['processing','پردازش/یادگیری اولیه',35],['guided_example','مثال هدایت‌شده',30],['independent_practice','تمرین مستقل',25]]:level===2?[['independent_practice','تمرین مستقل',30],['mixed_practice','تمرین ترکیبی',25],['review','بازیابی فاصله‌دار',15]]:level===3?[['mixed_practice','تمرین ترکیبی و انتقال',30],['timed_test','آزمون زمان‌دار',25],['review','بازیابی تأخیری',15]]:[['mixed_practice','تمرین ترکیبی نگهداری',25],['review','مرور نگهداری',15]];let created=0;for(const [type,label,minutes] of templates){const title=`${label} · ${topic.name}`;if(state.activities.some(x=>x.topicId===topic.id&&x.title===title&& !['done','dropped','expired'].includes(x.state)))continue;if(state.activities.some(x=>x.topicId===topic.id&&x.title===title&&x.state==='done'))continue;state.activities.unshift({id:id(),title,type,subjectId:topic.subjectId||'',subjectName:topic.subjectName||'',topicId:topic.id,topicName:topic.name,contentType:topic.contentType,estimate:minutes,remaining:minutes,minChunk:15,maxChunk:60,splittable:true,deadline:'none',state:'planned',personalWeight:1,origin:'advisor',reason:`بر پایهٔ ${masteryLabel(level)}؛ روش: ${topicMethods(topic)[0]}`});created++}if(created)saveAndRender(`${created} فعالیت پیشنهادی به برنامه اضافه شد`);else notify('فعالیت تکراری ساخته نشد؛ ابتدا سنجش تازه ثبت کنید یا فعالیت‌های موجود را بررسی کنید')}


  // ---- فرم‌های تازه: مهلت، جلسهٔ مطالعه، مشکل یادگیری ----
  function addDeadlineForm(){const topics=state.topics||[];if(!topics.length){notify('ابتدا در «بانک دروس» یک مبحث ثبت کنید');return}const list=topics.map(t=>`<option value="${esc(t.id)}">${esc(t.subjectName||'')} · ${esc(t.name)}</option>`).join('');dialog('ثبت مهلت مبحث',`<form id="modalForm"><div class="form-grid"><label>مبحث<select name="topicId">${list}</select></label><label>نوع مهلت<select name="kind">${Object.entries(DEADLINE_KINDS).map(([k,v])=>`<option value="${k}" ${k==='final_consolidation'?'selected':''}>${v}</option>`).join('')}</select></label><label>تاریخ مهلت<input type="date" name="date" value="${todayISO()}" required></label><label>هدف درصد (اختیاری)<input type="number" name="percent" min="0" max="100" placeholder="مثلاً ۷۰"></label><label>هدف سطح (اختیاری)<input type="number" name="level" min="0" max="4" placeholder="۰ تا ۴"></label><label>مسیر هدف<select name="track"><option value="konkur">کنکور (تستی)</option><option value="final">نهایی/مدرک</option></select></label><label class="check-label"><input type="checkbox" name="master"> مهلت مادرِ بازمحاسبه</label></div><label>یادداشت<input name="note" placeholder="اختیاری"></label><div class="modal-actions"><button class="btn" type="button" data-action="close">انصراف</button><button class="btn primary" type="submit">ذخیرهٔ مهلت</button></div></form>`);setModalType('deadline')}

  function addSessionForm(){const topics=state.topics||[];dialog('ثبت دستی ساعت مطالعه',`<form id="modalForm"><div class="form-grid"><label>نوع جلسه<select name="kind">${Object.entries(SESSION_KINDS).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></label><label>مبحث<select name="topicId"><option value="">— بدون مبحث —</option>${topics.map(t=>`<option value="${esc(t.id)}">${esc(t.name)}</option>`).join('')}</select></label><label>شروع<input type="datetime-local" name="startedAt" required></label><label>پایان<input type="datetime-local" name="endedAt" required></label><label>استراحت در این بازه (دقیقه)<input type="number" name="breakMinutes" min="0" max="600" value="0"></label></div><label>یادداشت<input name="note" placeholder="اختیاری"></label><div class="modal-actions"><button class="btn" type="button" data-action="close">انصراف</button><button class="btn primary" type="submit">ذخیرهٔ جلسه</button></div></form>`);setModalType('session')}

  function addProblemForm(){const topics=state.topics||[];dialog('ثبت مشکل یادگیری',`<form id="modalForm"><label>عنوان<input name="title" required placeholder="مثلاً در تست زمان‌دار هندسه گیر می‌کنم"></label><div class="form-grid"><label>نوع مشکل<select name="kind">${Object.entries(PROBLEM_KINDS).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></label><label>مبحث مرتبط<select name="topicId"><option value="">— بدون مبحث —</option>${topics.map(t=>`<option value="${esc(t.id)}">${esc(t.name)}</option>`).join('')}</select></label><label>شدت خودگزارشی ۱ تا ۵<input type="number" name="severity" min="1" max="5" value="3"></label><label>اولین ظهور<input type="date" name="firstSeen" value="${todayISO()}"></label></div><label>شرح<textarea name="description" placeholder="چه زمانی ظاهر می‌شود، در چه نوع سؤالی، چه کاری تا حالا کرده‌ای"></textarea></label><div class="modal-actions"><button class="btn" type="button" data-action="close">انصراف</button><button class="btn primary" type="submit">ذخیره</button></div></form>`);setModalType('problem')}

  function problemActionForm(problem){dialog('ثبت اقدام روی مشکل',`<form id="modalForm"><p class="card-body">${esc(problem.title)}</p><div class="form-grid"><label>وضعیت تازه<select name="status">${Object.entries(PROBLEM_STATUS).map(([k,v])=>`<option value="${k}" ${problem.status===k?'selected':''}>${v}</option>`).join('')}</select></label></div><label>چه کاری کردی و نتیجه چه بود<textarea name="note" required></textarea></label><div class="modal-actions"><button class="btn" type="button" data-action="close">انصراف</button><button class="btn primary" type="submit">ثبت اقدام</button></div></form>`);$('#modalForm').dataset.problemId=problem.id;setModalType('problemAction')}

  function nightlyReviewDialog(){const today=todayISO();const done=(state.activities||[]).filter(a=>a.state==='done');const incomplete=(state.activities||[]).filter(a=>a.state==='partial'||a.state==='overdue');const better=(state.activities||[]).filter(a=>a.state==='done'&&num(a.actual)>0&&num(a.actual)<num(a.estimate));const worse=(state.activities||[]).filter(a=>a.state==='done'&&num(a.actual)>num(a.estimate));const sess=sessionTotals(sessionsBetween(today,today));const plan=makePlan();const planned=plan.placements.reduce((n,x)=>n+x.minutes,0);const risks=(state.deadlines||[]).filter(d=>d.kind==='final_consolidation');const lines=[`امروز ${fmtMin(sess.total)} از ${fmtMin(planned)} دقیقهٔ برنامه اجرا شد (${planned?Math.round(sess.total/planned*100):0}٪).`,`از این تعداد، ${fmtMin(sess.cls)} کلاس و ${fmtMin(sess.independent)} مطالعهٔ مستقل بود.`];if(incomplete.length)lines.push('ناقص مانده: '+incomplete.slice(0,5).map(a=>a.title).join('؛ '));if(better.length)lines.push('بهتر از برآورد: '+better.slice(0,3).map(a=>a.title).join('؛ '));if(worse.length)lines.push('بدتر از برآورد: '+worse.slice(0,3).map(a=>a.title).join('؛ '));for(const d of risks.slice(0,4)){const t=(state.topics||[]).find(x=>x.id===d.topicId);const planD=t?backCalculate(t):null;if(planD&&!planD.feasible)lines.push(`ریسک مهلت: ${t.name} — برای رسیدن باید ${planD.lateDays} روز پیش‌تر شروع می‌شد.`)}lines.push('کلاس‌ها و تعهدهای ثابت دست‌نخورده می‌مانند؛ کار ناقص با سنجش اهمیت و فوریت بین روزهای باز توزیع می‌شود.');dialog('بازبینی و بازسازی شبانه',`<div class="advice"><span class="advice-mark">✓</span><span>${lines.map(esc).join('<br>')}</span></div><article class="card"><h3 class="card-title">چرا بازسازی، نه انتقال خودکار؟</h3><p class="card-body">انتقال کورکورانهٔ کار ناقص به فردا باعث انباشت می‌شود. ابتدا اهمیت و فوریت سنجیده می‌شود؛ اگر کار مهم نیست یا مهلتش رفته، تعویق یا حذف با دلیل ثبت می‌شود.</p></article><div class="modal-actions"><button class="btn" type="button" data-action="refresh-plan">بازسازی برنامه</button><button class="btn primary" type="button" data-action="close">بستن</button></div>`)}

  