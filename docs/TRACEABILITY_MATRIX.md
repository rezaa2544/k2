# ماتریس ردیابی — K2

تاریخ: ۱۴۰۵/۰۷/۲۴ (2026-10-17)
ستون «تست» نام فایل/تابع واقعی در `tests/` است. ستون «وضعیت» یکی از:
**کامل** (پیاده‌سازی + تست)، **جزئی** (هسته پیاده شده ولی بخشی از متن نیازمندی پوشش داده نشده)، **عمدی-انجام‌نشده** (با دلیل)، **انجام‌نشده**.

---

## ۱. راه‌اندازی و پروفایل

| شناسه | اولویت | پیاده‌سازی | تست | وضعیت |
|---|---|---|---|---|
| ONB-01 | P0 | `onboarding.py` (OnboardingState، ۱۲ گام)، `ui/views/onboarding.py` | `test_onboarding.py::test_state_is_resumable`، `test_gui.py::test_onboarding_wizard_saves_state` | کامل |
| ONB-02 | P0 | `domain/models.py::ExamProfile`، `service.py::create_exam_profile`، `onboarding.py::ONBOARDING_STEPS` | `test_onboarding.py::test_onboarding_steps_cover_required_areas`، `test_edge_cases.py::test_exam_date_change_is_reflected_in_review_cap` | کامل |
| ONB-03 | P0 | `onboarding.py::build_sample_fixed_events/build_sample_routines/detect_sample_conflicts`، `capacity.py::collect_fixed_intervals` | `test_onboarding.py::test_sample_schedule_contains_all_week_days`، `test_sunday_conflict_is_detected_and_not_hidden`، `test_imported_schedule_affects_capacity` | کامل |
| ONB-04 | P0 | `advisor_engine.py::assess_mastery` (L0–L4 با اطمینان)، `ui/views/onboarding.py` | `test_advisor.py::test_mastery_from_diagnostic_evidence`، `test_mastery_without_evidence_is_l0_with_low_confidence` | کامل |
| ONB-05 | P1 | `exam_analysis.py` + `ui/views/exams.py` (ورود نتیجهٔ آزمون قبلی) | `test_e2e_scenario.py::test_full_learning_cycle` | کامل |

## ۲. تقویم، بومی‌سازی و ذخیره‌سازی

| شناسه | اولویت | پیاده‌سازی | تست | وضعیت |
|---|---|---|---|---|
| CAL-01 | P0 | `jdate.py` (تبدیل، هفتهٔ شنبه‌محور، سال کبیسه) | `test_jdate.py` (۱۰ تست شامل `test_leap_year`، `test_week_starts_on_saturday`، `test_roundtrip_over_many_dates`) | کامل |
| CAL-02 | P0 | `ui/theme.py` (RTL، فونت وزیرمتن)، `ui/widgets.py`، `jdate.py::persian_digits` | `test_gui.py::test_application_layout_is_rtl`، `test_persian_font_is_loaded`، `test_jdate.py::test_persian_digits` | کامل |
| CAL-03 | P0 | `domain/models.py::FixedEvent` (تکرارشونده/یک‌باره/ضبط‌شده)، `Routine` | `test_onboarding.py::test_sample_schedule_contains_recorded_geology_class`، `test_edge_cases.py::test_overlapping_classes_are_detected_but_not_silently_dropped` | کامل |
| DATA-01 | P0 | `storage/db.py`، `storage/repositories.py` (بدون هیچ مسیر شبکه) | `test_storage.py::test_database_works_offline_without_network`، `test_e2e_scenario.py::test_offline_operation_without_network` | کامل |
| DATA-02 | P0 | `storage/backup.py` (پشتیبان آنلاین + فراداده + بازیابی مرحله‌ای)، `storage/schema.py` | `test_storage.py::test_backup_and_restore_roundtrip`، `test_backup_inspection_detects_healthy_file`، `test_restore_rejects_newer_schema` | کامل |
| DATA-03 | P1 | `reporting.py::export_activities_csv/export_attempts_csv` | `test_reporting.py::test_export_activities_csv`، `test_export_attempts_csv` | **جزئی** — خروجی PDF پیاده نشده (L-8) |

## ۳. ظرفیت و زمان‌بندی

