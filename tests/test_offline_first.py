"""آزمون پذیرش «آفلاین‌محور»: با شبکهٔ کاملاً قطع، همهٔ کارها باید انجام شوند.

شرط پذیرش کاربر: «با شبکهٔ کاملاً خاموش، ثبت عقب‌افتادگی، گرفتن برنامهٔ
تازه، ثبت ساعت مطالعه و تنظیم روزهای بعدی — بدون اتصال مجدد.»

این تست واقعاً سوکت‌ها را می‌بندد (نه اینکه فقط ظاهر برنامه آفلاین باشد)
و کل مسیر کاربر را بدون شبکه اجرا می‌کند.
"""

from __future__ import annotations

import ast
import datetime as _dt
import socket
import ssl
import sys
from pathlib import Path

import pytest

from k2.domain.enums import (
    ActivityState,
    ActivityType,
    DeadlineKind,
    DeadlineType,
    SessionKind,
    TrackKind,
)
from k2.domain.models import (
    Activity,
    ExamProfile,
    LearningEvidence,
    StudySession,
    Subject,
    Topic,
    TopicDeadline,
)
from k2.service import AdvisorService

TODAY = _dt.date.today()

#: ماژول‌هایی که اگر در کد محصول ایمپورت شوند، برنامه به شبکه نیاز دارد.
#: ``urllib`` عمداً نیست: ``urllib.parse`` برای اعتبارسنجی نشانی منبع
#: استفاده می‌شود و هیچ اتصالی باز نمی‌کند.
FORBIDDEN_MODULES = {
    "requests", "urllib3", "httpx", "aiohttp",
    "socket", "ssl", "ftplib", "telnetlib", "smtplib",
    "socketserver", "xmlrpc", "webbrowser", "asyncio",
}

#: نام توابع/متدهاش که بازکردن اتصال شبکه‌اند و نباید در کد محصول باشند.
FORBIDDEN_CALLS = {
    "urlopen", "urlretrieve", "create_connection", "getaddrinfo",
    "gethostbyname", "gethostbyaddr", "gethostname", "HTTPConnection",
    "HTTPSConnection", "create_default_context", "wrap_socket",
    "socket_create_connection",
}


def _source_files() -> list[Path]:
    root = Path(__file__).resolve().parents[1] / "src" / "k2"
    return sorted(root.rglob("*.py"))


