"""پایگاه شواهد علمی یادگیری — مرجع تصمیم‌های موتور مشاور.

این ماژول «تحقیق جامع» منابع روان‌شناسی یادگیری و حافظه را در قالب یک
کاتالوگ ساختاریافته نگه می‌دارد. هر قاعدهٔ محصول در موتورهای K2 می‌تواند به
یک یا چند شناسهٔ evidence ارجاع دهد تا «چرا» هر تصمیم قابل ردیابی باشد.

قاعدهٔ محصول: اینجا **هیچ عدد الگوریتمی به‌عنوان حقیقت علمی** ثبت نمی‌شود.
اعداد اثر (effect size) یافتهٔ پژوهش‌های یادشده، اما آستانه‌ها و ضرایب
پختصاصی K2 فرضیهٔ محصول [H] هستند و در تنظیمات قابل تغییرند.

منابع اصلی مرورشده (کامل‌شدن این فهرست در docs/research مستند شده است):
  * Cepeda et al. 2006/2008 — اثر فاصله‌گذاری (spacing) و قاعدهٔ ۱۰–۲۰٪
  * Roediger & Karpicke 2006؛ Karpicke & Roediger 2006/2008 — اثر آزمون/بازیابی فعال
  * Karpicke 2012/2025 — مرور بازیابی‌محور؛ اندازهٔ اثر g≈۰٫۵۰
  * Taylor & Rohrer 2010؛ Rohrer et al. 2015/2020 — تمرین درهم‌آمیخته (interleaving)
  * Sweller & Cooper 1985؛ Renkl & Atkinson 2003؛ Kalyuga et al. 2003 —
    مثال حل‌شده، محو تدریجی راهنما (fading) و اثر وارونگی تخصص
  * Bjork & Bjork 1992/1994 — نظریهٔ نوین بی‌استفاده‌سازی و دشواری‌های مطلوب
  * Dudai 2004/2012؛ Diekelmann & Born 2010 — تثبیت حافظه و نقش خواب SWS
  * Wozniak — مدل DSR و FSRS (open-spaced-repetition) — پایداری/بازیابی‌پذیری
  * Butterfield & Metcalfe 2001؛ Eich, Stern & Metcalfe 2012 — اثر فراصلاح
    (hypercorrection) و بازگشت خطاهای پرشدهقانی
  * Cepeda et al. 2009؛ Pashler et al. 2007 — بهینه‌سازی تمرین توزیع‌شده
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Evidence:
    """یک شاهد علمی با شناسهٔ پایدار و پیامد طراحی برای K2."""

    id: str
    title: str
    authors: str
    year: int
    finding: str
    effect: str
    url: str
    design_rule: str
    #: آیا این شاهد در قالب «قاعدهٔ محاسباتی» در موتورها استفاده شده است؟
    used_in_engine: bool = False


EVIDENCE: dict[str, Evidence] = {
    e.id: e
    for e in (
        Evidence(
            id="SPACING-01",
            title="Distributed Practice in Verbal Recall Tasks: A Review and Quantitative Synthesis",
            authors="Cepeda, Pashler, Vul, Wixted & Rohrer",
            year=2006,
            finding=(
                "مرور ۸۳۹ برآورد اندازهٔ اثر از ۳۱۷ آزمایش: مطالعهٔ توزیع‌شده "
                "(فاصله‌دار) به‌طور مستمر از مطالعهٔ متمرکز (cramming) بهتر است؛ "
                "فاصلهٔ بهینه با بازهٔ نگهداشت افزایش می‌یابد."
            ),
            effect="۸۳۹ برآورد اثر از ۳۱۷ آزمایش",
            url="https://journals.sagepub.com/doi/10.1037/0033-2909.132.3.354",
            design_rule=(
                "هرگز همهٔ مرورهای یک مبحث را در یک روز متمرکز نکن؛ فاصله‌ها "
                "با فاصله تا آزمون مقیاس شوند."
            ),
            used_in_engine=True,
        ),
        Evidence(
            id="SPACING-02",
            title="Spacing Effects in Learning: A Temporal Ridgeline of Optimal Retention",
            authors="Cepeda, Vul, Rohrer, Wixted & Pashler",
            year=2008,
            finding=(
                "با ۱٬۳۵۴ شرکت‌کننده، فاصلهٔ بهینهٔ بین دو جلسهٔ مطالعه حدود "
                "۱۰–۲۰٪ بازهٔ نگهداشت است؛ نسبت به فاصلهٔ صفر، بازدهی بازیابی "
                "۶۴٪ بیشتر شد."
            ),
            effect="d≈۱٫۱ (بازیابی) و d≈۱٫۵ (تشخیص) در فاصلهٔ بهینه",
            url="https://journals.sagepub.com/doi/10.1111/j.1467-9280.2008.02209.x",
            design_rule=(
                "فاصلهٔ مرور بعدی = ضریبِ قابل‌تنظیم × روزهای باقی‌مانده تا آزمون "
                "(پیش‌فرض ۱۵٪، بازهٔ ۱۰–۲۰٪ شواهدی)."
            ),
            used_in_engine=True,
        ),
        Evidence(
            id="TESTING-01",
            title="Test-Enhanced Learning: Taking Memory Tests Improves Long-Term Retention",
            authors="Roediger & Karpicke",
            year=2006,
            finding=(
                "در آزمون‌های تأخیری (۲ روز تا ۱ هفته)، آزمون دادن پیش از "
                "آزمون نهایی یادگیری را بیشتر از مطالعهٔ مجدد تقویت می‌کند، "
                "حتی وقتی مطالعهٔ مجدد اعتمادبه‌نفس را بیشتر می‌کند."
            ),
            effect="د: ۰٫۵ تا ۰٫۹۵ در آزمون‌های تأخیری",
            url="https://journals.sagepub.com/doi/10.1111/j.1467-9280.2006.01693.x",
            design_rule=(
                "«تثبیت» یعنی بازیابی فعال بدون نگاه به منبع، نه بازخوانی؛ "
                "بازخوانی فقط وقتی مفید است که بلافاصله آزمون گرفته شود."
            ),
            used_in_engine=True,
        ),
        Evidence(
            id="TESTING-02",
            title="Repeated Retrieval During Learning Is the Key to Long-Term Retention",
            authors="Karpicke & Roediger",
            year=2006,
            finding=(
                "مرور مجدد مواردی که یک بار بازیابی شده‌اند فایده‌ای ندارد، اما "
                "بازیابی فعالِ پیاپی، ماندگاری را بیش از ۱۰۰٪ بهبود می‌بخشد."
            ),
            effect="+۱۰۰٪ تا +۴۰۰٪ نسبت به یک‌بار مطالعه",
            url="https://www.science.org/doi/10.1126/science.1152408",
            design_rule=(
                "یک بار «درست خواندن» کافی نیست؛ تا رسیدن به فاز نگهداری، "
                "بازیابی فعال تکرار شود."
            ),
            used_in_engine=True,
        ),
        Evidence(
            id="TESTING-03",
            title="Retrieval-Based Learning: A Decade of Progress",
            authors="Karpicke",
            year=2025,
            finding=(
                "در ۱۵۹ مطالعه، اندازهٔ اثر ترکیبی تمرین بازیابی نسبت به "
                "مطالعهٔ مجدد g≈۰٫۵۰ است و ۸۱٪ مقایسه‌ها به نفع بازیابی است."
            ),
            effect="g≈۰٫۵۰ (۱۵۹ مطالعه)",
            url="https://learninglab.psych.purdue.edu/downloads/2025/2025_Karpicke_Retrieval_Based_Learning_Review.pdf",
            design_rule=(
                "حتی وقتی زمان کم است، تبدیل مطالعهٔ مجدد به آزمون/بازیابی "
                "اولویت دارد."
            ),
            used_in_engine=True,
        ),
        Evidence(
            id="INTERLEAVE-01",
            title="The Effects of Interleaved Practice",
            authors="Taylor & Rohrer",
            year=2010,
            finding=(
                "تمرین درهم‌آمیختهٔ چهار نوع مسئله، عملکرد تمرین را کاهش داد "
                "اما نمرهٔ آزمون یک‌روز بعد را دو برابر کرد؛ مکانیزم: توانایی "
                "جفت‌کردن هر سؤال با روش مناسب."
            ),
            effect="d≈۱٫۲۱ (۷۷٪ مقابل ۳۸٪)",
            url="https://onlinelibrary.wiley.com/doi/abs/10.1002/acp.1598",
            design_rule=(
                "پس از یادگیری اولیه، سؤال‌های هم‌تیپ و هم‌سطح را درهم‌آمیخته "
                "تمرین شود؛ افت عملکرد حین تمرین هشدار نیست بلکه نشانهٔ یادگیری."
            ),
            used_in_engine=True,
        ),
        Evidence(
            id="INTERLEAVE-02",
            title="A Randomized Controlled Trial of Interleaved Mathematics Practice",
            authors="Rohrer, Dedrick, Hartwig & Cheung",
            year=2020,
            finding=(
                "در ۵۴ کلاس واقعی، تمرین درهم‌آمیخته طی یک نیم‌سال، نمرهٔ "
                "آزمون یک‌ماههٔ بعد را از ۳۸٪ به ۶۱٪ رساند."
            ),
            effect="d≈۰٫۸۳ (۵۴ کلاس)",
            url="https://psycnet.apa.org/doi/10.1037/edu0000467",
            design_rule=(
                "در فازهای تشدید و جمع‌بندی، «تمرین مخلوط» جای «تمرین بلوکی» "
                "را می‌گیرد."
            ),
            used_in_engine=True,
        ),
        Evidence(
            id="WORKED-EX-01",
            title="The Worked-Example Effect",
            authors="Sweller & Cooper",
            year=1985,
            finding=(
                "مطالعهٔ مثال حل‌شده برای مبتدی‌ها بهتر از حل مستقیم مسئله است؛ "
                "بار شناختی جستجوی راه‌حل حذف می‌شود."
            ),
            effect="اثر پایدار و پرتکرار",
            url="https://en.wikipedia.org/wiki/Worked-example_effect",
            design_rule=(
                "مبحث تازه (سطح L0/L1) همیشه با مثال حل‌شده کامل آغاز شود، "
                "نه با مسئلهٔ سرد."
            ),
            used_in_engine=True,
        ),
        Evidence(
            id="WORKED-EX-02",
            title="The Guidance Fading Effect / How Fading Worked Solution Steps Works",
            authors="Renkl & Atkinson؛ Kalyuga et al.",
            year=2003,
            finding=(
                "حذف تدریجی گام‌های حل‌شده (به‌ویژه از گام‌های آخر) بهتر از "
                "حذف یک‌باره است؛ با افزایش تخصص، راهنمای ثابت به بار اضافی "
                "تبدیل می‌شود (اثر وارونگی تخصص)."
            ),
            effect="fading بهتر از switching ناگهانی",
            url="https://link.springer.com/article/10.1007/s10648-019-09465-5",
            design_rule=(
                "مسیر مبحث: مثال کامل → مثال نیمه‌کامل → تمرین مستقل؛ سرعت "
                "این گذار بر پایهٔ عملکرد واقعی، نه بر پایهٔ تقویم ثابت."
            ),
            used_in_engine=True,
        ),
        Evidence(
            id="EXPERTISE-01",
            title="The Expertise Reversal Effect",
            authors="Kalyuga, Ayres, Chandler & Sweller",
            year=2003,
            finding=(
                "روش‌هایی که به مبتدی کمک می‌کنند با افزایش تخصص بی‌اثر و حتی "
                "مخرب می‌شوند؛ مثلاً مثال حل‌شده برای فرد مسلط افزونه می‌شود."
            ),
            effect="متاآنالیز ۲۰۲۵: d≈۰٫۵ به نفع راهنمای زیاد برای مبتدی و d≈−۰٫۴۳ برای متخصص",
            url="https://en.wikipedia.org/wiki/Expertise_reversal_effect",
            design_rule=(
                "ماتریس تجویز فاز×سطح: سطح بالاتر هرگز با همان فعالیت سطح "
                "پایین تکرار نمی‌شود."
            ),
            used_in_engine=True,
        ),
        Evidence(
            id="CONSOL-01",
            title="The neurobiology of consolidations, or, how stable is the engram?",
            authors="Dudai",
            year=2004,
            finding=(
                "تثبیت دوسطحی: تثبیت سیناپسی (دقایق تا چند ساعت) و تثبیت "
                "سیستمی (هفته‌ها تا بیشتر) که در آن حافظهٔ وابسته به هیپوکامپ "
                "به شبکه‌های قشری منتقل می‌شود."
            ),
            effect="چارچوب نظری",
            url="https://www.annualreviews.org/doi/10.1146/annurev.psych.55.090902.142050",
            design_rule=(
                "«تثبیت» در K2 یک فرآیند چندمرحله‌ای است، نه یک رویداد؛ "
                "نردبان تثبیت دقیقاً همین زمان‌بندی را مدل می‌کند."
            ),
            used_in_engine=True,
        ),
        Evidence(
            id="CONSOL-02",
            title="System consolidation of memory during sleep",
            authors="Diekelmann & Born",
            year=2010,
            finding=(
                "تثبیت سیستمِ فعال در خواب عمیق (SWS): بازپخش هیپوکامپی و "
                "انتقال تدریجی نشانه‌ها به نئوکورتکس؛ خواب پس از یادگیری "
                "ماندگاری حافظهٔ اعلامی را بهتر می‌کند."
            ),
            effect="چندین متاآنالیز مثبت",
            url="https://link.springer.com/article/10.1007/s00426-011-0335-6",
            design_rule=(
                "بازیابی اولیهٔ یک مبحث تازه در کمتر از ۲۴ ساعت (پس از یک "
                "شب خواب) برنامه‌ریزی شود؛ شب‌بیداریِ پیش از آزمون جبران "
                "تثبیت انجام‌شده نیست."
            ),
            used_in_engine=True,
        ),
        Evidence(
            id="DD-01",
            title="A New Theory of Disuse / Desirable Difficulties",
            authors="Bjork & Bjork",
            year=1992,
            finding=(
                "دو «قدرت» مجزا: قدرت ذخیره‌سازی و قدرت بازیابی "
                ". بازیابی موفق در وضعیت بازیابیِ پایین‌تر، رشد "
                "بیشتری در قدرت ذخیره می‌دهد؛ پس «فراموشیِ جزئی» پیش از مرور "
                "مطلوب است."
            ),
            effect="چارچوب نظری توضیح‌دهندهٔ spacing/testing/interleaving",
            url="https://bjorklab.psych.ucla.edu/research/",
            design_rule=(
                "مرور وقتی ارزش دارد که چیزی از آن فراموش شده باشد؛ فاصله‌ها "
                "را آنقدر باز کن که بازیابی سخت (نه ناممکن) باشد."
            ),
            used_in_engine=True,
        ),
        Evidence(
            id="DSR-01",
            title="FSRS: DSR memory model (difficulty, stability, retrievability)",
            authors="Wozniak (DSR)؛ Ye & جامعهٔ FSRS",
            year=2022,
            finding=(
                "بازیابی‌پذیری R(t,S)=(1+19t/81S)^−۰٫۵؛ S = روزهایی که طول "
                "می‌کشد R به ۹۰٪ برسد؛ هر مرور موفق S را ضربی افزایش می‌دهد و "
                "مرور در وضعیت فراموشیِ بیشتر، رشد بیشتری می‌دهد."
            ),
            effect="۲۰–۲۱ پارامتر برازش‌شده روی دادهٔ واقعی کاربران",
            url="https://github.com/open-spaced-repetition/free-spaced-repetition-scheduler",
            design_rule=(
                "هر مبحث/آیتم مرور در K2 سه عدد دارد: سختی، پایداری، "
                "بازیابی‌پذیری؛ موعد بعدی از هدف بازیابی (پیش‌فرض ۹۰٪) محاسبه "
                "می‌شود، نه از الگوی ثابت ۱/۳/۷."
            ),
            used_in_engine=True,
        ),
        Evidence(
            id="HYPER-01",
            title="The correction of errors committed with high confidence (Hypercorrection)",
            authors="Butterfield & Metcalfe",
            year=2001,
            finding=(
                "خطاهایی که با اطمینان بالا مرتکب شده‌اند، پس از بازخورد "
                "تصحیحی بهتر از خطاهای کم‌اطمینان تصحیح می‌شوند؛ نکتهٔ کلیدی: "
                "بازخورد تصحیحی حتماً باید بیاید."
            ),
            effect="هماهنگ در آزمون‌های فوری و تأخیری",
            url="https://link.springer.com/article/10.1007/s11409-006-6894-z",
            design_rule=(
                "پس از هر آزمون، خطاهای پرشدهقانی اولویت‌دار تصحیح و دوباره "
                "آزمون شوند؛ بانک خطا خالی نمی‌ماند."
            ),
            used_in_engine=True,
        ),
        Evidence(
            id="HYPER-02",
            title="The hypercorrection effect persists over a week, but high-confidence errors return",
            authors="Eich, Stern & Metcalfe",
            year=2012,
            finding=(
                "خطاهای پرشدهقانی تصحیح‌شده اگر بدون آزمون مجدد باقی بمانند، "
                "بازمی‌گردند؛ آزمون مجدد پس از تصحیح، بازگشت را متوقف می‌کند."
            ),
            effect="تصحیح ۸۶٪ → ۵۶٪ پس از یک هفته بدون آزمون مجدد",
            url="https://link.springer.com/article/10.3758/s13423-011-0173-y",
            design_rule=(
                "هر خطای تصحیح‌شده یک «مرور تأخیریِ الزامی» می‌سازد؛ تا وقتی "
                "آن مرور انجام نشود، خطا بسته حساب نمی‌شود."
            ),
            used_in_engine=True,
        ),
        Evidence(
            id="FEEDBACK-01",
            title="Feedback timing and learning from errors",
            authors="Butler & Roediger",
            year=2008,
            finding=(
                "بازخورد پس از تلاش برای بازیابی (حتی اگر تلاش نادرست باشد) "
                "مؤثرتر از بازخورد پیش از تلاش است؛ آزمون بدون بازخورد هم "
                "مفید است، اما بازخورد اثر را تقویت می‌کند."
            ),
            effect="هماهنگ با ادبیات testing effect",
            url="https://journals.sagepub.com/doi/10.1002/acp.1503",
            design_rule=(
                "ابتدا سؤال بزن، بعد پاسخ را ببین؛ ترتیب معکوس ارزش "
                "یادگیری‌اش را از دست می‌دهد."
            ),
            used_in_engine=True,
        ),
        Evidence(
            id="DUALCODE-01",
            title="Dual coding theory (verbal + visual representations)",
            authors="Paivio",
            year=1986,
            finding=(
                "اطلاعات هم به‌صورت کلامی و هم تصویری کدگذاری می‌شوند؛ "
                "ترکیب هر دو مسیر، بازیابی را تقویت می‌کند."
            ),
            effect="چارچوب نظری؛ آثار متوسط تا بزرگ در محتوای تصویری",
            url="https://en.wikipedia.org/wiki/Dual-coding_theory",
            design_rule=(
                "برای محتوای نموداری/شکلی: توصیف با زبان خودت + بازخوانیِ "
                "برچسب‌دار، هر دو انجام شوند."
            ),
            used_in_engine=True,
        ),
        Evidence(
            id="SLEEP-01",
            title="The memory function of sleep",
            authors="Diekelmann & Born",
            year=2010,
            finding=(
                "الگوهای فعالیت عصبی حین یادگیری در خواب عمیق بازپخش می‌شوند؛ "
                "این بازپخش، تثبیت سیستم و تغییر کیفیتی حافظه (گسسته به کلی) "
                "را می‌سازد."
            ),
            effect="NRN review",
            url="https://www.nature.com/articles/nrn2762",
            design_rule=(
                "برنامهٔ هر شب، خواب کافی را به‌عنوان «قرارداد ظرفیت» رعایت "
                "می‌کند؛ کاهش خواب ظرفیت فردا را کم می‌کند، نه فقط امروز را."
            ),
            used_in_engine=False,
        ),
        Evidence(
            id="SPACING-03",
            title="Optimizing Distributed Practice: Theoretical Analysis and Practical Implications",
            authors="Cepeda, Vul, Rohrer, Wixted & Pashler",
            year=2009,
            finding=(
                "در بازه‌های نگهداشت چندماهه، فاصلهٔ بهینه از یک روز بیشتر "
                "می‌شود؛ رابطهٔ فاصله/بازهٔ نگهداشت تقریباً ثابت می‌ماند."
            ),
            effect="۴۸ نقطهٔ داده",
            url="https://home.cs.colorado.edu/~mozer/Research/Selected%20Publications/reprints/Cepedaetal2009.pdf",
            design_rule=(
                "فاصله‌های مرور با نزدیک‌شدن به آزمون به‌طور خودکار کوچک "
                "می‌شوند (قاعدهٔ سقف وابسته به آزمون)."
            ),
            used_in_engine=True,
        ),
    )
}

#: موضوع‌های پشتیبانی‌شده برای جست‌وجوی شواهد.
EVIDENCE_TOPICS: dict[str, tuple[str, ...]] = {
    "spacing": ("SPACING-01", "SPACING-02", "SPACING-03"),
    "retrieval": ("TESTING-01", "TESTING-02", "TESTING-03", "FEEDBACK-01"),
    "interleaving": ("INTERLEAVE-01", "INTERLEAVE-02"),
    "worked_examples": ("WORKED-EX-01", "WORKED-EX-02", "EXPERTISE-01"),
    "consolidation": ("CONSOL-01", "CONSOL-02", "SLEEP-01"),
    "desirable_difficulties": ("DD-01",),
    "memory_model": ("DSR-01",),
    "errors": ("HYPER-01", "HYPER-02", "FEEDBACK-01"),
    "dual_coding": ("DUALCODE-01",),
}


def evidence(evidence_id: str) -> Evidence:
    """شاهد بر پایهٔ شناسه؛ خطا اگر شناسه ناشناخته باشد."""
    try:
        return EVIDENCE[evidence_id]
    except KeyError as exc:
        raise KeyError(f"شناسهٔ شاهد ناشناخته: {evidence_id}") from exc


def evidence_for_topic(topic: str) -> tuple[Evidence, ...]:
    """همهٔ شواهد مرتبط با یک موضوع (کلید EVIDENCE_TOPICS)."""
    ids = EVIDENCE_TOPICS.get(topic, ())
    return tuple(EVIDENCE[i] for i in ids if i in EVIDENCE)


def cite(evidence_id: str) -> str:
    """ارجاع کوتاه قابل نمایش به کاربر: «نویسنده (سال)»."""
    item = evidence(evidence_id)
    return f"{item.authors.split('؛')[0].split(' و ')[0]} ({item.year})"


def evidence_summary(evidence_ids: tuple[str, ...] | list[str]) -> str:
    """خلاصهٔ یک‌خطی از یک یا چند شاهد برای نمایش در UI."""
    if not evidence_ids:
        return ""
    parts = [f"{evidence(i).authors} ({evidence(i).year})" for i in evidence_ids]
    return "پشتیبان علمی: " + " · ".join(parts)


__all__ = [
    "EVIDENCE",
    "EVIDENCE_TOPICS",
    "Evidence",
    "cite",
    "evidence",
    "evidence_for_topic",
    "evidence_summary",
]