| شناسه | اولویت | پیاده‌سازی | تست | وضعیت |
|---|---|---|---|---|
| CAP-01 | P0 | `capacity.py::compute_capacity` | `test_capacity.py::test_capacity_baseline`، `test_capacity_subtracts_classes_and_routines_once`، `test_overlapping_events_counted_once`، `test_energy_levels_change_capacity` | کامل |
| CAP-02 | P0 | `capacity.py::CapacityBreakdown` (raw/effective/margin)، `ui/views/dashboard.py` (کاشی‌ها) | `test_capacity.py::test_capacity_baseline`، `test_gui.py::test_pages_render_with_real_data` | کامل |
| CAP-03 | P0 | `capacity.py` + `scheduler.py` (بازه‌های ممنوع) | `test_scheduler.py::test_nothing_is_scheduled_during_sleep`، `test_nothing_is_scheduled_on_top_of_a_class`، `test_capacity.py::test_sleep_is_never_available` | کامل |
| SCH-01 | P0 | `scheduler.py::score_priority` + `Placement.reason` | `test_scheduler.py::test_placement_carries_reason`، `test_hard_deadline_activity_is_scheduled_first` | کامل |
| SCH-02 | P0 | `scheduler.py::plan_day` | `test_scheduler.py::test_no_overlap_between_placements`، `test_non_splittable_activity_needs_contiguous_block` | کامل |
| SCH-03 | P0 | `scheduler.py` → `DayPlan.unplaced` با دلیل | `test_scheduler.py::test_unplaced_activities_are_reported_with_reason`، `test_past_hard_deadline_is_reported_not_hidden` | کامل |
| SCH-04 | P0 | `scheduler.py::plan_range` (بازبرنامه‌ریزی + حفظ باقی‌مانده)، `activity_lifecycle.py` | `test_scheduler.py::test_plan_range_carries_unplaced_activities_forward`، `test_edge_cases.py::test_exam_date_change_is_reflected_in_review_cap` | کامل |
| SCH-05 | P0 | `scheduler.py` (اولویت پایدار)، `config.py` (سقف بازچینی خودکار) | `test_invariants.py::test_activity_never_disappears_across_a_week` | کامل |
| SCH-06 | P1 | — | — | **عمدی-انجام‌نشده** (D-007: مشروط به بنچمارک) |
| EST-01 | P0 | `domain/models.py::Activity.est_minutes/actual_minutes`، `estimation.py` | `test_reporting.py::test_weekly_report_flags_underestimation` | کامل |
| EST-02 | P0 | `estimation.py::estimate_minutes` (p70، حداقل ۵ نمونه، پیش‌فرض ۱.۳) | `test_reporting.py::test_weekly_report_flags_underestimation`، `test_edge_cases.py::test_large_review_dataset_does_not_break` | کامل |

## ۴. مدل فعالیت و عقب‌افتادگی

| شناسه | اولویت | پیاده‌سازی | تست | وضعیت |
|---|---|---|---|---|
| ACT-01 | P0 | `domain/models.py::Activity` (درس/مبحث/نوع/تخمین/واقعی/باقی‌مانده/تقسیم/وابستگی/مهلت/انرژی/وضعیت) | `test_activity_lifecycle.py` (۱۳ تست) | کامل |
| ACT-02 | P0 | `domain/state_machine.py` (۱۰ وضعیت + جدول گذار) | `test_activity_lifecycle.py::test_every_state_has_a_transition_entry`، `test_valid_transitions`، `test_invalid_transition_raises`، `test_terminal_states_have_no_outgoing_transitions` | کامل |
| ACT-03 | P0 | `activity_lifecycle.py::partial_activity` (باقی‌مانده + نقطه توقف) | `test_activity_lifecycle.py::test_partial_activity_keeps_remaining_and_marker`، `test_invariants.py::test_remaining_minutes_are_preserved_for_partial_placement` | کامل |
| ACT-04 | P0 | `activity_lifecycle.py::defer_activity/drop_activity` + `storage/repositories.py::log_activity_event` | `test_activity_lifecycle.py::test_defer_and_drop_require_reason`، `test_defer_records_reason`، `test_e2e_scenario.py::test_no_activity_is_silently_dropped` | کامل |
| BL-01 | P0 | `backlog.py` (زمان بدهی، سن، مهلت، مسدودها) | `test_edge_cases.py::test_backlog_levels` | کامل |
| BL-02 | P0 | `config.py` (آستانه‌های ۰.۳/۰.۷/۱.۰ و سقف ۳۰٪) | `test_edge_cases.py::test_backlog_levels`، `test_backlog_with_zero_capacity_is_red` | کامل |
| BL-03 | P0 | `backlog.py::triage` (سه سطل) | `test_edge_cases.py::test_triage_splits_into_three_buckets` | کامل |
| BL-04 | P0 | `backlog.py::minimal_day`، `recovery_after_break` | `test_edge_cases.py::test_minimal_day_is_small_and_contains_no_heavy_new_work`، `test_return_after_break_reduces_load`، `test_return_after_break_without_break_keeps_capacity` | کامل |
| BL-05 | P1 | `backlog.py` (هشدار ازدحام) + `reporting.py` | `test_edge_cases.py::test_backlog_with_zero_capacity_is_red` | **جزئی** — هشدار متنی وجود دارد، پیش‌بینی کمیّ نیست |

