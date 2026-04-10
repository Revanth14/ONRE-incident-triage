import unittest
from unittest.mock import patch

from app.services import classifier
from app.services.extractor import regex_extract


def empty_llm_facts() -> dict[str, object]:
    return {
        "symptoms": [],
        "affected_services": [],
        "scope_qualifier": None,
        "severity_language": None,
        "explicit_layer": None,
    }


class ExtractorTests(unittest.TestCase):
    def test_auth_incident_is_not_marked_wireless_only(self) -> None:
        facts = regex_extract(
            "All London offices reporting users unable to authenticate. "
            "Both wired and wireless affected. RADIUS server alarms firing."
        )

        self.assertTrue(facts.has_auth_signals)
        self.assertFalse(facts.is_wireless_only)
        self.assertFalse(facts.wired_unaffected)

    def test_all_city_offices_counts_as_multi_site(self) -> None:
        facts = regex_extract("All London offices reporting users unable to authenticate.")

        self.assertTrue(facts.is_multi_site)
        self.assertGreaterEqual(facts.sites_count_estimate, 2)


class ClassifierTests(unittest.TestCase):
    def test_classify_uses_heuristics_when_api_key_missing(self) -> None:
        text = "Users across two offices cannot authenticate to the network. RADIUS alarms are firing."
        facts = regex_extract(text)

        with patch.object(classifier.settings, "openai_api_key", ""):
            result = classifier.classify(text, facts, empty_llm_facts(), None)

        self.assertEqual(result["primary_class"], "auth_802_1x")
        self.assertGreaterEqual(result["confidence"], 60)
        self.assertTrue(result["diagnostic_path"])

    def test_classify_handles_llm_failure_without_crashing(self) -> None:
        text = "Network is slow."
        facts = regex_extract(text)

        with (
            patch.object(classifier.settings, "openai_api_key", "test-key"),
            patch.object(classifier, "_call_llm_classifier", side_effect=RuntimeError("boom")),
        ):
            result = classifier.classify(text, facts, empty_llm_facts(), None)

        self.assertEqual(result["primary_class"], "insufficient_information")
        self.assertEqual(result["subtype"], "vague_description")


if __name__ == "__main__":
    unittest.main()
