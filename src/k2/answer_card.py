"""خواندن کارت پاسخ آزمون — کاملاً آفلاین، بدون هیچ سرویس بیرونی.

چرا این ماژول به‌جای OCR: آنچه برنامه لازم دارد تشخیص حرف یا رقم نیست؛
آنچه لازم دارد این است که **کدام گزینه در هر سؤال پر شده** است. کارت پاسخ
کنکور یک شبکهٔ دایرهٔ چاپی است که دانش‌آموز یکی را سیاه می‌کند. پس به‌جای
تشخیص متن، شبکه را پیدا می‌کنیم و میزان سیاهی هر خانه را می‌سنجیم.

قواعد صداقت این ماژول:

* هیچ سؤالی حدس زده نمی‌شود. اگر هیچ یا بیش از یک گزینه پر شده باشد، یا
  پرکردن مرزی باشد، سؤال «نامشخص/ابهام‌دار» ثبت می‌شود نه اینکه یک گزینه
  تصادفی انتخاب شود.
* هیچ عددی (تعداد سؤال، درست، غلط، خالی) از خودِ تصویر استخراج نمی‌شود؛
  کاربر آن‌ها را می‌بیند و تأیید می‌کند.
* تشخیص شبکه و آستانه‌ها در خروجی برگردانده می‌شوند تا کاربر بتواند اشتباه
  را ببیند و اصلاح کند.

وابستگی: ``Pillow`` برای باز کردن تصویر. اگر نصب نباشد، ماژول خطای صریح
می‌دهد و کاربر مسیر دستی (وارد کردن اعداد)作为 پشتیبان باقی می‌ماند.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

try:  # pragma: no cover - وابستگی اختیاری
    from PIL import Image, ImageOps  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore
    ImageOps = None  # type: ignore


class AnswerCardError(RuntimeError):
    """تصویر خوانده نشد یا ساختار کارت پیدا نشد."""


#: برچسب گزینه‌ها (ترتیب استاندارد کارت پاسخ کنکور).
OPTION_LABELS = ("1", "2", "3", "4")

#: آستانه‌های پیش‌فرض [H] — در رابط کاربری قابل تنظیم‌اند.
DEFAULT_FILL_THRESHOLD = 0.45
DEFAULT_AMBIGUOUS_BAND = 0.20


@dataclass
class CellReading:
    """یک خانهٔ شبکه."""

    row: int
    column: int
    fill: float

    @property
    def label(self) -> str:
        return OPTION_LABELS[self.column] if self.column < len(OPTION_LABELS) else str(
            self.column + 1
        )


@dataclass
class QuestionReading:
    """نتیجهٔ یک سؤال."""

    number: int
    selected: Optional[int]
    fill_values: tuple[float, ...]
    status: str  # "marked" | "blank" | "ambiguous"
    note: str = ""

    @property
    def is_clean(self) -> bool:
        return self.status == "marked"


@dataclass
class CardReading:
    """نتیجهٔ کامل خواندن یک کارت پاسخ."""

    rows: int
    columns: int
    questions: list[QuestionReading] = field(default_factory=list)
    grid_confidence: float = 0.0
    rotation_degrees: float = 0.0
    fill_threshold: float = DEFAULT_FILL_THRESHOLD
    ambiguous_band: float = DEFAULT_AMBIGUOUS_BAND
    warnings: list[str] = field(default_factory=list)
    #: متن/عدد خوانده‌شده از تصویر (مثلاً شمارهٔ داوطلندی) — اگر پیدا شد.
    ocr_text: str = ""

    @property
    def clean_count(self) -> int:
        return sum(1 for q in self.questions if q.status == "marked")

    @property
    def blank_count(self) -> int:
        return sum(1 for q in self.questions if q.status == "blank")

    @property
    def ambiguous_count(self) -> int:
        return sum(1 for q in self.questions if q.status == "ambiguous")

    def selected_list(self) -> list[Optional[int]]:
        """گزینهٔ انتخاب‌شدهٔ هر سؤال؛ ``None`` برای خالی یا ابهام‌دار."""
        return [q.selected if q.status == "marked" else None for q in self.questions]

    def to_dict(self) -> dict:
        return {
            "rows": self.rows,
            "columns": self.columns,
            "questions": [
                {
                    "number": q.number,
                    "selected": q.selected,
                    "fill": list(q.fill_values),
                    "status": q.status,
                    "note": q.note,
                }
                for q in self.questions
            ],
            "grid_confidence": self.grid_confidence,
            "rotation_degrees": self.rotation_degrees,
            "fill_threshold": self.fill_threshold,
            "ambiguous_band": self.ambiguous_band,
            "warnings": list(self.warnings),
        }


# ---------------------------------------------------------------------------
# پردازش تصویر
# ---------------------------------------------------------------------------


def _require_pil() -> None:
    if Image is None:  # pragma: no cover
        raise AnswerCardError(
            "کتابخانهٔ Pillow نصب نیست. برای خواندن کارت پاسخ آن را نصب کن "
            "(pip install Pillow). تا آن زمان، اعداد را دستی وارد کن."
        )


def load_image(path) -> "Image.Image":
    """تصویر را می‌خواند و به grayscale + اندازهٔ متعادل تبدیل می‌کند."""
    _require_pil()
    try:
        image = Image.open(path)
        image.load()
    except FileNotFoundError as exc:
        raise AnswerCardError(f"فایل تصویر پیدا نشد: {path}") from exc
    except Exception as exc:  # pragma: no cover - فرمت ناشناخته
        raise AnswerCardError(
            "فایل تصویر خوانده نشد. فرمت‌های معمول PNG/JPG/WebP را امتحان کن."
        ) from exc
    image = ImageOps.exif_transpose(image)
    image = image.convert("L")
    # بزرگ‌کردن تصویرهای کوچک تا شبکهٔ دایره‌ها قابل سنجش باشد
    width, height = image.size
    if max(width, height) < 1200:
        scale = 1200 / max(width, height)
        image = image.resize((int(width * scale), int(height * scale)))
    return image


def ink_mask(image, threshold: int = 128):
    """نقشهٔ باینری «مرکب»: True یعنی پیکسل تیره است."""
    return image.point(lambda p: 255 if p < threshold else 0, mode="L")


def _project(mask, axis: int) -> list[int]:
    """تجمیع مرکب‌بودن روی یک محور (۰ = افقی،۱ = عمودی)."""
    width, height = mask.size
    pixels = mask.load()
    totals: list[int] = []
    if axis == 0:  # تجمیع ستونی → طول بر حسب عرض
        for x in range(width):
            count = 0
            for y in range(height):
                if pixels[x, y]:
                    count += 1
            totals.append(count)
    else:  # تجمیع سطری → طول بر حسب ارتفاع
        for y in range(height):
            count = 0
            for x in range(width):
                if pixels[x, y]:
                    count += 1
            totals.append(count)
    return totals


def _runs(values: Sequence[int], minimum: int) -> list[tuple[int, int]]:
    """بازه‌های پیوسته‌ای که مقدارشان از ``minimum`` بیشتر است."""
    out: list[tuple[int, int]] = []
    start: Optional[int] = None
    for index, value in enumerate(values):
        if value >= minimum:
            if start is None:
                start = index
        elif start is not None:
            out.append((start, index - 1))
            start = None
    if start is not None:
        out.append((start, len(values) - 1))
    return out


def _merge_close(runs: Sequence[tuple[int, int]], gap: int) -> list[tuple[int, int]]:
    """بازه‌های خیلی نزدیک را می‌آمیزد (خطای نویز در اسکن)."""
    if not runs:
        return []
    merged = [list(runs[0])]
    for start, end in runs[1:]:
        if start - merged[-1][1] <= gap:
            merged[-1][1] = end
        else:
            merged.append([start, end])
    return [(a, b) for a, b in merged]


def _detect_bands(values: Sequence[int], span: int) -> list[tuple[int, int]]:
    """باندهای پیوستهٔ شبکه را از یک بردار تجمیعی پیدا می‌کند.

    چرا آستانهٔ پایین: خط دایرهٔ چاپی در عرضی‌ترین نقطهٔ خود بیشترین مرکب
    را دارد و در لبه‌ها کمتر. با آستانهٔ بالا، یک سطر دایره به چند تکه
    می‌شکد و شبکه خراب می‌شود.

    چرا ادغام بر پایهٔ فاصلهٔ میانه: فاصلهٔ واقعی بین دو خانهٔ همسایه خودش
    معیار درست است. اگر بر پایهٔ «عرض خانه» ادغام کنیم، در کارتی که خانه‌ها
    به هم نزدیک‌اند همهٔ ستون‌ها به هم می‌چسبند.
    """
    peak = max(values) if values else 0
    if peak <= 0:
        return []
    runs = _runs(values, max(2, int(peak * 0.06)))
    if not runs:
        return []
    widths = sorted(b - a + 1 for a, b in runs)
    median_width = widths[len(widths) // 2]
    if median_width <= 1:
        return []
    # تکه‌های بسیار کوچک‌تر از اندازهٔ معمول نویزند
    minimum = max(3, int(median_width * 0.4))
    bands = [r for r in runs if r[1] - r[0] + 1 >= minimum]
    if len(bands) < 2:
        return bands
    gaps = sorted(bands[i + 1][0] - bands[i][1] for i in range(len(bands) - 1))
    median_gap = gaps[len(gaps) // 2]
    if median_gap <= 0:
        return bands
    merge_limit = max(2, int(median_gap * 0.45))
    return _merge_close(bands, merge_limit)


def detect_grid(
    image,
    *,
    expected_rows: Optional[int] = None,
    fill_threshold: float = DEFAULT_FILL_THRESHOLD,
) -> tuple[list[tuple[int, int]], list[tuple[int, int]], float]:
    """شبکهٔ سطر و ستون دایره‌ها را پیدا می‌کند.

    خروجی: (بازهٔ سطرها، بازهٔ ستون‌ها، اطمینان). اطمینان بر پایهٔ یکنواختی
    فاصلهٔ خانه‌ها حساب می‌شود؛ اگر شبکه پیدا نشد، لیست خالی برمی‌گردد.
    """
    width, height = image.size
    mask = ink_mask(image)
    row_sums = _project(mask, 1)
    if not max(row_sums) if row_sums else True:
        return [], [], 0.0

    row_runs = _detect_bands(row_sums, height)
    if not row_runs:
        return [], [], 0.0

    # ستون‌ها را فقط در بازهٔ چند سطر اول می‌یابیم. چرا: اگر تجمیع عمودی را
    # روی کل ارتفاع بگیریم، ستون دایره‌ها به هم می‌چسبند (هر ستون در همهٔ
    # سطرها مرکب دارد) و شبکه یک تکه دیده می‌شود.
    probe_rows = row_runs[: min(3, len(row_runs))]
    top = max(0, probe_rows[0][0] - 4)
    bottom = min(height, probe_rows[-1][1] + 5)
    col_sums = [0] * width
    pixels = mask.load()
    for y in range(top, bottom):
        for x in range(width):
            if pixels[x, y]:
                col_sums[x] += 1
    col_runs = _detect_bands(col_sums, width)
    if not col_runs:
        return [], [], 0.0

    confidence = _grid_confidence(row_runs, col_runs, height, width)
    if expected_rows and len(row_runs) not in (expected_rows, expected_rows + 1):
        # اگر تعداد سطرها با انتظار نمی‌خواند، اطمینان را پایین می‌آوریم
        confidence *= 0.5
    return row_runs, col_runs, confidence


def _grid_confidence(
    row_runs: Sequence[tuple[int, int]],
    col_runs: Sequence[tuple[int, int]],
    height: int,
    width: int,
) -> float:
    """یکنواختی شبکه را به عددی بین صفر و یک تبدیل می‌کند."""
    if len(row_runs) < 2 or len(col_runs) < 2:
        return 0.0
    row_gaps = [
        row_runs[i + 1][0] - row_runs[i][1] for i in range(len(row_runs) - 1)
    ]
    col_gaps = [
        col_runs[i + 1][0] - col_runs[i][1] for i in range(len(col_runs) - 1)
    ]
    row_score = _evenness(row_gaps, height)
    col_score = _evenness(col_gaps, width)
    return max(0.0, min(1.0, (row_score + col_score) / 2.0))


def _evenness(gaps: Sequence[int], span: int) -> float:
    if not gaps or span <= 0:
        return 0.0
    average = sum(gaps) / len(gaps)
    if average <= 0:
        return 0.0
    deviation = sum(abs(g - average) for g in gaps) / len(gaps)
    return max(0.0, 1.0 - (deviation / average))


# ---------------------------------------------------------------------------
# خواندن کارت
# ---------------------------------------------------------------------------


def read_card(
    path,
    *,
    expected_rows: Optional[int] = None,
    columns: int = 4,
    fill_threshold: float = DEFAULT_FILL_THRESHOLD,
    ambiguous_band: float = DEFAULT_AMBIGUOUS_BAND,
) -> CardReading:
    """کارت پاسخ را می‌خواند و برای هر سؤال گزینهٔ پر‌شده را برمی‌گرداند.

    ``expected_rows`` اگر داده شود فقط برای پایین آوردن اطمینان استفاده
    می‌شود، نه برای اینکه تعداد سؤال را تحمیل کند — چون تحمیل کردن یعنی
    ساختن سؤالی که در تصویر نیست.
    """
    image = load_image(path)
    row_runs, col_runs, confidence = detect_grid(
        image, expected_rows=expected_rows, fill_threshold=fill_threshold
    )
    if not row_runs or len(col_runs) < columns:
        raise AnswerCardError(
            "شبکهٔ دایره‌های کارت پاسخ پیدا نشد. تصویر را دقیق‌تر و کامل‌تر "
            "بگیر (کل کارت در کادر باشد و نور یکنواخت باشد)."
        )
    warnings: list[str] = []
    if confidence < 0.5:
        warnings.append(
            "اطمینان تشخیص شبکه پایین است؛ جدول را قبل از ذخیره کنترل کن."
        )
    # اگر ستون‌های تشخیص‌داده‌شده بیشتر از انتظار است، شبکه را به اندازهٔ
    # موردانتظر برش می‌زنیم (ستون‌های اضافی معمولاً حاشیه/شماره هستند).
    used_cols = col_runs[:columns] if len(col_runs) >= columns else col_runs
    if len(col_runs) > columns:
        warnings.append(
            f"{len(col_runs)} ستون تشخیص داده شد و {columns} ستون اول استفاده "
            "می‌شود؛ اگر ترتیب ستون‌ها فرق داشت، در جدول اصلاح کن."
        )

    mask = ink_mask(image)
    width, height = mask.size
    pixels = mask.load()

    questions: list[QuestionReading] = []
    for row_index, (r0, r1) in enumerate(row_runs, start=1):
        fills: list[float] = []
        for c0, c1 in used_cols:
            area = max(1, (r1 - r0 + 1) * (c1 - c0 + 1))
            ink = 0
            for y in range(max(0, r0), min(height, r1 + 1)):
                for x in range(max(0, c0), min(width, c1 + 1)):
                    if pixels[x, y]:
                        ink += 1
            fills.append(ink / area)
        question = _classify(row_index, fills, fill_threshold, ambiguous_band)
        questions.append(question)

    return CardReading(
        rows=len(row_runs),
        columns=len(used_cols),
        questions=questions,
        grid_confidence=confidence,
        fill_threshold=fill_threshold,
        ambiguous_band=ambiguous_band,
        warnings=warnings,
    )


def _classify(
    number: int,
    fills: Sequence[float],
    threshold: float,
    band: float,
) -> QuestionReading:
    """یک سؤال را بر پایهٔ میزان سیاهی خانه‌ها برچسب می‌زند.

    هیچ‌وقت گزینه‌ای انتخاب نمی‌شود که مرز ابهام باشد؛ آن سؤال
    «ابهام‌دار» می‌شود تا کاربر خودش تصمیم بگیرد.
    """
    high = threshold + band
    low = max(0.0, threshold - band)
    marked = [i for i, f in enumerate(fills) if f >= high]
    near = [i for i, f in enumerate(fills) if low <= f < high]
    if len(marked) == 1 and not near:
        return QuestionReading(number, marked[0], tuple(fills), "marked")
    if not marked and not near:
        return QuestionReading(number, None, tuple(fills), "blank", "هیچ گزینه‌ای پر نشده")
    if len(marked) > 1:
        return QuestionReading(
            number,
            None,
            tuple(fills),
            "ambiguous",
            "بیش از یک گزینه پر شده: " + "، ".join(str(i + 1) for i in marked),
        )
    return QuestionReading(
        number,
        None,
        tuple(fills),
        "ambiguous",
        "پرکردن مرزی است؛ با چشم خودت بررسی کن.",
    )


def compare_with_key(
    reading: CardReading, key: Sequence[Optional[int]]
) -> dict:
    """کارت خوانده‌شده را با کلید پاسخ مقایسه می‌کند.

    ``key`` فهرستی به طول سؤال‌هاست؛ ``None`` یعنی پاسخ آن سؤال در کلید
    ثبت نشده. سؤال ابهام‌دار هرگز «درست» یا «غلط» شمرده نمی‌شود؛ در
    ``unknown`` می‌رود.
    """
    correct = wrong = blank = unknown = 0
    details: list[dict] = []
    for index, question in enumerate(reading.questions):
        expected = key[index] if index < len(key) else None
        if question.status == "ambiguous":
            unknown += 1
            verdict = "unknown"
        elif question.status == "blank":
            blank += 1
            verdict = "blank"
        elif expected is None:
            unknown += 1
            verdict = "unknown"
        elif question.selected == expected:
            correct += 1
            verdict = "correct"
        else:
            wrong += 1
            verdict = "wrong"
        details.append(
            {
                "number": question.number,
                "selected": question.selected,
                "expected": expected,
                "verdict": verdict,
                "note": question.note,
            }
        )
    return {
        "correct": correct,
        "wrong": wrong,
        "blank": blank,
        "unknown": unknown,
        "total": len(reading.questions),
        "details": details,
    }


def summarise(reading: CardReading) -> str:
    """یک خط خلاصه برای نمایش به کاربر."""
    parts = [
        f"{reading.rows} سؤال خوانده شد",
        f"{reading.clean_count} پر‌شده",
        f"{reading.blank_count} خالی",
    ]
    if reading.ambiguous_count:
        parts.append(f"{reading.ambiguous_count} ابهام‌دار")
    parts.append(f"اطمینان شبکه {reading.grid_confidence:.0%}")
    return " · ".join(parts)