## ۵. یادگیری و مرور

| شناسه | اولویت | پیاده‌سازی | تست | وضعیت |
|---|---|---|---|---|
| LRN-01 | P0 | `domain/models.py::Subject/Topic`، `domain/learning.py` (نوع محتوا) | `test_advisor.py::test_prescription_creates_activities_with_criteria` | کامل |
| LRN-02 | P0 | `domain/learning.py::PRESCRIPTION_MATRIX`، `service.py` | `test_advisor.py::test_prescription_matrix_has_all_phase_level_cells`، `test_e2e_scenario.py::test_full_learning_cycle` | کامل |
| LRN-03 | P0 | `domain/enums.py::ActivityType` (کلاس/پردازش/مثال/تمرین/تست/تحلیل) | `test_e2e_scenario.py::test_full_learning_cycle` | کامل |
| REV-01 | P0 | `domain/models.py::ReviewItem`، `review_engine.py` | `test_review_engine.py` (۱۷ تست) | کامل |
| REV-02 | P0 | `review_engine.py::next_interval` + سقف ۳۶۵ روز و سقف وابسته به آزمون | `test_review_engine.py::test_interval_capped_by_days_to_exam`، `test_failed_review_resets_interval_and_increases_lapse`، `test_repeated_failures_mark_item_as_leech` | کامل |
| REV-03 | P1 | `review_engine.py` (تشخیص فراموشی تکراری) + `reporting.py::repeated_error_rate` | `test_review_engine.py::test_overdue_item_needs_retention_check`، `test_reporting.py::test_repeated_error_rate` | کامل |
| REV-04 | P1 | `review_engine.py::maintenance_state` + `retention_check` | `test_review_engine.py::test_maintenance_state_after_success_streak`، `test_retention_signal_detects_drop` | کامل |
| MAST-01 | P0 | `advisor_engine.py::assess_mastery` (L0–L4، اطمینان، خودسنجی ناکافی) | `test_advisor.py::test_mastery_from_diagnostic_evidence`، `test_self_report_alone_has_low_confidence`، `test_mastery_low_score_is_l1` | کامل |
| SUB-01 | P0 | `domain/learning.py` (انواع محتوای حفظی/مفهومی/محاسباتی/متنی/واژگان) | `test_advisor.py::test_prescription_creates_activities_with_criteria` | کامل |
| SUB-02 | P1 | `domain/learning.py::PRESCRIPTION_MATRIX` (عمومی) | `test_advisor.py::test_prescription_matrix_has_all_phase_level_cells` | **جزئی** — ماتریس عمومی پیاده شده، نه جدول اختصاصی هر ۹ درس (L-9) |

## ۶. آزمون و تحلیل خطا

| شناسه | اولویت | پیاده‌سازی | تست | وضعیت |
|---|---|---|---|---|
| EX-01 | P0 | `domain/models.py::ExamAttempt`، `exam_analysis.py::score_attempt` | `test_exam_analysis.py::test_raw_percentage`، `test_negative_marking_percentage` | کامل |
| EX-02 | P0 | `domain/models.py::ExamQuestion` (درست/غلط/نزده + مبحث) | `test_exam_analysis.py::test_error_breakdown_counts_codes` | کامل |
| ERR-01 | P0 | `domain/enums.py::ErrorCode` (E1–E9)، `domain/learning.py::REMEDIATION_MAP` | `test_exam_analysis.py::test_error_breakdown_counts_codes`، `test_repeated_errors_are_detected` | **جزئی** — مجموعهٔ ثابت است، «نسخه‌بندی‌شده» نه (L-10) |
| ERR-02 | P0 | `exam_analysis.py::build_remediation` (فعالیت اصلاحی + مهلت) | `test_exam_analysis.py::test_remediation_creates_activities_with_deadlines`، `test_e2e_scenario.py::test_full_learning_cycle` | کامل |
| ERR-03 | P1 | `reporting.py::repeated_error_rate`، `exam_analysis.py::topic_weakness` | `test_exam_analysis.py::test_topic_weakness_uses_weight`، `test_reporting.py::test_repeated_error_rate` | کامل |
| EX-03 | P1 | `ui/views/exams.py` (شبیه‌سازی زمان‌دار) | `test_exam_analysis.py::test_exam_kind_labels_are_distinct` | **جزئی** — ورودی زمان‌دار ثبت می‌شود، شبیه‌سازی کامل سؤال‌به‌سؤال نه |

