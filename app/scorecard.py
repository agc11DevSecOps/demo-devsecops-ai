"""Evidence-only AISVS scorecard generation."""

from __future__ import annotations

import csv
import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.demo import AISVS_ID, EVIDENCE, ROOT


SCORECARD = ROOT / "scorecard"


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


def _status(records: list[dict[str, Any]], requirement: str, run: str) -> str:
    matching = [record for record in records if requirement in record["aisvs_ids"]]
    if not matching:
        return "NOT TESTED"
    decisions = {record["decision"] for record in matching}
    if run == "A":
        return "FAIL" if decisions & {"EXECUTED", "ALLOWED", "FAIL"} else "NOT TESTED"
    return "PASS" if decisions & {"BLOCKED", "DENIED", "REVIEW", "ALLOWED"} else "NOT TESTED"


def build() -> dict[str, Any]:
    catalog = json.loads((SCORECARD / "requirements_v1.01.json").read_text(encoding="utf-8"))
    requirements = catalog["requirements"]
    records = {"A": _records("A"), "B": _records("B")}
    rows: list[dict[str, Any]] = []
    for requirement in requirements:
        rows.append({**requirement, "A": _status(records["A"], requirement["id"], "A"), "B": _status(records["B"], requirement["id"], "B")})
    by_chapter: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_chapter[row["chapter"]].append(row)
    chapters = []
    for chapter, values in sorted(by_chapter.items()):
        chapter_status = {}
        for run in ("A", "B"):
            tested = sum(value[run] != "NOT TESTED" for value in values)
            level_one = [value for value in values if value["level"] == 1]
            if level_one and all(value[run] == "PASS" for value in level_one):
                level = "L1"
            elif tested == 0:
                level = "NOT TESTED"
            else:
                level = "below L1"
            chapter_status[run] = {"level": level, "tested": tested, "applicable": len(values)}
        chapters.append({"chapter": chapter, **chapter_status})
    return {"catalog_status": catalog["source_status"], "requirements": rows, "chapters": chapters}


def write() -> dict[str, Any]:
    report = build()
    markdown = ["# AISVS Evidence Scorecard", "", f"Catalog status: `{report['catalog_status']}`", "", "| Chapter | A | B |", "| --- | --- | --- |"]
    for chapter in report["chapters"]:
        markdown.append(f"| {chapter['chapter']} | {chapter['A']['level']} ({chapter['A']['tested']}/{chapter['A']['applicable']}) | {chapter['B']['level']} ({chapter['B']['tested']}/{chapter['B']['applicable']}) |")
    markdown.extend(["", "## Requirement Detail", "", "| Requirement | A | B |", "| --- | --- | --- |"])
    for row in report["requirements"]:
        markdown.append(f"| {row['id']} | {row['A']} | {row['B']} |")
    markdown.extend(["", "Levels follow AISVS v1.01 definitions. This is a self-assessment of a demo system, not an audit. Requirements not exercised by the demo are counted as NOT TESTED."])
    (SCORECARD / "out.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    body = "\n".join(f"<tr><td>{html.escape(row['id'])}</td><td>{row['A']}</td><td>{row['B']}</td></tr>" for row in report["requirements"])
    page = f"<!doctype html><meta charset=utf-8><title>AISVS Scorecard</title><h1>AISVS Evidence Scorecard</h1><p>{html.escape(report['catalog_status'])}</p><table border=1><tr><th>Requirement</th><th>A</th><th>B</th></tr>{body}</table>"
    (SCORECARD / "out.html").write_text(page, encoding="utf-8")
    with (SCORECARD / "delta.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["requirement_id", "chapter", "a_status", "b_status"], lineterminator="\n")
        writer.writeheader()
        for row in report["requirements"]:
            if row["A"] == "FAIL" and row["B"] == "PASS":
                writer.writerow({"requirement_id": row["id"], "chapter": row["chapter"], "a_status": row["A"], "b_status": row["B"]})
    return report
