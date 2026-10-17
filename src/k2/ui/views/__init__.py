"""نماهای رابط کاربری."""

from __future__ import annotations

from .activities import ActivitiesPage, AddActivityDialog
from .dashboard import DashboardPage
from .exams import ExamsPage, RecordAttemptDialog
from .onboarding import OnboardingWizard
from .reports import ReportsPage
from .review import ReviewPage
from .settings import SettingsPage
from .today import TodayPlanPage

__all__ = [
    "ActivitiesPage",
    "AddActivityDialog",
    "DashboardPage",
    "ExamsPage",
    "OnboardingWizard",
    "RecordAttemptDialog",
    "ReportsPage",
    "ReviewPage",
    "SettingsPage",
    "TodayPlanPage",
]