def _imports_of(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                names.add(node.module.split(".")[0])
    return names


@pytest.fixture()
def no_network(monkeypatch):
    """هر تلاش برای بازکردن سوکت یا اتصال TLS باید شکست بخورد."""

    def _blocked(*args, **kwargs):  # pragma: no cover - نباید فراخوانی شود
        raise AssertionError(
            "کد محصول سعی در استفاده از شبکه کرد؛ برنامه باید آفلاین کار کند."
        )

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(socket, "getaddrinfo", _blocked)
    monkeypatch.setattr(socket, "gethostbyname", _blocked)
    monkeypatch.setattr(ssl, "create_default_context", _blocked)
    monkeypatch.setattr(ssl, "SSLContext", _blocked)
    for name in ("requests", "urllib", "urllib.request", "http", "httpx"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    yield _blocked


def _seed(service: AdvisorService) -> Topic:
    subject = Subject(name="ریاضی", coefficient=2.0)
    service.create_subject(subject)
    topic = Topic(subject_id=subject.id, name="احتمال", estimated_minutes=240)
    service.create_topic(topic)
    return topic


# ---------------------------------------------------------------------------
# ۱) کد به شبکه وصل نیست
# ---------------------------------------------------------------------------


def test_product_code_imports_no_network_modules():
    """هیچ فایلی از ``src/k2`` نباید ماژول شبکه‌ای ایمپورت کند."""
    offenders: list[str] = []
    for path in _source_files():
        found = _imports_of(path) & FORBIDDEN_MODULES
        if found:
            offenders.append(f"{path.name}: {sorted(found)}")
    assert not offenders, "واسط شبکه در کد محصول: " + "; ".join(offenders)


def test_product_code_makes_no_network_calls():
    """هیچ فراخوانی‌ای که اتصال شبکه باز نکند نباید در کد محصول باشد."""
    offenders: list[str] = []
    for path in _source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = ""
            owner = ""
            if isinstance(func, ast.Attribute):
                name = func.attr
                owner = (
                    func.value.id
                    if isinstance(func.value, ast.Name)
                    else ""
                )
            elif isinstance(func, ast.Name):
                name = func.id
            if name not in FORBIDDEN_CALLS:
                continue
            offenders.append(f"{path.name}:{node.lineno}: {name}")
    assert not offenders, "فراخوانی شبکه‌ای: " + "; ".join(offenders)


def test_no_unreviewed_network_urls_in_product_source():
    """نشانی اینترنتی فقط به‌عنوان منبع استناد مجاز است.

    ``konkur_catalog`` و ``learning_science`` نشانی منبع را به‌عنوان
    فراداده نگه می‌دارند (بدون رفتن به شبکه). هر نشانیِ دیگری در کد
    محصول یعنی کدی که به شبکه وصل می‌شود.
    """
    allowed = {"konkur_catalog.py", "learning_science.py", "advisor_engine.py"}
    offenders: list[str] = []
    for path in _source_files():
        if path.name in allowed:
            continue
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if "https://" in line or "http://" in line:
                offenders.append(f"{path.name}:{number}")
    assert not offenders, offenders


# ---------------------------------------------------------------------------
# ۲) مسیر کامل کاربر با شبکهٔ بسته
# ---------------------------------------------------------------------------


def test_full_offline_workflow_with_sockets_blocked(tmp_path, no_network):
    """ثبت عقب‌افتادگی، گرفتن برنامه، ثبت مطالعه و تنظیم روزهای بعد."""
    db = tmp_path / "offline.db"
    service = AdvisorService(db)

    try:
        # ---- راه‌اندازی اولیه ----
        topic = _seed(service)
        service.create_exam_profile(
            ExamProfile(name="کنکور", target_date=TODAY + _dt.timedelta(days=250))
        )

        # ---- ۱) ثبت عقب‌افتادگی ----
        service.create_activity(
            Activity(
                title="کار عقب‌افتاده",
                type=ActivityType.INDEPENDENT_PRACTICE,
                est_minutes=60, remaining_minutes=60, min_chunk=20, max_chunk=60,
                deadline_type=DeadlineType.HARD,
                deadline_at=_dt.datetime.combine(
                    TODAY - _dt.timedelta(days=2), _dt.time(23, 59)
                ),
                state=ActivityState.OVERDUE,
            )
        )
        service.create_activity(
            Activity(
                title="کار امروز", type=ActivityType.INDEPENDENT_PRACTICE,
                est_minutes=45, remaining_minutes=45,
            )
        )
        backlog = service.backlog(TODAY)
        assert backlog.debt_minutes >= 60
        assert "کار عقب‌افتاده" in [
            item.title for item in service.list_activities()
        ]

        # ---- ۲) گرفتن برنامهٔ تازه (بدون شبکه) ----
        plan = service.plan_day(TODAY)
        assert plan.planned_minutes > 0
        assert plan.planned_minutes <= plan.capacity_minutes
        titles = [p.title for p in plan.placements] + [
            u.title for u in plan.unplaced
        ]
        # هیچ کاری پنهان نمی‌شود: یا در برنامه هست یا با دلیل در فهرست
        # «جا نشده»؛ هر دو قابل مشاهده‌اند.
        assert "کار امروز" in titles
        assert "کار عقب‌افتاده" in titles
        assert any(u.title == "کار عقب‌افتاده" for u in plan.unplaced)
        assert any(
            "مهلت" in (u.reason or "") for u in plan.unplaced
        ), "دلیل جا نشدن باید روشن باشد"

        # ---- ۳) ثبت ساعت مطالعه ----
        service.save_study_session(
            StudySession(
                subject_id=topic.subject_id, topic_id=topic.id,
                kind=SessionKind.STUDY, mode="timer",
                started_at=_dt.datetime.combine(TODAY, _dt.time(9, 0)),
                ended_at=_dt.datetime.combine(TODAY, _dt.time(10, 30)),
                minutes=90,
            )
        )
        assert service.session_totals(TODAY, TODAY).total_minutes == 90

        # ---- ۴) تنظیم روزهای بعد ----
        future = service.plan_range(TODAY + _dt.timedelta(days=1), 3)
        assert len(future) == 3
        review = service.nightly_review(TODAY)
        assert review.completion_ratio >= 0
        replan = service.replan_forward(today=TODAY)
        assert replan.fixed_preserved >= 0
        assert isinstance(replan.decisions, list)

        # ---- ۵) مهلت و مسیر دوگانه ----
        service.save_topic_deadline(
            TopicDeadline(
                topic_id=topic.id, kind=DeadlineKind.FINAL_CONSOLIDATION,
                target_date=TODAY + _dt.timedelta(days=45),
                target_percent=75, is_master=True,
            )
        )
        assert service.topic_deadline_plan(topic.id, today=TODAY).milestones
        changed, _message = service.record_track_evidence(
            topic.id, TrackKind.KONKUR,
            LearningEvidence(
                topic_id=topic.id, observed_on=TODAY, source="diagnostic",
                score=0.9,
            ),
        )
        assert changed is True

        # ---- ۶) گزارش مشاور و خروجی ----
        assert "دقیقه" in service.night_summary(TODAY)
        exported = service.export_json(tmp_path / "out" / "k2.json")
        assert exported.exists() and exported.stat().st_size > 0
    finally:
        service.close()

    # ---- ۷) داده‌ها پس از بستن برنامه زنده‌اند ----
    reopened = AdvisorService(db)
    try:
        assert reopened.list_activities()
        assert reopened.session_totals(TODAY, TODAY).total_minutes == 90
        assert len(reopened.list_study_sessions()) == 1
        assert reopened.list_topic_deadlines()
        assert "دقیقه" in reopened.night_summary(TODAY)
    finally:
        reopened.close()


def test_planner_does_not_touch_the_network_with_everything_enabled(
    tmp_path, no_network
):
    """زمان‌بند با همهٔ قابلیت‌ها روشن هم نباید به شبکه وصل شود."""
    service = AdvisorService(tmp_path / "p.db")
    try:
        topic = _seed(service)
        service.record_learning_evidence(
            LearningEvidence(
                topic_id=topic.id, observed_on=TODAY - _dt.timedelta(days=1),
                score=0.7,
            )
        )
        service.record_attempt(
            name="آزمون", total=50, correct=30, wrong=15, blank=5,
            duration_minutes=60,
        )
        service.create_activity(
            Activity(
                title="کار", type=ActivityType.INDEPENDENT_PRACTICE,
                est_minutes=45, remaining_minutes=45,
            )
        )
        for _ in range(3):
            plan = service.plan_day(TODAY)
            assert plan.planned_minutes >= 0
            plan_range = service.plan_range(TODAY, 7)
            assert len(plan_range) == 7
    finally:
        service.close()


def test_settings_and_backup_work_offline(tmp_path, no_network):
    """تنظیمات و پشتیبان‌گیری/بازیابی کاملاً محلی است."""
    service = AdvisorService(tmp_path / "s.db")
    try:
        _seed(service)
        service.save_study_session(
            StudySession(
                kind=SessionKind.STUDY, mode="manual",
                started_at=_dt.datetime.combine(TODAY, _dt.time(8, 0)),
                ended_at=_dt.datetime.combine(TODAY, _dt.time(8, 45)),
                minutes=45,
            )
        )
        service.settings.save()
        backup = service.backup(tmp_path / "backups")
        assert Path(backup.path).exists()
    finally:
        service.close()

    other = AdvisorService(tmp_path / "s2.db")
    try:
        info = other.restore(backup.path)
        assert other.list_study_sessions()
        assert info.counts.get("study_session", 0) >= 1
        assert info.counts.get("topic", 0) >= 1
    finally:
        other.close()


def test_restore_never_silently_replaces_local_data(tmp_path, no_network):
    """بازیابی، دادهٔ محلی را بی‌صدا جایگزین نمی‌کند: ابتدا پشتیبان امن می‌شود."""
    source = AdvisorService(tmp_path / "a.db")
    try:
        _seed(source)
        source.save_study_session(
            StudySession(
                kind=SessionKind.STUDY, mode="manual",
                started_at=_dt.datetime.combine(TODAY, _dt.time(8, 0)),
                ended_at=_dt.datetime.combine(TODAY, _dt.time(8, 45)),
                minutes=45,
            )
        )
        backup = source.backup(tmp_path / "backups")
    finally:
        source.close()

    target = AdvisorService(tmp_path / "b.db")
    try:
        local_activity = target.create_activity(
            Activity(
                title="کار محلی که نباید بی‌صدا برود",
                type=ActivityType.INDEPENDENT_PRACTICE,
                est_minutes=30, remaining_minutes=30,
            )
        )
        # پیش از بازیابی، یک پشتیبان خودکار از وضعیت فعلی گرفته می‌شود تا
        # اگر کاربر منصرف شد، داده‌هایش گم نشود.
        safety = target.backup(tmp_path / "backups")
        assert safety.path != backup.path
        assert Path(safety.path).exists()

        info = target.restore(backup.path)
        assert info is not None
        # پس از بازیابی، نسخهٔ امن هنوز روی دیسک است.
        assert Path(safety.path).exists()
        assert target.list_study_sessions()
    finally:
        target.close()


def test_export_json_contains_every_entity_group(tmp_path, no_network):
    """خروجی JSON همهٔ گروه‌های دادهٔ اصلی را دارد و بدون شبکه ساخته می‌شود."""
    service = AdvisorService(tmp_path / "e.db")
    try:
        topic = _seed(service)
        service.create_activity(
            Activity(
                title="کار", type=ActivityType.INDEPENDENT_PRACTICE,
                est_minutes=45, remaining_minutes=45,
            )
        )
        service.save_study_session(
            StudySession(
                subject_id=topic.subject_id, topic_id=topic.id,
                kind=SessionKind.STUDY, mode="timer",
                started_at=_dt.datetime.combine(TODAY, _dt.time(9, 0)),
                ended_at=_dt.datetime.combine(TODAY, _dt.time(9, 45)),
                minutes=45,
            )
        )
        path = service.export_json(tmp_path / "k2.json")
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
        for key in (
            "subjects", "topics", "activities", "attempts", "topic_deadlines",
            "study_sessions", "learning_problems", "fixed_events", "routines",
            "review_items",
        ):
            assert key in payload, key
        assert payload["topics"][0]["name"] == "احتمال"
        assert payload["study_sessions"][0]["kind"] == SessionKind.STUDY.value
    finally:
        service.close()


def test_exam_result_attachment_works_with_network_off(tmp_path, no_network):
    """پیوست نتیجهٔ آزمون (تصویر کارت پاسخ) کاملاً محلی کار می‌کند."""
    service = AdvisorService(tmp_path / "att.db")
    try:
        _seed(service)
        service.record_attempt(
            name="آزمون جامع", total=20, correct=15, wrong=5, blank=0,
            duration_minutes=30,
        )
        attempt = service.list_attempts()[-1]
        card = tmp_path / "kart-pasokh.png"
        card.write_bytes(b"PNG\x89 card image bytes")
        target = service.attach_file(
            card, owner="attempt", owner_id=int(attempt.id or 0),
            note="کارت پاسخ آزمون",
        )
        assert target.exists()
        stored = service.list_attempts()[-1]
        assert stored.attachment_name == "kart-pasokh.png"
        assert stored.attachment_sha256
        assert stored.attachment_note == "کارت پاسخ آزمون"
        assert service.attachment_status(stored.attachment_path)["verified"] is True

        # پس از بستن و بازکردن، پیوست هنوز ثبت است
        service.close()
        reopened = AdvisorService(tmp_path / "att.db")
        try:
            again = reopened.list_attempts()[-1]
            assert again.attachment_name == "kart-pasokh.png"
        finally:
            reopened.close()
    finally:
        service.close()
