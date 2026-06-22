"""Schema utility tests."""

from src.llm.schema_utils import strip_json_markdown


def test_strip_json_markdown_removes_fences():
    raw = """```json
{"sentiment": "negative"}
```"""
    assert strip_json_markdown(raw) == '{"sentiment": "negative"}'
