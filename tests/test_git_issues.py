from __future__ import annotations
import json
from pathlib import Path

import pytest

from src.services.git_issues import GitIssuesStore


@pytest.fixture()
def issues_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "GIT_ISSUES.md"
    file_path.write_text(
        "\n".join(
            [
                "- [ ] ISSUE-1: Add login | assignee=alice | labels=backend, auth",
                "- [x] ISSUE-2: Document API",
                "- [ ] ISSUE-3: Improve anomaly scoring",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return file_path


def test_list_open_issues(issues_file: Path) -> None:
    store = GitIssuesStore(issues_file)
    open_issues = store.list_open_issues()
    assert {issue.id for issue in open_issues} == {"ISSUE-1", "ISSUE-3"}


def test_close_and_complete_markdown(issues_file: Path) -> None:
    store = GitIssuesStore(issues_file)

    closed_issue = store.close_issue("ISSUE-1")
    assert closed_issue.status == "closed"

    completed = store.complete_open_issues()
    assert {issue.id for issue in completed} == {"ISSUE-3"}

    content = issues_file.read_text(encoding="utf-8")
    assert "- [x] ISSUE-1" in content
    assert "- [/] ISSUE-3" in content


def test_json_issue_store(tmp_path: Path) -> None:
    issues_payload = [
        {"id": "ISSUE-10", "title": "Initial setup", "status": "open"},
        {"id": "ISSUE-11", "title": "Add docs", "status": "open"},
    ]
    issues_json = tmp_path / "issues.json"
    issues_json.write_text(json.dumps(issues_payload), encoding="utf-8")

    store = GitIssuesStore(issues_json)
    updated = store.close_implemented_issues(["ISSUE-11"])
    assert [issue.id for issue in updated] == ["ISSUE-11"]

    new_payload = json.loads(issues_json.read_text(encoding="utf-8"))
    statuses = {entry["id"]: entry["status"] for entry in new_payload}
    assert statuses == {"ISSUE-10": "open", "ISSUE-11": "closed"}


def test_unknown_issue_raises(issues_file: Path) -> None:
    store = GitIssuesStore(issues_file)
    with pytest.raises(ValueError):
        store.close_issue("ISSUE-404")
