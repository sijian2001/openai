import unittest

from src.parser.html_text import chunk_sections, extract_text


class ParserHTMLTextTests(unittest.TestCase):
    def test_extract_text_ignores_script_and_styles(self) -> None:
        html = """
        <html>
            <head>
                <style>body { color: red; }</style>
                <script>console.log('ignore');</script>
            </head>
            <body>
                <div>Revenue increased 10% year over year.</div>
                <div>Net income totaled $2B.</div>
            </body>
        </html>
        """
        text = extract_text(html)
        self.assertIn("Revenue increased 10% year over year.", text)
        self.assertNotIn("console.log", text)

    def test_chunk_sections_respects_max_length(self) -> None:
        text = " ".join(f"Sentence {i} describing revenue growth." for i in range(10))
        chunks = list(chunk_sections(text, max_length=120))
        self.assertGreater(len(chunks), 1)


if __name__ == "__main__":
    unittest.main()
