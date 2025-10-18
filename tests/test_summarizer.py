import unittest

from src.summarizer import Summary, summarize_text, top_keywords


class SummarizerTests(unittest.TestCase):
    def test_summarize_text_prioritizes_informative_sentences(self) -> None:
        text = (
            "Revenue for the quarter reached $10 billion, growing 20 percent year over year. "
            "We expanded operating margin to 32 percent, supported by disciplined cost controls. "
            "Cash flow from operations totaled $3.5 billion, allowing us to repurchase $1 billion of shares. "
            "The company announced a new product line targeting enterprise clients. "
            "We remain focused on long-term growth opportunities across cloud and AI."
        )

        summary = summarize_text(text, sentence_limit=3)
        self.assertIsInstance(summary, Summary)
        self.assertLessEqual(len(summary.sentences), 3)
        self.assertTrue(
            any("Revenue for the quarter" in sentence for sentence in summary.sentences)
        )

    def test_top_keywords_filters_stopwords(self) -> None:
        keywords = top_keywords("the revenue increased and the revenue guidance improved")
        self.assertIn("revenue", keywords)
        self.assertNotIn("the", keywords)


if __name__ == "__main__":
    unittest.main()