## ۷. موتور مشاور و گزارش‌ها

| شناسه | اولویت | پیاده‌سازی | تست | وضعیت |
|---|---|---|---|---|
| ADV-01 | P0 | `advisor_engine.py::detect_bottleneck` | `test_advisor.py::test_bottleneck_knowledge/method/speed/execution/none` | کامل |
| ADV-02 | P0 | `advisor_engine.py::prescribe_for_topic` (فاز × سطح × گلوگاه) | `test_advisor.py::test_prescription_creates_activities_with_criteria` | کامل |
| ADV-03 | P0 | `advisor_engine.py::next_action` (+ دلیل)، `ui/views/dashboard.py` | `test_advisor.py::test_next_action_has_a_reason` | کامل |
| ADV-04 | P1 | `reporting.py::build_weekly_report` | `test_reporting.py::test_weekly_report_computes_adherence`، `test_weekly_report_flags_underestimation` | کامل |
| ADV-05 | P1 | `reporting.py::pressure_signal` (غیرتشخیصی) | `test_reporting.py::test_pressure_signal_activates_and_is_non_diagnostic`، `test_pressure_signal_is_inactive_without_patterns` | کامل |
| BEH-01 | P0 | `backlog.py::minimal_day`، `recovery_after_break` | `test_edge_cases.py::test_minimal_day_is_small_and_contains_no_heavy_new_work`، `test_return_after_break_reduces_load` | کامل |
| BEH-02 | P1 | `scheduler.py` (تقسیم فعالیت بزرگ به بلوک) + `ui/views/dashboard.py` (کار بعدی) | `test_scheduler.py::test_splittable_activity_is_split_across_blocks` | کامل |
| BEH-03 | P2 | — | — | **انجام‌نشده** (اختیاری/آزمایشی در سند مبدأ) |
| NFR-01 | P0 | بدون استریک/رقابت/رتبه در `reporting.py` و `ui/` | `test_reporting.py::test_no_streak_or_ranking_language_in_reports` | کامل |
| NFR-02 | P0 | بدون چت‌بات آزاد؛ هیچ وابستگی شبکه‌ای | `test_e2e_scenario.py::test_offline_operation_without_network` | کامل |

## ۸. کیفیت و بسته‌بندی

| شناسه | اولویت | پیاده‌سازی | تست | وضعیت |
|---|---|---|---|---|
| QA-01 | P0 | ۱۴ فایل تست، ۱۷۰ تست | `test_jdate`، `test_capacity`، `test_scheduler`، `test_activity_lifecycle`، `test_review_engine`، `test_exam_analysis`، `test_gui.py::test_navigation_and_dashboard_have_clear_visual_hierarchy` | کامل |
| QA-02 | P0 | `tests/test_e2e_scenario.py::test_full_learning_cycle` | همان تست | کامل |
| QA-03 | P0 | `tests/test_invariants.py`، `tests/test_edge_cases.py` | `test_invariants_hold_for_random_schedules` (۵ seed)، `test_capacity_never_exceeded_over_a_week`، `test_no_activity_is_scheduled_in_the_past` | کامل |
| QA-04 | P0 | `tests/test_storage.py` | `test_backup_and_restore_roundtrip`، `test_migration_from_v1_preserves_data` | کامل |
| QA-05 | P0 | `k2.spec`، `packaging/build_windows.ps1`، `.github/workflows/build-windows.yml` | `packaging/output/K2/K2.exe` (اجرا شد زیر Wine) | **جزئی** — build و اجرا زیر Wine تأیید شد؛ **ویندوز فیزیکی تأیید نشده** (L-1، L-2) |
| QA-06 | P0 | `config.py` (همهٔ اعداد با برچسب `[H]`)، `ui/views/settings.py` | `test_advisor.py::test_phase_boundaries_are_configurable`، `test_edge_cases.py::test_exam_date_change_is_reflected_in_review_cap` | کامل |

---

## ۹. جمع‌بندی

| وضعیت | تعداد |
|---|---|
| کامل | ۴۸ |
| جزئی | ۶ (DATA-03، BL-05، SUB-02، ERR-01، EX-03، QA-05) |
| عمدی-انجام‌نشده | ۱ (SCH-06) |
| انجام‌نشده | ۱ (BEH-03) |
| **مجموع** | **۵۶** |

هر مورد «جزئی» یا «انجام‌نشده» در [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) با شمارهٔ محدودیت ثبت شده است.
