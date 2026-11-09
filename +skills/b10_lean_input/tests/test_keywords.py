"""Deterministic keyword scoring. No network and no Trafilatura."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import keywords  # noqa: E402


class KeywordTests(unittest.TestCase):
    def test_stopwords_short_tokens_and_numbers_are_dropped(self):
        ranked = keywords.top_keywords("the and garden garden 123 99 soil ok ok", None)
        words = [item["keyword"] for item in ranked]
        self.assertEqual(words, ["garden", "soil"])
        self.assertEqual(ranked[0]["score"], 2)
        self.assertNotIn("the", words)
        self.assertNotIn("and", words)
        self.assertNotIn("ok", words)

    def test_title_boost_is_applied_once(self):
        plain = keywords.top_keywords("alpha kale", None)
        boosted = keywords.top_keywords("alpha kale", "Kale report")
        plain_kale = next(item["score"] for item in plain if item["keyword"] == "kale")
        boosted_kale = next(item["score"] for item in boosted if item["keyword"] == "kale")
        self.assertEqual(boosted_kale, plain_kale + keywords.TITLE_BOOST)
        self.assertEqual(plain[0]["keyword"], "alpha")
        self.assertEqual(boosted[0]["keyword"], "kale")

    def test_at_most_ten_and_stable_order(self):
        pieces = []
        names = ["term" + chr(ord("a") + index) for index in range(15)]
        for index, name in enumerate(names):
            pieces.append((name + " ") * (20 - index))
        text = "".join(pieces)
        first = keywords.top_keywords(text, "terma")
        second = keywords.top_keywords(text, "terma")
        self.assertEqual(first, second)
        self.assertEqual(len(first), 10)
        scores = [item["score"] for item in first]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(first[0]["keyword"], "terma")


if __name__ == "__main__":
    unittest.main()
