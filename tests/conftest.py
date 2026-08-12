from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def make_repo(tmp_path: Path):
    def create(files: dict[str, str | bytes], *, name: str = "repository") -> Path:
        root = tmp_path / name
        root.mkdir()
        for relative, content in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                path.write_bytes(content)
            else:
                path.write_text(content, encoding="utf-8", newline="\n")
        return root

    return create


def finding(report, finding_id: str):
    return next(item for item in report.findings if item.id == finding_id)


def category_score(report, category_id: str) -> int:
    return next(item["score"] for item in report.scores["categories"] if item["id"] == category_id)
