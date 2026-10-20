"""Evidence-only AISVS scorecard generation."""

from __future__ import annotations

import csv
import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from app.common import AISVS_ID, EVIDENCE, ROOT


SCORECARD = ROOT / "scorecard"
APPLICABILITY = ROOT / "applicability.yaml"


# Source evidence: only validated AISVS JSONL can influence scorecard status.
def _records(run: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted((EVIDENCE / run).glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record.get("run") != run or not isinstance(record.get("aisvs_ids"), list):
                raise ValueError("invalid_evidence_record")
            if any(AISVS_ID.fullmatch(item) is None for item in record["aisvs_ids"]):
                raise ValueError("invalid_evidence_id")
            records.append(record)
    return records


def load_applicability() -> dict[str, dict[str, str]]:
    """Return the declared not-applicable requirements mapped to their reason.

    Each value carries the category and its rationale. A requirement that could
    be exercised by the demo must never appear here.
    """
    document = yaml.safe_load(APPLICABILITY.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("format_version") != 1:
        raise ValueError("invalid_applicability_format")
    categories = document.get("categories")
    entries = document.get("not_applicable")
    if not isinstance(categories, dict) or not isinstance(entries, dict):
        raise ValueError("invalid_applicability_format")
    resolved: dict[str, dict[str, str]] = {}
    for requirement, category in entries.items():
        if AISVS_ID.fullmatch(str(requirement)) is None:
            raise ValueError("invalid_applicability_id")
        if not isinstance(category, str) or category not in categories:
            raise ValueError("invalid_applicability_category")
        resolved[requirement] = {"category": category, "reason": " ".join(str(categories[category]).split())}
    return resolved


def _status(records: list[dict[str, Any]], requirement: str, run: str) -> str:
    matching = [record for record in records if requirement in record["aisvs_ids"]]
    if not matching:
        return "NOT TESTED"
    decisions = {record["decision"] for record in matching}
    if run == "A":
        return "FAIL" if decisions & {"EXECUTED", "ALLOWED", "FAIL"} else "NOT TESTED"
    return "PASS" if decisions & {"BLOCKED", "DENIED", "REVIEW", "ALLOWED"} else "NOT TESTED"


# Derivation: visual bundles and supporting artifacts are deliberately not inputs.
def build() -> dict[str, Any]:
    catalog = json.loads((SCORECARD / "requirements_v1.01.json").read_text(encoding="utf-8"))
    requirements = catalog["requirements"]
    known = {requirement["id"] for requirement in requirements}
    applicability = load_applicability()
    unknown = sorted(set(applicability) - known)
    if unknown:
        raise ValueError(f"applicability_unknown_requirements: {', '.join(unknown)}")
    records = {"A": _records("A"), "B": _records("B")}
    rows: list[dict[str, Any]] = []
    for requirement in requirements:
        na = applicability.get(requirement["id"])
        if na is None:
            rows.append({**requirement, "A": _status(records["A"], requirement["id"], "A"), "B": _status(records["B"], requirement["id"], "B"), "applicable": True})
        else:
            rows.append({**requirement, "A": "N/A", "B": "N/A", "applicable": False, "applicability_category": na["category"], "applicability_reason": na["reason"]})
    by_chapter: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_chapter[row["chapter"]].append(row)
    chapters = []
    for chapter, values in sorted(by_chapter.items()):
        applicable = [value for value in values if value["applicable"]]
        chapter_status = {}
        for run in ("A", "B"):
            tested = sum(value[run] != "NOT TESTED" for value in applicable)
            level_one = [value for value in applicable if value["level"] == 1]
            if not applicable:
                level = "N/A"
            elif level_one and all(value[run] == "PASS" for value in level_one):
                level = "L1"
            elif tested == 0:
                level = "NOT TESTED"
            else:
                level = "below L1"
            chapter_status[run] = {"level": level, "tested": tested, "applicable": len(applicable)}
        chapters.append({"chapter": chapter, **chapter_status})
    return {
        "catalog_status": catalog["source_status"],
        "requirements": rows,
        "chapters": chapters,
        "not_applicable": [
            {"id": row["id"], "chapter": row["chapter"], "category": row["applicability_category"], "reason": row["applicability_reason"]}
            for row in rows
            if not row["applicable"]
        ],
    }


def write() -> dict[str, Any]:
    report = build()
    markdown = ["# AISVS Evidence Scorecard", "", f"Catalog status: `{report['catalog_status']}`", "", "| Chapter | A | B |", "| --- | --- | --- |"]
    for chapter in report["chapters"]:
        markdown.append(f"| {chapter['chapter']} | {chapter['A']['level']} ({chapter['A']['tested']}/{chapter['A']['applicable']}) | {chapter['B']['level']} ({chapter['B']['tested']}/{chapter['B']['applicable']}) |")
    markdown.extend(["", "## Requirement Detail", "", "| Requirement | A | B |", "| --- | --- | --- |"])
    for row in report["requirements"]:
        markdown.append(f"| {row['id']} | {row['A']} | {row['B']} |")
    markdown.extend(["", "## Not Applicable", ""])
    if report["not_applicable"]:
        markdown.extend(["| Requirement | Category | Reason |", "| --- | --- | --- |"])
        for entry in report["not_applicable"]:
            markdown.append(f"| {entry['id']} | {entry['category']} | {entry['reason']} |")
    else:
        markdown.append("None declared.")
    markdown.extend(["", "Levels follow AISVS v1.01 definitions. This is a self-assessment of a demo system, not an audit. Requirements declared not applicable in `applicability.yaml` are excluded from the denominator; requirements not exercised by the demo are counted as NOT TESTED."])
    (SCORECARD / "out.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    chapter_rows = "\n".join(
        f"<tr><td>{html.escape(chapter['chapter'])}</td><td>{chapter['A']['level']} ({chapter['A']['tested']}/{chapter['A']['applicable']})</td><td>{chapter['B']['level']} ({chapter['B']['tested']}/{chapter['B']['applicable']})</td></tr>"
        for chapter in report["chapters"]
    )
    body = "\n".join(f"<tr><td>{html.escape(row['id'])}</td><td>{row['A']}</td><td>{row['B']}</td></tr>" for row in report["requirements"])
    na_rows = "\n".join(
        f"<tr><td>{html.escape(entry['id'])}</td><td>{html.escape(entry['category'])}</td><td>{html.escape(entry['reason'])}</td></tr>"
        for entry in report["not_applicable"]
    )
    page = (
        f"<!doctype html><meta charset=utf-8><title>AISVS Scorecard</title><h1>AISVS Evidence Scorecard</h1>"
        f"<p>{html.escape(report['catalog_status'])}</p>"
        f"<h2>Chapters</h2><table border=1><tr><th>Chapter</th><th>A</th><th>B</th></tr>{chapter_rows}</table>"
        f"<h2>Requirement Detail</h2><table border=1><tr><th>Requirement</th><th>A</th><th>B</th></tr>{body}</table>"
        f"<h2>Not Applicable</h2><table border=1><tr><th>Requirement</th><th>Category</th><th>Reason</th></tr>{na_rows}</table>"
    )
    (SCORECARD / "out.html").write_text(page, encoding="utf-8")
    with (SCORECARD / "delta.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["requirement_id", "chapter", "a_status", "b_status"], lineterminator="\n")
        writer.writeheader()
        for row in report["requirements"]:
            if row["A"] == "FAIL" and row["B"] == "PASS":
                writer.writerow({"requirement_id": row["id"], "chapter": row["chapter"], "a_status": row["A"], "b_status": row["B"]})
    return report
