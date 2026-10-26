"""نمای «ساعت مطالعه»: تایمر واقعی، ثبت دستی و جمع خالص (بند ۱۵)."""

from __future__ import annotations

import datetime as _dt

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...domain.enums import SessionKind
from ...domain.models import StudySession, StudySessionRevision
from ...jdate import format_datetime, format_jalali, format_minutes, format_number
from ...service import AdvisorService
from ..widgets import Card, info_box, notify, warn_box

SESSION_KINDS = [
    (SessionKind.STUDY, "مطالعهٔ مستقل"),
    (SessionKind.LIVE_CLASS, "کلاس حضوری/آنلاین"),
    (SessionKind.RECORDED_CLASS, "کلاس ضبط‌شده"),
    (SessionKind.TEST, "تست/آزمون"),
    (SessionKind.ANALYSIS, "تحلیل تست"),
    (SessionKind.REVIEW, "مرور"),
    (SessionKind.CONSOLIDATION, "تثبیت"),
    (SessionKind.HOMEWORK, "تکلیف"),
]


class ManualSessionDialog(QDialog):
    """ثبت دستی یک جلسهٔ مطالعه (وقتی تایمر استفاده نشده)."""

    def __init__(
        self, service: AdvisorService, session: StudySession | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.service = service
        self.session = session
        self.setWindowTitle("ثبت دستی ساعت مطالعه")
        self.setLayoutDirection(Qt.RightToLeft)
        # حداقل پهنا برای اینکه برچسب‌های فارسی و فهرست‌های کشویی بریده نشوند.
        self.setMinimumWidth(580)
        form = QFormLayout(self)

        self.kind_combo = QComboBox()
        for kind, label in SESSION_KINDS:
            self.kind_combo.addItem(label, kind.value)
        form.addRow("نوع جلسه:", self.kind_combo)

        self.subject_combo = QComboBox()
        self.subject_combo.addItem("— بدون درس —", None)
        for subject in service.repo.list_subjects(include_unselected=True):
            self.subject_combo.addItem(subject.name, subject.id)
        form.addRow("درس:", self.subject_combo)

        self.topic_combo = QComboBox()
        self.topic_combo.addItem("— بدون مبحث —", None)
        for topic in service.list_topics():
            self.topic_combo.addItem(f"{topic.subject_name} · {topic.name}", topic.id)
        form.addRow("مبحث:", self.topic_combo)

        self.start_edit = QDateTimeEdit()
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.end_edit = QDateTimeEdit()
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        now = _dt.datetime.now().replace(second=0, microsecond=0)
        self.start_edit.setDateTime(now - _dt.timedelta(hours=1))
        self.end_edit.setDateTime(now)
        form.addRow("شروع:", self.start_edit)
        form.addRow("پایان:", self.end_edit)

        self.break_spin = QSpinBox()
        self.break_spin.setRange(0, 600)
        self.break_spin.setSuffix(" دقیقه")
        form.addRow("استراحت در این بازه:", self.break_spin)

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("یادداشت اختیاری")
        form.addRow("یادداشت:", self.note_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("ذخیره")
        buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _accept(self) -> None:
        start = self.start_edit.dateTime().toPython()
        end = self.end_edit.dateTime().toPython()
        if end <= start:
            QMessageBox.warning(self, "بازهٔ نامعتبر", "زمان پایان باید بعد از شروع باشد.")
            return
        gross = int((end - start).total_seconds())
        paused = int(self.break_spin.value()) * 60
        minutes = max(0, (gross - paused) // 60)
        self.result_session = StudySession(
            subject_id=self.subject_combo.currentData(),
            topic_id=self.topic_combo.currentData(),
            kind=SessionKind(self.kind_combo.currentData()),
            mode="manual",
            started_at=start,
            ended_at=end,
            paused_seconds=paused,
            minutes=minutes,
            note=self.note_edit.text().strip(),
        )
        self.accept()


class CorrectSessionDialog(QDialog):
    """اصلاح یک جلسهٔ ثبت‌شده با دلیل — تاریخچه حفظ می‌شود."""

    FIELDS = [
        ("minutes", "دقیقهٔ خالص"),
        ("kind", "نوع جلسه"),
        ("note", "یادداشت"),
    ]

    def __init__(
        self, service: AdvisorService, session: StudySession,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.service = service
        self.session = session
        self.setWindowTitle("اصلاح جلسهٔ ثبت‌شده")
        self.setLayoutDirection(Qt.RightToLeft)
        # حداقل پهنا برای اینکه برچسب‌های فارسی و فهرست‌های کشویی بریده نشوند.
        self.setMinimumWidth(520)
        form = QFormLayout(self)

        self.field_combo = QComboBox()
        for value, label in self.FIELDS:
            self.field_combo.addItem(label, value)
        form.addRow("فیلد:", self.field_combo)
        self.field_combo.currentIndexChanged.connect(self._on_field)

        self.kind_combo = QComboBox()
        for kind, label in SESSION_KINDS:
            self.kind_combo.addItem(label, kind.value)
        index = self.kind_combo.findData(session.kind)
        if index >= 0:
            self.kind_combo.setCurrentIndex(index)
        form.addRow("نوع تازه:", self.kind_combo)

        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 1440)
        self.minutes_spin.setValue(session.minutes)
        form.addRow("دقیقهٔ تازه:", self.minutes_spin)

        self.note_edit = QLineEdit(session.note)
        form.addRow("یادداشت تازه:", self.note_edit)

        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText("دلیل اصلاح؛ مثلاً تایمر را دیر زدم")
        form.addRow("دلیل:", self.reason_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("ذخیرهٔ اصلاح")
        buttons.button(QDialogButtonBox.Cancel).setText("انصراف")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self._on_field()

    def _on_field(self) -> None:
        field = self.field_combo.currentData()
        self.kind_combo.setEnabled(field == "kind")
        self.minutes_spin.setEnabled(field == "minutes")
        self.note_edit.setEnabled(field == "note")

    def _accept(self) -> None:
        reason = self.reason_edit.text().strip()
        if not reason:
            QMessageBox.warning(self, "دلیل لازم است", "برای هر اصلاح، دلیل ثبت شود.")
            return
        field = self.field_combo.currentData()
        if field == "minutes":
            value: object = self.minutes_spin.value()
        elif field == "kind":
            value = self.kind_combo.currentData()
        else:
            value = self.note_edit.text()
        try:
            self.revision: StudySessionRevision = self.service.correct_study_session(
                int(self.session.id or 0),
                field_name=field,
                new_value=value,
                reason=reason,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "اصلاح نشد", str(exc))
            return
        self.accept()


class StudyTimerPage(QWidget):
    """تایمر مطالعه با شروع/توقف/ادامه و جمع خالص روزانه و هفتگی."""

    def __init__(self, service: AdvisorService, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick)
        self._build()
        self.refresh()

    # ---- ساخت رابط ----

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("ساعت مطالعه")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        btn_manual = QPushButton("ثبت دستی")
        btn_manual.clicked.connect(self._manual)
        header.addWidget(btn_manual)
        btn_correct = QPushButton("اصلاح با تاریخچه")
        btn_correct.clicked.connect(self._correct)
        header.addWidget(btn_correct)
        root.addLayout(header)

        timer_card = Card("تایمر", tone="timer")
        clock_row = QHBoxLayout()
        self.clock = QLabel("۰۰:۰۰:۰۰")
        self.clock.setObjectName("bigNumber")
        clock_row.addWidget(self.clock)
        self.timer_state = QLabel("آماده")
        self.timer_state.setObjectName("muted")
        clock_row.addWidget(self.timer_state)
        clock_row.addStretch(1)
        timer_card.add_layout(clock_row)

        form_row = QHBoxLayout()
        self.kind_combo = QComboBox()
        for kind, label in SESSION_KINDS:
            self.kind_combo.addItem(label, kind.value)
        form_row.addWidget(QLabel("نوع:"))
        form_row.addWidget(self.kind_combo)
        self.topic_combo = QComboBox()
        self.topic_combo.addItem("— بدون مبحث —", None)
        for topic in self.service.list_topics():
            self.topic_combo.addItem(
                f"{topic.subject_name} · {topic.name}", topic.id
            )
        form_row.addWidget(QLabel("مبحث:"))
        form_row.addWidget(self.topic_combo, 1)
        timer_card.add_layout(form_row)

        buttons_row = QHBoxLayout()
        self.btn_start = QPushButton("شروع")
        self.btn_start.setObjectName("primary")
        self.btn_start.clicked.connect(self._start)
        buttons_row.addWidget(self.btn_start)
        self.btn_pause = QPushButton("استراحت")
        self.btn_pause.clicked.connect(self._pause)
        self.btn_pause.setEnabled(False)
        buttons_row.addWidget(self.btn_pause)
        self.btn_stop = QPushButton("پایان و ثبت")
        self.btn_stop.clicked.connect(self._stop)
        self.btn_stop.setEnabled(False)
        buttons_row.addWidget(self.btn_stop)
        buttons_row.addStretch(1)
        timer_card.add_layout(buttons_row)
        root.addWidget(timer_card)

        self.tip = info_box()
        self.tip.setWordWrap(True)
        root.addWidget(self.tip)

        stats_row = QHBoxLayout()
        self.tile_day = Card("امروز", tone="timer")
        self.day_value = QLabel("—")
        self.day_value.setObjectName("bigNumber")
        self.tile_day.add(self.day_value)
        self.day_detail = QLabel("")
        self.day_detail.setObjectName("muted")
        self.day_detail.setWordWrap(True)
        self.tile_day.add(self.day_detail)
        stats_row.addWidget(self.tile_day)

        self.tile_week = Card("این هفته", tone="timer")
        self.week_value = QLabel("—")
        self.week_value.setObjectName("bigNumber")
        self.tile_week.add(self.week_value)
        self.week_detail = QLabel("")
        self.week_detail.setObjectName("muted")
        self.week_detail.setWordWrap(True)
        self.tile_week.add(self.week_detail)
        stats_row.addWidget(self.tile_week)

        self.tile_compare = Card("برنامه در مقابل اجرا", tone="study")
        self.compare_value = QLabel("—")
        self.compare_value.setObjectName("bigNumber")
        self.tile_compare.add(self.compare_value)
        self.compare_detail = QLabel("")
        self.compare_detail.setObjectName("muted")
        self.compare_detail.setWordWrap(True)
        self.tile_compare.add(self.compare_detail)
        stats_row.addWidget(self.tile_compare)
        root.addLayout(stats_row)

        card = Card("جلسه‌های ثبت‌شده", tone="timer")
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["شروع", "نوع", "درس/مبحث", "خالص", "استراحت", "نوع ثبت", "یادداشت"]
        )
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        card.add(self.table)
        root.addWidget(card, 1)

    # ---- به‌روزرسانی ----

    def refresh(self) -> None:
        today = _dt.date.today()
        day = self.service.session_totals(today, today, "امروز")
        week = self.service.weekly_session_totals(today)
        self.day_value.setText(format_minutes(day.total_minutes))
        self.day_detail.setText(
            f"کلاس {format_minutes(day.class_minutes)} — "
            f"مطالعهٔ مستقل {format_minutes(day.independent_minutes)} — "
            f"تست {format_minutes(day.test_minutes)} — "
            f"تحلیل {format_minutes(day.analysis_minutes)} — "
            f"مرور {format_minutes(day.review_minutes)}"
        )
        self.week_value.setText(format_minutes(week.total_minutes))
        self.week_detail.setText(
            f"کلاس {format_minutes(week.class_minutes)} — "
            f"مطالعهٔ مستقل {format_minutes(week.independent_minutes)} — "
            f"{week.session_count} جلسه"
        )
        comparison = self.service.planned_vs_actual(today, today)
        planned = int(comparison.get("planned_minutes", 0) or 0)
        actual = int(comparison.get("actual_minutes", 0) or 0)
        ratio = float(comparison.get("ratio", 0.0) or 0.0)
        self.compare_value.setText(f"{format_number(ratio * 100)}٪")
        self.compare_detail.setText(
            f"برنامه {format_minutes(planned)} — اجرا {format_minutes(actual)}\n"
            f"{comparison.get('message', '')}"
        )

        sessions = self.service.list_study_sessions()
        self.table.setRowCount(0)
        for session in sessions[:60]:
            row = self.table.rowCount()
            self.table.insertRow(row)
            id_item = QTableWidgetItem(
                format_datetime(session.started_at) if session.started_at else "—"
            )
            id_item.setData(Qt.UserRole, session.id)
            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, QTableWidgetItem(session.kind.label))
            label = session.topic_name or session.subject_name or "—"
            self.table.setItem(row, 2, QTableWidgetItem(label))
            self.table.setItem(row, 3, QTableWidgetItem(format_minutes(session.minutes)))
            self.table.setItem(
                row, 4, QTableWidgetItem(format_minutes(session.paused_seconds / 60))
            )
            mode = {
                "timer": "تایمر",
                "manual": "دستی",
                "corrected": "اصلاح‌شده",
            }.get(session.mode, session.mode)
            self.table.setItem(row, 5, QTableWidgetItem(mode))
            self.table.setItem(row, 6, QTableWidgetItem(session.note or "—"))

        running = self.service.running_session()
        if running is not None:
            from k2.study_timer import StudyTimer

            self._timer = StudyTimer(running)
            self.btn_start.setEnabled(False)
            self.btn_pause.setEnabled(True)
            self.btn_stop.setEnabled(True)
            self.timer_state.setText("جلسهٔ ناتمام از نشست قبل پیدا شد — ادامه بده")
            self.timer.start()
        else:
            self._timer = None
            self.btn_start.setEnabled(True)
            self.btn_pause.setEnabled(False)
            self.btn_stop.setEnabled(False)
            self.timer_state.setText("آماده")
            self.timer.stop()
        self._update_tip()
        self._tick()

    def _update_tip(self) -> None:
        settings = self.service.settings.timer
        self.tip.setText(
            f"دقیقهٔ ثبت‌شده همیشه خالص است: زمان استراحت کم می‌شود. کلاس جدا از "
            f"مطالعهٔ مستقل شمرده می‌شود تا ساعت درس، ساعت مطالعهٔ شخصی‌ات را "
            f"پنهان نکند. بلوک پیشنهادی: {format_number(settings.max_continuous_minutes)} "
            f"دقیقه کار + {format_number(settings.suggested_break_minutes)} دقیقه استراحت."
        )

    def _tick(self) -> None:
        timer = getattr(self, "_timer", None)
        if timer is None:
            return
        snapshot = timer.snapshot()
        self.clock.setText(snapshot.display)
        if snapshot.running:
            self.timer_state.setText("در حال اندازه‌گیری…")
        elif snapshot.paused:
            self.timer_state.setText("استراحت — زمان استراحت شمرده نمی‌شود")

    # ---- کنش‌ها ----

    def _start(self) -> None:
        from k2.study_timer import StudyTimer

        running = self.service.running_session()
        if running is not None:
            notify(
                self,
                "جلسهٔ باز",
                "یک جلسهٔ ناتمام داری؛ ابتدا آن را ببند یا ادامه بده.",
            )
            return
        timer = StudyTimer()
        session = timer.start(
            kind=SessionKind(self.kind_combo.currentData()),
            topic_id=self.topic_combo.currentData(),
        )
        self.service.save_study_session(session)
        self._timer = timer
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.timer.start()
        self._tick()

    def _pause(self) -> None:
        timer = getattr(self, "_timer", None)
        if timer is None:
            return
        timer.toggle()
        self.service.save_study_session(timer.session)
        self._tick()

    def _stop(self) -> None:
        timer = getattr(self, "_timer", None)
        if timer is None:
            return
        try:
            session = timer.stop()
        except RuntimeError as exc:
            QMessageBox.warning(self, "تایمر", str(exc))
            return
        self.service.save_study_session(session)
        self.timer.stop()
        self._timer = None
        notify(
            self,
            "جلسه ثبت شد",
            f"دقیقهٔ خالص: {format_minutes(session.minutes)} — "
            f"استراحت: {format_minutes(session.paused_seconds / 60)}",
        )
        self.refresh()

    def _manual(self) -> None:
        dialog = ManualSessionDialog(self.service, None, self)
        if dialog.exec() != QDialog.Accepted:
            return
        session = getattr(dialog, "result_session", None)
        if session is None:
            return
        try:
            self.service.save_study_session(session)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "ذخیره نشد", str(exc))
            return
        self.refresh()

    def _correct(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            notify(self, "انتخاب نشده", "اول یک جلسه را از جدول انتخاب کن.")
            return
        item = self.table.item(row, 0)
        if item is None:
            return
        session_id = item.data(Qt.UserRole)
        if session_id is None:
            return
        session = next(
            (s for s in self.service.list_study_sessions() if s.id == session_id),
            None,
        )
        if session is None:
            return
        dialog = CorrectSessionDialog(self.service, session, self)
        if dialog.exec() != QDialog.Accepted:
            return
        revisions = self.service.session_revisions(session_id)
        notify(
            self,
            "اصلاح ثبت شد",
            f"تاریخچهٔ تغییر: {len(revisions)} رکورد — مقدار قبلی حذف نشده است.",
        )
        self.refresh()


__all__ = ["CorrectSessionDialog", "ManualSessionDialog", "StudyTimerPage"]
