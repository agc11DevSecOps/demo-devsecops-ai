"""S2: inspect normalized prompt representations before inference."""

from __future__ import annotations

import os

from app.evidence import Event, EvidenceWriter
from app.scenarios.helpers import load_jsonl
from app.security.input import INJECTION, PROMPT_GUARD_ATTACKS, PROMPT_GUARD_THRESHOLD, _prompt_guard_model_dir, _prompt_guard_scores, normalize


def scenario_s2(run: str, writer: EvidenceWriter) -> None:
    records = load_jsonl("prompts/injection_11.jsonl")
    attacks = [record["prompt"] for record in records if not record.get("benign")]
    benign = [record["prompt"] for record in records if record.get("benign")]
    if len(attacks) != PROMPT_GUARD_ATTACKS or len(benign) != 1:
        raise AssertionError("fixture_count")
    prompts = attacks + benign
    if run == "A":
        writer.emit(Event("A", "S2", "prompt injection", "EXECUTED", "scripted leak response for 10 attack inputs", ("v1.01-C2.1.1",), "SCRIPTED", "\n".join(prompts), visual={"input": {"attack_prompts": attacks, "benign_prompt": benign[0]}, "control": {"inspection": "absent in baseline"}, "observation": {"leaked_responses": len(attacks)}, "state": {"blocked": 0}}))
        return
    if os.environ.get("OPS_DEMO_PROMPT_GUARD") == "1":
        if not _prompt_guard_model_dir().is_dir():
            raise RuntimeError("prompt_guard_model_missing")
        classifier_blocked = 0
        blocked = 0
        for prompt in prompts[:PROMPT_GUARD_ATTACKS]:
            _, candidates = normalize(prompt)
            by_classifier = max(_prompt_guard_scores(candidates)) >= PROMPT_GUARD_THRESHOLD
            by_rules = any(INJECTION.search(candidate) for candidate in candidates)
            classifier_blocked += by_classifier
            blocked += by_classifier or by_rules
        benign_candidates = normalize(prompts[-1])[1]
        benign_score = max(_prompt_guard_scores(benign_candidates))
        if benign_score >= PROMPT_GUARD_THRESHOLD or any(INJECTION.search(candidate) for candidate in benign_candidates):
            raise AssertionError("prompt_guard_false_positive")
        if blocked != PROMPT_GUARD_ATTACKS:
            raise AssertionError(f"prompt_guard_missed_{PROMPT_GUARD_ATTACKS - blocked}_attacks")
        writer.emit(Event("B", "S2", "Prompt Guard 2 22M inspection", "BLOCKED", f"Prompt Guard 2 22M (DeBERTa-xsmall) flagged {classifier_blocked}/{PROMPT_GUARD_ATTACKS} normalized attacks; normalization rules covered the rest ({blocked}/{PROMPT_GUARD_ATTACKS} blocked)", ("v1.01-C2.1.1", "v1.01-C2.1.2", "v1.01-C2.1.3", "v1.01-C2.1.6", "v1.01-C2.1.7"), input_value="\n".join(prompts), visual={"input": {"attack_prompts": attacks, "benign_prompt": benign[0]}, "control": {"classifier": "Prompt Guard 2 22M", "threshold": "0.5"}, "observation": {"classifier_blocked": classifier_blocked, "total_blocked": blocked}, "state": {"blocked": blocked, "total": PROMPT_GUARD_ATTACKS}}))
        writer.emit(Event("B", "S2", "paraphrased injection", "ALLOWED", f"benign paraphrase below threshold (score {benign_score:.3f})", ("v1.01-C2.1.3",), input_value=prompts[-1]))
        return
    blocked = 0
    for prompt in prompts[:PROMPT_GUARD_ATTACKS]:
        _, candidates = normalize(prompt)
        if any(INJECTION.search(candidate) for candidate in candidates):
            blocked += 1
    if blocked != PROMPT_GUARD_ATTACKS:
        raise AssertionError("unexpected_s2_detection_count")
    writer.emit(Event("B", "S2", "normalized injection inspection", "BLOCKED", f"{blocked}/{PROMPT_GUARD_ATTACKS} blocked by fallback rules", ("v1.01-C2.1.1", "v1.01-C2.1.2", "v1.01-C2.1.3", "v1.01-C2.1.6", "v1.01-C2.1.7"), input_value="\n".join(prompts)))
    writer.emit(Event("B", "S2", "paraphrased injection", "ALLOWED", "fallback score unavailable; tool boundary still applies", ("v1.01-C2.1.3",), input_value=prompts[-1]))
