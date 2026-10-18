"""تست‌های پایگاه شواهد علمی یادگیری."""

from __future__ import annotations

import pytest

from k2 import learning_science as ls


class TestEvidenceCatalog:
    def test_all_evidence_have_unique_ids(self):
        ids = list(ls.EVIDENCE)
        assert len(ids) == len(set(ids))

    def test_required_fields_present(self):
        for item in ls.EVIDENCE.values():
            assert item.id
            assert item.title
            assert item.authors
            assert 1980 <= item.year <= 2030
            assert item.finding
            assert item.url.startswith("http")
            assert item.design_rule

    def test_topic_index_points_to_existing_ids(self):
        for topic, ids in ls.EVIDENCE_TOPICS.items():
            for evidence_id in ids:
                assert evidence_id in ls.EVIDENCE, f"{topic} → {evidence_id}"

    def test_engine_used_evidence_exists_for_core_topics(self):
        # موضوع‌های هستهٔ موتور باید حداقل یک شوید «مصرف‌شده در موتور» داشته باشند.
        for topic in (
            "spacing",
            "retrieval",
            "interleaving",
            "consolidation",
            "memory_model",
        ):
            used = [e for e in ls.evidence_for_topic(topic) if e.used_in_engine]
            assert used, f"موضوع {topic} شوید مصرف‌شده ندارد"

    def test_evidence_lookup_and_cite(self):
        item = ls.evidence("SPACING-02")
        assert "Cepeda" in item.authors
        assert ls.cite("SPACING-02").endswith("(2008)")

    def test_unknown_id_raises(self):
        with pytest.raises(KeyError):
            ls.evidence("NOPE")

    def test_summary_lists_authors(self):
        summary = ls.evidence_summary(["TESTING-01", "SPACING-01"])
        assert "Roediger" in summary
        assert "Cepeda" in summary
        assert ls.evidence_summary([]) == ""
