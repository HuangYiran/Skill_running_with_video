import pathlib
import unittest


class ReadmeQualityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.readme_path = pathlib.Path(__file__).resolve().parents[1] / "README.md"

    def test_readme_exists(self) -> None:
        self.assertTrue(self.readme_path.exists(), "README.md should exist at repo root")

    def test_readme_has_required_sections(self) -> None:
        content = self.readme_path.read_text(encoding="utf-8")
        required_headers = [
            "## Overview",
            "## Current Repository Structure",
            "## Getting Started",
            "## Development Workflow",
            "## Testing",
            "## Contributing",
        ]
        for header in required_headers:
            self.assertIn(header, content, f"Missing expected section: {header}")

    def test_readme_has_meaningful_length(self) -> None:
        content = self.readme_path.read_text(encoding="utf-8").strip()
        self.assertGreater(
            len(content),
            600,
            "README.md should include sufficient detail (more than 600 characters).",
        )


if __name__ == "__main__":
    unittest.main()
