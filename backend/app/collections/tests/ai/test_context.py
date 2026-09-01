from pathlib import Path

from app.collections.ai.context import workbook_readme_markdown

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent / "fixtures" / "dataset_a_original.xlsx"
)


def test_workbook_readme_markdown_extracts_only_the_readme_sheet() -> None:
    markdown = workbook_readme_markdown(FIXTURE_PATH)
    assert markdown.startswith("## README")
    assert "Report date" in markdown
    # Should not bleed into the next sheet's content.
    assert "## Customers" not in markdown
