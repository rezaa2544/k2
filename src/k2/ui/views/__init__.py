"""نماهای رابط کاربری."""

from __future__ import annotations

from .activities import ActivitiesPage, AddActivityDialog
from .backlogs import BacklogsPage
from .classes import ClassesPage, FixedEventDialog, RoutineDialog
from .comprehensive import ComprehensiveExamsPage
from .consolidation import ConsolidationPage
from .course_bank import AddTopicDialog, CourseBankPage, EvidenceDialog
from .dashboard import DashboardPage
from .deadlines import DeadlineDialog, DeadlinesPage
from .exams import ExamsPage, RecordAttemptDialog
from .onboarding import OnboardingWizard
from .problems import LearningProblemsPage, ProblemDialog, ResolveDialog
from .reports import ReportsPage
from .review import ReviewPage
from .settings import SettingsPage
from .study_timer_page import (
    CorrectSessionDialog,
    ManualSessionDialog,
    StudyTimerPage,
)
from .tests_page import QuestionDialog, TestsPage
from .today import TodayPlanPage
from .weekly_plan import WeeklyPlanPage

__all__ = [
    "ActivitiesPage",
    "AddActivityDialog",
    "AddTopicDialog",
    "BacklogsPage",
    "ClassesPage",
    "ComprehensiveExamsPage",
    "ConsolidationPage",
    "CorrectSessionDialog",
    "CourseBankPage",
    "DashboardPage",
    "DeadlineDialog",
    "DeadlinesPage",
    "EvidenceDialog",
    "ExamsPage",
    "FixedEventDialog",
    "LearningProblemsPage",
    "ManualSessionDialog",
    "OnboardingWizard",
    "ProblemDialog",
    "QuestionDialog",
    "RecordAttemptDialog",
    "ReportsPage",
    "ResolveDialog",
    "ReviewPage",
    "RoutineDialog",
    "SettingsPage",
    "StudyTimerPage",
    "TestsPage",
    "TodayPlanPage",
    "WeeklyPlanPage",
]
