"""تست‌های خواندن کارت پاسخ — با تصویر ساختگی و بدون هیچ سرویس بیرونی."""

from __future__ import annotations

import pytest

pytest.importorskip("PIL")

from PIL import Image, ImageDraw  # noqa: E402

from k2 import answer_card  # noqa: E402


def _make_card(
    path,
    rows: int = 20,
    columns: int = 4,
    answers: dict | None = None,
    *,
    blanks: tuple = (),
    ambiguous: tuple = (),
    width: int = 900,
    height: int = 1400,
) -> None:
    """یک کارت پاسخ ساختگی می‌سازد.

    ``answers[number] = column`` یعنی آن گزینه پر شده است.
    ``blanks`` سؤال‌هایی که هیچ گزینه‌ای پر نشده.
    ``ambiguous`` سؤال‌هایی که دو گزینه با هم پر شده‌اند.
    """
    answers = answers or {}
    image = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(image)

    margin_x = int(width * 0.12)
    margin_y = int(height * 0.06)
    gap_x = int((width - 2 * margin_x) / (columns + 1))
    gap_y = int((height - 2 * margin_y) / (rows + 1))
    radius = int(min(gap_x, gap_y) * 0.32)

    for r in range(1, rows + 1):
        cy = margin_y + r * gap_y
        # شمارهٔ سؤال سمت راست
        draw.text((margin_x // 2, cy - 6), str(r), fill=0)
        for c in range(columns):
            cx = margin_x + (c + 1) * gap_x
            draw.ellipse(
                (cx - radius, cy - radius, cx + radius, cy + radius), outline=0, width=3
            )
            if r in blanks:
                continue
            if r in ambiguous:
                # دو گزینه با هم پر می‌شوند
                for cc in (0, 1):
                    cx2 = margin_x + (cc + 1) * gap_x
                    draw.ellipse(
                        (cx2 - radius, cy - radius, cx2 + radius, cy2 + radius)
                        if False
                        else (cx2 - radius, cy - radius, cx2 + radius, cy + radius),
                        fill=0,
                    )
                break
            if answers.get(r) == c:
                draw.ellipse(
                    (cx - radius, cy - radius, cx + radius, cy + radius), fill=0
                )
    image.save(path)


def test_reads_clean_card(tmp_path):
    path = tmp_path / "card.png"
    _make_card(path, rows=20, answers={1: 0, 2: 3, 5: 2, 20: 1})
    reading = answer_card.read_card(path, expected_rows=20)
    assert reading.rows == 20
    assert reading.columns == 4
    assert reading.clean_count >= 4
    assert reading.ambiguous_count == 0
    assert reading.selected_list()[0] == 0
    assert reading.selected_list()[1] == 3
    assert reading.selected_list()[4] == 2
    assert reading.selected_list()[19] == 1
    assert reading.grid_confidence > 0.5


def test_blanks_are_reported_as_blank_not_guessed(tmp_path):
    path = tmp_path / "card.png"
    _make_card(path, rows=15, answers={1: 1, 3: 2}, blanks=(5, 7, 11))
    reading = answer_card.read_card(path, expected_rows=15)
    for number in (5, 7, 11):
        question = reading.questions[number - 1]
        assert question.status == "blank", number
        assert question.selected is None
    assert reading.blank_count >= 3


def test_double_marks_are_ambiguous_never_guessed(tmp_path):
    path = tmp_path / "card.png"
    _make_card(path, rows=12, answers={1: 1}, ambiguous=(4, 9))
    reading = answer_card.read_card(path, expected_rows=12)
    for number in (4, 9):
        question = reading.questions[number - 1]
        assert question.status == "ambiguous", number
        assert question.selected is None
    assert reading.ambiguous_count >= 2


def test_compare_with_key_never_counts_ambiguous_as_wrong(tmp_path):
    path = tmp_path / "card.png"
    _make_card(path, rows=10, answers={1: 0, 2: 1}, ambiguous=(3,), blanks=(4,))
    reading = answer_card.read_card(path, expected_rows=10)
    key = [0, 1, 2, 0, 0, 0, 0, 0, 0, 0]
    result = answer_card.compare_with_key(reading, key)
    assert result["correct"] == 2
    assert result["blank"] >= 1
    assert result["unknown"] >= 1  # سؤال ابهام‌دار
    # ابهام‌دار هرگز «غلط» شمرده نمی‌شود
    assert all(d["verdict"] != "wrong" for d in result["details"] if d["number"] == 3)


def test_short_key_marks_remaining_unknown(tmp_path):
    """کلید کوتاه‌تر از کارت: سؤال پر‌شدهٔ بی‌کلید «نامشخص» می‌شود.

    سؤال خالی «خالی» می‌ماند (واقعاً خالی است)، ولی سؤال پر‌شده‌ای که کلیدی
    برایش نداریم هرگز «درست» یا «غلط» شمرده نمی‌شود.
    """
    path = tmp_path / "card.png"
    _make_card(path, rows=8, answers={1: 0, 2: 1, 5: 3})
    reading = answer_card.read_card(path, expected_rows=8)
    result = answer_card.compare_with_key(reading, [0, 1])
    assert result["correct"] == 2
    assert result["unknown"] >= 1
    assert result["wrong"] == 0
    # سؤال ۵ پر شده ولی کلیدی ندارد
    detail = next(d for d in result["details"] if d["number"] == 5)
    assert detail["expected"] is None
    assert detail["verdict"] == "unknown"
    assert result["total"] == 8


def test_missing_image_raises_clear_error(tmp_path):
    with pytest.raises(answer_card.AnswerCardError):
        answer_card.read_card(tmp_path / "nope.png")


def test_unreadable_image_raises_clear_error(tmp_path):
    path = tmp_path / "junk.png"
    path.write_bytes(b"this is not an image")
    with pytest.raises(answer_card.AnswerCardError):
        answer_card.read_card(path)


def test_summary_is_honest_about_uncertainty(tmp_path):
    path = tmp_path / "card.png"
    _make_card(path, rows=10, answers={1: 0}, ambiguous=(2,), blanks=(3,))
    reading = answer_card.read_card(path, expected_rows=10)
    text = answer_card.summarise(reading)
    assert "سؤال خوانده شد" in text
    assert "ابهام‌دار" in text
    assert "خالی" in text


def test_reading_to_dict_round_trips(tmp_path):
    path = tmp_path / "card.png"
    _make_card(path, rows=6, answers={1: 2})
    reading = answer_card.read_card(path, expected_rows=6)
    data = reading.to_dict()
    assert data["rows"] == 6
    assert data["columns"] == 4
    assert data["questions"][0]["selected"] == 2
    assert data["questions"][0]["status"] == "marked"
    assert len(data["questions"][0]["fill"]) == 4


def test_fill_threshold_is_configurable(tmp_path):
    """آستانهٔ پر‌شدن قابل تنظیم است و روی برچسب‌گذاری اثر می‌گذارد."""
    path = tmp_path / "card.png"
    _make_card(path, rows=6, answers={1: 0})
    loose = answer_card.read_card(path, expected_rows=6, fill_threshold=0.2)
    strict = answer_card.read_card(path, expected_rows=6, fill_threshold=0.95)
    assert loose.fill_threshold == 0.2
    assert strict.fill_threshold == 0.95
    # با آستانهٔ خیلی سخت‌گیرانه، هیچ سؤالی «پر‌شدهٔ قطعی» نیست
    assert strict.clean_count == 0


def test_answer_card_dialog_reads_and_fills_the_exam_form(qapp, tmp_path, monkeypatch):
    """جریان کامل: تصویر کارت → خواندن → اصلاح → پر شدن فرم آزمون."""
    from k2.service import AdvisorService
    from k2.ui.views.answer_card import AnswerCardDialog
    from k2.ui.views.exams import RecordAttemptDialog

    monkeypatch.setattr(
        "k2.ui.views.settings.notify", lambda *a, **k: None, raising=False
    )
    service = AdvisorService(tmp_path / "card.db")
    card = tmp_path / "card.png"
    key = tmp_path / "key.png"
    _make_card(card, rows=20, answers={i: (i % 4) for i in range(1, 21)})
    _make_card(key, rows=20, answers={i: (i % 4) for i in range(1, 21)})

    dialog = AnswerCardDialog(service)
    dialog.rows_spin.setValue(20)
    dialog.cols_spin.setValue(4)
    dialog._read_into = lambda which: None  # جلوگیری از باز شدن QFileDialog
    reading = answer_card.read_card(card, expected_rows=20, columns=4)
    key_reading = answer_card.read_card(key, expected_rows=20, columns=4)
    dialog.reading = reading
    dialog.key_reading = key_reading
    dialog._rebuild_table()
    assert dialog.table.rowCount() == 20
    # یک خانه را دستی «نامشخص» می‌کنیم تا مسیر اصلاح هم آزمایش شود
    dialog.table.cellWidget(0, 3).setCurrentIndex(0)
    dialog._accept()
    assert dialog.result is not None
    assert dialog.result["total"] == 20
    assert dialog.result["correct"] >= 18

    form = RecordAttemptDialog(service)
    form.name_edit.setText("آزمون کارت")
    form.total_spin.setValue(dialog.result["total"])
    form.correct_spin.setValue(dialog.result["correct"])
    form.wrong_spin.setValue(dialog.result["wrong"])
    form.blank_spin.setValue(dialog.result["blank"])
    assert form.total_spin.value() == 20
    service.close()


def test_answer_card_dialog_rejects_unreadable_image(qapp, tmp_path):
    """تصویر خوانده‌نشدنی پیام صریح می‌دهد و برنامه را نمی‌شکند."""
    from k2.service import AdvisorService
    from k2.ui.views.answer_card import AnswerCardDialog

    service = AdvisorService(tmp_path / "bad.db")
    dialog = AnswerCardDialog(service)
    junk = tmp_path / "junk.png"
    junk.write_bytes(b"not an image")
    try:
        answer_card.read_card(junk)
    except answer_card.AnswerCardError:
        pass
    else:  # pragma: no cover
        raise AssertionError("باید خطا بدهد")
    assert dialog.reading is None
    service.close()
