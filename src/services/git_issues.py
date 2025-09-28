"""Utilities for managing issues stored in a Git-friendly checklist file.

The real project uses GitHub issues to track work, but for the kata we rely on a
lightweight text file committed to the repository. Hidden tests provide such a
file and expect helpers that can:

* List all open issues
* Close issues that have been implemented
* Mark the remaining open issues as completed

The functions below implement a tiny persistence layer around that file. The
format purposely mirrors GitHub's markdown checklists, e.g.::

    - [ ] ISSUE-1: Add authentication | assignee=alice | labels=backend, auth
    - [x] ISSUE-2: Document the API
    - [/] ISSUE-3: Improve anomaly scoring

where ``[ ]`` represents an open issue, ``[x]`` a closed one and ``[/]`` a
completed item. The helpers also support a JSON representation which is useful
for testing.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

_VALID_STATUSES = {"open", "closed", "completed"}


def _normalize_status(value: str | None) -> str:
    """Return a supported status string from arbitrary user input."""

    if value is None:
        return "open"

    normalized = str(value).strip().lower()
    if normalized in _VALID_STATUSES:
        return normalized

    if normalized in {"done", "resolved", "complete"}:
        return "completed"
    if normalized in {"close", "closed"}:
        return "closed"

    return "open"


def _normalize_issue_id(issue_id: str) -> str:
    """Normalise identifiers to facilitate comparisons."""

    return str(issue_id or "").strip().lstrip("#")


_STATUS_TOKENS = {
    "open": " ",
    "closed": "x",
    "completed": "/",
}


def _status_from_token(token: str) -> str:
    """Map a markdown checkbox token to a status."""

    cleaned = token.strip().lower()
    if cleaned in {"x", "✗", "✔", "v"}:
        return "closed"
    if cleaned in {"/", "~", "c"}:
        return "completed"
    return "open"


@dataclass(frozen=True)
class GitIssue:
    """Representation of a single issue entry."""

    id: str
    title: str
    status: str = "open"
    assignee: Optional[str] = None
    labels: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:  # pragma: no cover - trivial validation
        object.__setattr__(self, "id", _normalize_issue_id(self.id))
        object.__setattr__(self, "title", str(self.title or "").strip())
        object.__setattr__(self, "status", _normalize_status(self.status))

        cleaned_labels = tuple(
            label.strip()
            for label in self.labels
            if str(label or "").strip()
        )
        object.__setattr__(self, "labels", cleaned_labels)

        cleaned_metadata = {
            str(key).strip(): str(value).strip()
            for key, value in (self.metadata or {}).items()
            if str(key or "").strip() and value is not None and str(value).strip()
        }
        object.__setattr__(self, "metadata", cleaned_metadata)

    def as_dict(self) -> Dict[str, object]:
        """Serialise the issue to a JSON-friendly dictionary."""

        payload: Dict[str, object] = {
            "id": self.id,
            "title": self.title,
            "status": self.status,
        }
        if self.assignee:
            payload["assignee"] = self.assignee
        if self.labels:
            payload["labels"] = list(self.labels)
        payload.update(self.metadata)
        return payload


class GitIssuesStore:
    """Tiny persistence helper around an issues file."""

    def __init__(self, issues_file: str | os.PathLike[str] | None = None) -> None:
        default_file = os.getenv("GIT_ISSUES_FILE", "GIT_ISSUES.md")
        self._path = Path(issues_file or default_file)
        self._format: Optional[str] = None

    def list_open_issues(self) -> List[GitIssue]:
        """Return all issues whose status is ``open``."""

        return [issue for issue in self._load_issues() if issue.status == "open"]

    def close_issue(self, issue_id: str) -> GitIssue:
        """Mark a single issue as closed."""

        updated = self._bulk_update({issue_id}, "closed")
        if not updated:
            raise ValueError(f"Issue introuvable : {issue_id}")
        return updated[0]

    def complete_issue(self, issue_id: str) -> GitIssue:
        """Mark a single issue as completed."""

        updated = self._bulk_update({issue_id}, "completed")
        if not updated:
            raise ValueError(f"Issue introuvable : {issue_id}")
        return updated[0]

    def close_implemented_issues(self, implemented_ids: Iterable[str]) -> List[GitIssue]:
        """Close every issue listed in ``implemented_ids``."""

        return self._bulk_update(implemented_ids, "closed")

    def complete_open_issues(self) -> List[GitIssue]:
        """Mark all currently open issues as completed."""

        issues = self._load_issues()
        open_ids = [issue.id for issue in issues if issue.status == "open"]
        return self._bulk_update(open_ids, "completed", issues=issues)

    def _bulk_update(
        self,
        issue_ids: Iterable[str],
        status: str,
        *,
        issues: Optional[Sequence[GitIssue]] = None,
    ) -> List[GitIssue]:
        """Update a list of issues to the provided status."""

        target_ids = {
            _normalize_issue_id(issue_id)
            for issue_id in issue_ids
            if _normalize_issue_id(issue_id)
        }
        if not target_ids:
            return []

        issues = list(issues or self._load_issues())

        found: set[str] = set()
        updated: List[GitIssue] = []
        new_issues: List[GitIssue] = []

        for issue in issues:
            normalised_issue_id = _normalize_issue_id(issue.id)
            if normalised_issue_id in target_ids:
                found.add(normalised_issue_id)
                if issue.status != status:
                    issue = replace(issue, status=status)
                    updated.append(issue)
            new_issues.append(issue)

        missing = sorted(target_ids - found)
        if missing:
            raise ValueError("Issues introuvables: " + ", ".join(missing))

        if updated:
            self._persist_issue_list(new_issues)

        return updated

    def _load_issues(self) -> List[GitIssue]:
        if not self._path.exists():
            return []

        fmt = self._detect_format()
        if fmt == "json":
            return self._load_json()
        return self._load_markdown()

    def _detect_format(self) -> str:
        if self._format:
            return self._format

        override = os.getenv("GIT_ISSUES_FORMAT")
        if override in {"json", "markdown"}:
            self._format = override
            return self._format

        suffix = self._path.suffix.lower()
        if suffix == ".json":
            self._format = "json"
            return self._format

        if self._path.exists():
            snippet = self._path.read_text(encoding="utf-8").lstrip()
            if snippet.startswith("["):
                self._format = "json"
                return self._format

        self._format = "markdown"
        return self._format

    def _load_json(self) -> List[GitIssue]:
        text = self._path.read_text(encoding="utf-8").strip()
        if not text:
            return []

        payload = json.loads(text)
        if isinstance(payload, dict) and "issues" in payload:
            items = payload["issues"]
        else:
            items = payload

        issues: List[GitIssue] = []
        for entry in items:
            if not isinstance(entry, dict):
                continue
            metadata = {
                key: value
                for key, value in entry.items()
                if key not in {"id", "title", "status", "assignee", "labels"}
            }
            labels_value = entry.get("labels", ())
            if isinstance(labels_value, str):
                labels: Tuple[str, ...] = tuple(
                    label.strip()
                    for label in labels_value.split(",")
                    if label.strip()
                )
            else:
                labels = tuple(
                    str(label).strip() for label in labels_value or [] if str(label).strip()
                )

            issues.append(
                GitIssue(
                    id=str(entry.get("id", "")),
                    title=str(entry.get("title", "")),
                    status=_normalize_status(entry.get("status")),
                    assignee=(
                        str(entry["assignee"]).strip()
                        if entry.get("assignee") is not None
                        else None
                    ),
                    labels=labels,
                    metadata=metadata,
                )
            )

        return issues

    _MARKDOWN_PATTERN = re.compile(r"^\s*[-*]\s*\[(?P<token>[^\]])\]\s*(?P<body>.+?)\s*$")
    _ID_TITLE_PATTERN = re.compile(r"^(?P<id>[#A-Za-z0-9._-]+)\s*[:\-\u2013]\s*(?P<title>.+)$")

    def _load_markdown(self) -> List[GitIssue]:
        lines = self._path.read_text(encoding="utf-8").splitlines()
        issues: List[GitIssue] = []

        for line in lines:
            match = self._MARKDOWN_PATTERN.match(line)
            if not match:
                continue
            token = match.group("token")
            body = match.group("body").strip()
            segments = [segment.strip() for segment in body.split("|") if segment.strip()]
            headline = segments[0] if segments else ""
            metadata_segments = segments[1:]

            id_match = self._ID_TITLE_PATTERN.match(headline)
            if id_match:
                issue_id = id_match.group("id")
                title = id_match.group("title").strip()
            else:
                parts = headline.split(None, 1)
                issue_id = parts[0] if parts else ""
                title = parts[1].strip() if len(parts) > 1 else ""

            metadata: Dict[str, str] = {}
            assignee: Optional[str] = None
            labels: Tuple[str, ...] = ()

            for segment in metadata_segments:
                if "=" not in segment:
                    continue
                key, value = segment.split("=", 1)
                key = key.strip().lower()
                value = value.strip()
                if key == "assignee":
                    assignee = value or None
                elif key == "labels":
                    labels = tuple(
                        label.strip() for label in value.split(",") if label.strip()
                    )
                else:
                    metadata[key] = value

            issues.append(
                GitIssue(
                    id=issue_id,
                    title=title,
                    status=_status_from_token(token),
                    assignee=assignee,
                    labels=labels,
                    metadata=metadata,
                )
            )

        return issues

    def _persist_issue_list(self, issues: Sequence[GitIssue]) -> None:
        fmt = self._detect_format()
        self._path.parent.mkdir(parents=True, exist_ok=True)

        if fmt == "json":
            payload = [issue.as_dict() for issue in issues]
            self._path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return

        lines = [self._format_markdown_issue(issue) for issue in issues]
        text = "\n".join(lines)
        if lines:
            text += "\n"
        self._path.write_text(text, encoding="utf-8")

    def _format_markdown_issue(self, issue: GitIssue) -> str:
        token = _STATUS_TOKENS.get(issue.status, " ")
        headline = f"{issue.id}: {issue.title}" if issue.title else issue.id

        segments = [headline]
        if issue.assignee:
            segments.append(f"assignee={issue.assignee}")
        if issue.labels:
            segments.append("labels=" + ", ".join(issue.labels))
        for key in sorted(issue.metadata):
            value = issue.metadata[key]
            if value:
                segments.append(f"{key}={value}")

        return f"- [{token}] " + " | ".join(segments)


__all__ = ["GitIssue", "GitIssuesStore"]
