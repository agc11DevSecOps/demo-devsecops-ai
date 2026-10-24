"""S2: the injection corpus with and without normalized pre-inference screening."""

from __future__ import annotations

import os

from app.evidence import Event, EvidenceWriter
from app.flow import EXPLOITED, guarded_ready, guarded_visual, lab_cases, lab_ready, lab_visual
from app.scenarios.helpers import load_jsonl
from app.security.input import INJECTION, PROMPT_GUARD_ATTACKS, PROMPT_GUARD_THRESHOLD, _prompt_guard_model_dir, _prompt_guard_scores, normalize

AISVS_B = ("v1.01-C2.1.1", "v1.01-C2.1.2", "v1.01-C2.1.3", "v1.01-C2.1.6", "v1.01-C2.1.7")


def _run_a_lab(records: list[dict], attacks: list[str], benign: list[str], writer: EvidenceWriter) -> None:
    from app.unguarded import run_case

    cases = lab_cases()
    rows = []
    representative = None
    for record in records:
        result = run_case(cases[f"s2-{record['id']}"])
        representative = representative or result
        rows.append({
            "id": record["id"],
            "category": record.get("category", ""),
            "prompt": record["prompt"],
            "model_output": result["output"][:300],
            "outcome": result["outcome"],
        })
    attack_rows = [row for row in rows if row["id"] != records[-1]["id"]]
    leaked = sum(row["outcome"] == EXPLOITED for row in attack_rows)
    writer.emit(Event(
        "A",
        "S2",
        "prompt injection",
        "EXECUTED",
        f"unguarded lab: {len(attack_rows)}/{len(attack_rows)} attacks reached FLAN-T5-small unscreened; {leaked} printed the prompt template, {len(attack_rows) - leaked} were not exploited by this model",
        ("v1.01-C2.1.1",),
        "MEASURED",
        "\n".join(attacks + benign),
        visual=lab_visual(representative, input_extra={"attack_prompts": attacks, "benign_prompt": benign[0]}, rows=rows, exploited=leaked, total=len(attack_rows)),
    ))


def scenario_s2(run: str, writer: EvidenceWriter) -> None:
    records = load_jsonl("prompts/injection_11.jsonl")
    attacks = [record["prompt"] for record in records if not record.get("benign")]
    benign = [record["prompt"] for record in records if record.get("benign")]
    if len(attacks) != PROMPT_GUARD_ATTACKS or len(benign) != 1:
        raise AssertionError("fixture_count")
    prompts = attacks + benign
    if run == "A":
        if lab_ready():
            _run_a_lab(records, attacks, benign, writer)
            return
        writer.emit(Event("A", "S2", "prompt injection", "EXECUTED", "scripted leak response for 10 attack inputs", ("v1.01-C2.1.1",), "SCRIPTED", "\n".join(prompts), visual={"input": {"attack_prompts": attacks, "benign_prompt": benign[0]}, "control": {"inspection": "absent in baseline"}, "observation": {"leaked_responses": len(attacks)}, "state": {"blocked": 0}}))
        return
    if os.environ.get("OPS_DEMO_PROMPT_GUARD") == "1":
        if not _prompt_guard_model_dir().is_dir():
            raise RuntimeError("prompt_guard_model_missing")
        classifier_blocked = 0
        rules_blocked = 0
        blocked = 0
        rows = []
        for record in records[:PROMPT_GUARD_ATTACKS]:
            _, candidates = normalize(record["prompt"])
            score = max(_prompt_guard_scores(candidates))
            by_classifier = score >= PROMPT_GUARD_THRESHOLD
            by_rules = any(INJECTION.search(candidate) for candidate in candidates)
            classifier_blocked += by_classifier
            rules_blocked += by_rules
            blocked += by_classifier or by_rules
            rows.append({
                "id": record["id"],
                "category": record.get("category", ""),
                "prompt": record["prompt"],
                "representations": len(candidates),
                "rules": "match" if by_rules else "no match",
                "classifier_score": f"{score:.3f}",
                "blocked_by": "both" if by_rules and by_classifier else "rules" if by_rules else "Prompt Guard" if by_classifier else "none",
            })
        benign_candidates = normalize(prompts[-1])[1]
        benign_score = max(_prompt_guard_scores(benign_candidates))
        if benign_score >= PROMPT_GUARD_THRESHOLD or any(INJECTION.search(candidate) for candidate in benign_candidates):
            raise AssertionError("prompt_guard_false_positive")
        if blocked != PROMPT_GUARD_ATTACKS:
            raise AssertionError(f"prompt_guard_missed_{PROMPT_GUARD_ATTACKS - blocked}_attacks")
        visual = {
            "input": {"attack_prompts": attacks, "benign_prompt": benign[0]},
            "control": {"classifier": "Prompt Guard 2 22M", "threshold": "0.5", "rules": "fixed injection expressions", "normalization": "NFKC, zero-width, confusables, base64, rot13"},
            "observation": {"classifier_blocked": classifier_blocked, "rules_blocked": rules_blocked, "total_blocked": blocked, "rows": rows},
            "state": {"blocked": blocked, "total": PROMPT_GUARD_ATTACKS},
        }
        benign_visual = None
        if guarded_ready():
            from app.guarded import run_case

            cases = lab_cases()
            attack = run_case(cases[f"s2-{records[0]['id']}"], requester="s2-guarded-attack")
            visual["trace"] = attack["trace"]
            visual["observation"].update(guarded_visual(attack))
            benign_run = run_case(cases[f"s2-{records[-1]['id']}"], requester="s2-guarded-benign")
            benign_visual = {
                "input": {"question": prompts[-1]},
                "control": {"classifier": "Prompt Guard 2 22M", "threshold": "0.5"},
                "observation": {"classifier_score": f"{benign_score:.3f}", **guarded_visual(benign_run)},
                "state": {"screen": "passed"},
                "trace": benign_run["trace"],
            }
        writer.emit(Event("B", "S2", "Prompt Guard 2 22M inspection", "BLOCKED", f"normalization and rules matched {rules_blocked}/{PROMPT_GUARD_ATTACKS} attacks and Prompt Guard 2 22M (DeBERTa-xsmall) flagged {classifier_blocked}/{PROMPT_GUARD_ATTACKS}; together {blocked}/{PROMPT_GUARD_ATTACKS} blocked before inference", AISVS_B, input_value="\n".join(prompts), visual=visual))
        writer.emit(Event("B", "S2", "paraphrased injection", "ALLOWED", f"benign paraphrase below threshold (score {benign_score:.3f})", ("v1.01-C2.1.3",), input_value=prompts[-1], visual=benign_visual))
        return
    blocked = 0
    for prompt in prompts[:PROMPT_GUARD_ATTACKS]:
        _, candidates = normalize(prompt)
        if any(INJECTION.search(candidate) for candidate in candidates):
            blocked += 1
    if blocked != PROMPT_GUARD_ATTACKS:
        raise AssertionError("unexpected_s2_detection_count")
    writer.emit(Event("B", "S2", "normalized injection inspection", "BLOCKED", f"{blocked}/{PROMPT_GUARD_ATTACKS} blocked by fallback rules", AISVS_B, input_value="\n".join(prompts)))
    writer.emit(Event("B", "S2", "paraphrased injection", "ALLOWED", "fallback score unavailable; tool boundary still applies", ("v1.01-C2.1.3",), input_value=prompts[-1]))
