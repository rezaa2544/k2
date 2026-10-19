"""نماهای رابط کاربری."""

from __future__ import annotations

from .activities import ActivitiesPage, AddActivityDialog
from .consolidation import ConsolidationPage
from .dashboard import DashboardPage
from .exams import ExamsPage, RecordAttemptDialog
from .onboarding import OnboardingWizard
from .reports import ReportsPage
from .review import ReviewPage
from .settings import SettingsPage
from .today import TodayPlanPage
from .topics import TopicsPage

__all__ = [
    "ActivitiesPage",
    "AddActivityDialog",
    "ConsolidationPage",
    "DashboardPage",
    "ExamsPage",
    "OnboardingWizard",
    "RecordAttemptDialog",
    "ReportsPage",
    "ReviewPage",
    "SettingsPage",
    "TodayPlanPage",
    "TopicsPage",
]
