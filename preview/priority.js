
  // ---- ماژول منبع و اطمینان در اولویت‌بندی ----
  // چرا لازم است: اولویت‌بندی روی چند عدد ساخته می‌شود. اگر منبع هر عدد
  // دیده نشود و اگر عددِ وارد‌نشده به‌جای «نامشخص» صفر نمایش داده شود،
  // برنامه بر پایهٔ عددی که کسی نگفته برنامه‌ریزی می‌شود.
  //
  // قاعدهٔ صداقت این ماژول:
  //   ۱) «نامشخص» هرگز به صفر تبدیل نمی‌شود؛ صفر یک ادعاست، نه فقدان داده.
  //   ۲) منبع هر عدد قابل دیدن است: رسمی، سوابق، محاسباتی، یا نظر خودتان.
  //   ۳) اطمینان جدا از منبع است؛ منبع رسمی به‌تنهایی اطمینان بالا نمی‌سازد.
  //   ۴) کاربر می‌تواند هر عدد را بازنویسی کند و بازنویسی هم علامت می‌خورد.

  const PRIORITY_SOURCES = {
    official: 'اطلاعیه رسمی',
    historical: 'سوابق آزمون',
    algorithmic: 'محاسباتی از دادهٔ ثبت‌شدهٔ خودت',
    personal: 'نظر یا برآورد خودت',
    unknown: 'بدون منبع'
  };
  const CONFIDENCE_LABELS = {
    high: 'اطمینان بالا',
    medium: 'اطمینان متوسط',
    low: 'اطمینان پایین',
    none: 'بدون اطمینان'
  };
  // ترتیب نمایش برای انتخابگر
  const PRIORITY_SOURCE_ORDER = ['official', 'historical', 'algorithmic', 'personal', 'unknown'];
  const CONFIDENCE_ORDER = ['high', 'medium', 'low', 'none'];

  // فاکتورهای اولویت که منبع و اطمینان دارند
  const PRIORITY_FACTORS = [
    { key: 'estimatedMinutes', label: 'برآورد زمان', unit: 'دقیقه' },
    { key: 'prerequisiteShare', label: 'پیش‌نیاز بودن', unit: '۰ تا ۱' },
    { key: 'finalExamShare', label: 'سهم آزمون نهایی', unit: '۰ تا ۱' }
  ];

  function ensureFactorMeta(topic) {
    if (!topic) return {};
    if (!topic.factorMeta || typeof topic.factorMeta !== 'object') topic.factorMeta = {};
    return topic.factorMeta;
  }

  // وضعیت یک فاکتور: مقدار (یا null اگر نامشخص)، منبع، اطمینان، بازنویسی
  function topicFactor(topic, key) {
    const meta = ensureFactorMeta(topic)[key] || {};
    const raw = topic ? topic[key] : undefined;
    const known = raw !== undefined && raw !== null && raw !== '';
    return {
      key,
      known,
      value: known ? num(raw) : null,
      source: meta.source || (known ? 'personal' : 'unknown'),
      confidence: meta.confidence || (known ? 'low' : 'none'),
      overridden: meta.overridden === true,
      note: meta.note || ''
    };
  }

  function factorValueText(f) {
    if (!f || !f.known) return 'نامشخص';
    if (f.key === 'estimatedMinutes') return fmtMin(f.value);
    return num(f.value).toFixed(1);
  }

  // نشان منبع: رسمی و سوابق متمایز، محاسباتی و نظر شخصی هم متمایز
  function factorSourceBadge(f) {
    if (!f || !f.known) return '<span class="pill warn" title="عدد وارد نشده؛ صفر فرض نشده است">نامشخص</span>';
    const cls = f.source === 'official' ? 'ok' : f.source === 'historical' ? 'ok'
      : f.source === 'algorithmic' ? 'info' : f.source === 'personal' ? '' : 'warn';
    const text = PRIORITY_SOURCES[f.source] || PRIORITY_SOURCES.unknown;
    const ov = f.overridden ? ' · بازنویسی‌شده' : '';
    return `<span class="pill ${cls}" title="منبع: ${esc(text)}${ov ? ' · ' + esc(ov.trim()) : ''}">${esc(text)}${esc(ov)}</span>`;
  }

  function factorConfidenceBadge(f) {
    if (!f || !f.known) return '<span class="pill warn">بدون اطمینان</span>';
    const cls = f.confidence === 'high' ? 'ok' : f.confidence === 'medium' ? 'info'
      : f.confidence === 'low' ? 'warn' : 'warn';
    return `<span class="pill ${cls}">${esc(CONFIDENCE_LABELS[f.confidence] || CONFIDENCE_LABELS.none)}</span>`;
  }

  // ستون‌های منبع و اطمینان برای جدول بانک دروس
  function factorCells(topic) {
    const pre = topicFactor(topic, 'prerequisiteShare');
    const fin = topicFactor(topic, 'finalExamShare');
    return `<td>${factorValueText(pre)}</td><td>${factorSourceBadge(pre)} ${factorConfidenceBadge(pre)}</td><td>${factorValueText(fin)}</td><td>${factorSourceBadge(fin)} ${factorConfidenceBadge(fin)}</td>`;
  }

  // کارت توضیح منبع‌ها بالای جدول: تا کاربر بداند هر برچسب یعنی چه
  function prioritySourcesCard() {
    const rows = PRIORITY_SOURCE_ORDER.map(k => {
      const desc = {
        official: 'عدد از اطلاعیهٔ سازمان سنجش آمده. پرچم‌واره: قابل استناد، ولی برای سال آزمون خودت بازبینی کن.',
        historical: 'از سوابق آزمون‌های گذشته استخراج شده. نسبت به امسال ممکن است جابه‌جا باشد.',
        algorithmic: 'از داده‌ای که خودت وارد کرده‌ای محاسبه شده (مثلاً شواهد عملکرد). ورودی‌اش را می‌بینی.',
        personal: 'نظر یا برآورد خودت است. گاهی تنها منبع موجود است و اشکالی ندارد؛ فقط باید علامت بخورد.',
        unknown: 'منبعی ثبت نشده. عدد نمایش داده نمی‌شود؛ «نامشخص» می‌ماند تا صفرِ جعلی ساخته نشود.'
      }[k];
      return `<tr><td>${esc(PRIORITY_SOURCES[k])}</td><td>${esc(desc)}</td></tr>`;
    }).join('');
    return `<article class="card tone-study"><div class="section-row"><h3 class="card-title">منبع هر عدد کجا می‌آید؟</h3>${actionBtn('فاکتورهای اولویت', 'topic-fields')}</div><p class="card-body">هر عدد اولویت دو برچسب جدا دارد: <strong>منبع</strong> و <strong>اطمینان</strong>. منبع رسمی به‌تنهایی اطمینان بالا نیست؛ اطمینان یعنی چقدر به این عدد برای سال آزمون خودت اعتماد داری. عدد وارد‌نشده «نامشخص» می‌ماند و هرگز به صفر تبدیل نمی‌شود، چون صفر یک ادعاست.</p><div class="table-wrap"><table><thead><tr><th>منبع</th><th>معنا</th></tr></thead><tbody>${rows}</tbody></table></div><div class="advice"><span class="advice-mark">i</span><span>اگر عددی را خودت عوض کردی، برچسب «بازنویسی‌شده» می‌خورد تا در گزارش بعدی مشخص باشد چه چیزی از منبع آمده و چه چیزی نظر توست.</span></div></article>`;
  }

  function priorityFactorForm(topic) {
    topic = topic || (state.topics || [])[0];
    if (!topic) { notify('ابتدا یک مبحث ثبت کنید'); return; }
    const rows = PRIORITY_FACTORS.map(f => {
      const st = topicFactor(topic, f.key);
      const val = st.known ? (f.key === 'estimatedMinutes' ? Math.round(st.value) : num(st.value)) : '';
      const src = PRIORITY_SOURCE_ORDER.map(k => `<option value="${k}" ${st.source === k ? 'selected' : ''}>${esc(PRIORITY_SOURCES[k])}</option>`).join('');
      const conf = CONFIDENCE_ORDER.map(k => `<option value="${k}" ${st.confidence === k ? 'selected' : ''}>${esc(CONFIDENCE_LABELS[k])}</option>`).join('');
      return `<tr><td>${esc(f.label)}<br><span class="card-body">${esc(f.unit)}</span></td>`
        + `<td><input type="number" name="val_${esc(f.key)}" ${f.key === 'estimatedMinutes' ? 'min="0" step="15"' : 'min="0" max="1" step="0.1"'} value="${val}" placeholder="نامشخص"></td>`
        + `<td><select name="src_${esc(f.key)}">${src}</select></td>`
        + `<td><select name="conf_${esc(f.key)}">${conf}</select></td>`
        + `<td>${esc(st.known ? factorValueText(st) : 'نامشخص')}</td></tr>`;
    }).join('');
    const list = (state.topics || []).map(t => `<option value="${esc(t.id)}" ${t.id === topic.id ? 'selected' : ''}>${esc(t.subjectName || '')} · ${esc(t.name)}</option>`).join('');
    dialog('فاکتورهای اولویت و منبع آن‌ها', `<form id="modalForm"><div class="form-grid"><label>مبحث<select name="topicId">${list}</select></label></div><div class="table-wrap"><table><thead><tr><th>فاکتور</th><th>مقدار (خالی = نامشخص)</th><th>منبع</th><th>اطمینان</th><th>فعلی</th></tr></thead><tbody>${rows}</tbody></table></div><p class="card-body">خالی گذاشتن یک مقدار یعنی «نمی‌دانم». برنامه آن را صفر حساب نمی‌کند؛ «نامشخص» می‌ماند و در گزارش می‌بینید. منبع و اطمینان را هم برای خودتان ثبت کنید تا شش ماه بعد بدانید این عدد از کجا آمده.</p><div class="modal-actions"><button class="btn" type="button" data-action="close">انصراف</button><button class="btn primary" type="submit">ذخیرهٔ فاکتورها</button></div></form>`);
    setModalType('priorityFactors');
  }

  function submitPriorityFactors(form) {
    const d = new FormData(form), v = n => d.get(n);
    const topic = (state.topics || []).find(x => x.id === String(v('topicId') || ''));
    if (!topic) { notify('مبحث را انتخاب کنید'); return; }
    const meta = ensureFactorMeta(topic);
    for (const f of PRIORITY_FACTORS) {
      const raw = v('val_' + f.key);
      const known = raw !== null && raw !== undefined && String(raw).trim() !== '';
      if (known) {
        let n = num(raw);
        n = f.key === 'estimatedMinutes' ? Math.max(0, Math.round(n)) : Math.max(0, Math.min(1, n));
        const prev = topicFactor(topic, f.key);
        const source = String(v('src_' + f.key) || 'personal');
        const confidence = String(v('conf_' + f.key) || 'low');
        meta[f.key] = {
          source, confidence,
          // بازنویسی یعنی عدد با منبع قبلی یکی نبوده
          overridden: prev.known && prev.value !== n,
          note: meta[f.key]?.note || ''
        };
        topic[f.key] = n;
      } else {
        // نامشخص: عدد حذف می‌شود، نه صفر شدن. سابقهٔ منبع می‌ماند.
        topic[f.key] = null;
        meta[f.key] = { ...(meta[f.key] || {}), source: 'unknown', confidence: 'none', overridden: false };
      }
    }
    closeDialog();
    saveAndRender('فاکتورهای اولویت با منبع و اطمینان ذخیره شد');
  }
