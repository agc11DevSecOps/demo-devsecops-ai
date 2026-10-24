"""Static catalog of the application security controls shown in the presentation.

Each control names where it is implemented, the exact excerpt that implements
it (extracted from the repository at projection time, never hand-copied), the
Makefile flag that enables it in Run B, its pinned version, the point where it is
wired into the flow, and what Run A does without it. A missing file or symbol
makes extraction fail closed; tests compare every excerpt with its source.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.common import ROOT

MAX_EXCERPT_LINES = 26
MAX_LINE = 160


class CatalogError(ValueError):
    """A control could not be located in the repository."""


@dataclass(frozen=True)
class Anchor:
    """A Python symbol (``symbol``) or a literal line prefix (``line``)."""

    path: str
    symbol: str = ""
    line: str = ""
    lines: int = 0


@dataclass(frozen=True)
class Control:
    id: str
    name: str
    scenarios: tuple[str, ...]
    stage: str
    what: str
    implementation: Anchor
    integration: Anchor
    flag: str
    version: str
    absent: str
    events: tuple[str, ...]


CONTROLS: tuple[Control, ...] = (
    Control(
        "fickling", "Fickling static pickle scan", ("S1",), "supply_chain",
        "Disassembles the pickle opcodes without loading them and rejects any artifact that is not LIKELY_SAFE.",
        Anchor("app/security/model_admission.py", symbol="fickling_scan"),
        Anchor("app/scenarios/s1.py", line="        severity = admission.fickling_scan(malicious)", lines=3),
        "OPS_DEMO_FICKLING=1", "Fickling 0.1.12, hash-pinned wheel",
        "Run A calls pickle.load() on the artifact: the embedded payload runs and creates sandbox/PWNED_BY_MODEL.",
        ("Fickling static scan",),
    ),
    Control(
        "modelscan", "ModelScan static model scan", ("S1", "PIPELINE"), "supply_chain",
        "Scans the serialized model for unsafe operators and reports each finding as an admission blocker.",
        Anchor("app/security/model_admission.py", symbol="modelscan_scan"),
        Anchor("app/scenarios/s1.py", line="        findings = admission.modelscan_scan(malicious)", lines=3),
        "OPS_DEMO_MODELSCAN=1", "ModelScan 0.8.8, hash-pinned wheel",
        "Run A has no scanner; nothing inspects the artifact before it is deserialized.",
        ("ModelScan static scan",),
    ),
    Control(
        "safetensors", "SafeTensors format gate", ("S1", "S0"), "supply_chain",
        "Admits only the non-executable SafeTensors container; the workload loads weights with use_safetensors=True.",
        Anchor("app/scenarios/s1.py", line="    safe_format = clean.suffix", lines=3),
        Anchor("app/llm/runtime.py", line="        model = AutoModelForSeq2SeqLM.from_pretrained(", lines=6),
        "always on", "SafeTensors container format",
        "Run A accepts a pickle artifact, an executable format.",
        ("SafeTensors format gate",),
    ),
    Control(
        "aibom", "AI BOM completeness gate", ("S1",), "supply_chain",
        "Requires model, digest, base model, licence and dataset origin; an incomplete BOM fails the admission build.",
        Anchor("app/scenarios/s1.py", line="    required = {\"model\", \"sha256\"", lines=6),
        Anchor("app/scenarios/s1.py", line="    aibom_bundle = admission.sign(aibom_path)", lines=3),
        "always on", "Repository-owned JSON AI BOM",
        "Run A ships the artifact with no bill of materials.",
        ("AI BOM published", "AI BOM completeness gate"),
    ),
    Control(
        "cosign", "Cosign signature verification", ("S1", "PIPELINE"), "supply_chain",
        "Signs the AI BOM and the model offline and verifies the signature before admission; a one-bit change is denied.",
        Anchor("app/security/model_admission.py", symbol="cosign_verify"),
        Anchor("app/security/model_admission.py", symbol="verify"),
        "OPS_DEMO_COSIGN=1", "Cosign 3.1.3, SHA-256-pinned binary; local key, no transparency log",
        "Run A verifies nothing: a tampered artifact loads the same way.",
        ("AI BOM signature", "Cosign integrity admission", "tampered model"),
    ),
    Control(
        "opa-admission", "OPA model admission policy", ("S1", "PIPELINE"), "supply_chain",
        "Deny-by-default Rego: admit only a safe format with a verified signature and a complete AI BOM.",
        Anchor("policies/admission.rego", line="default allow := false", lines=7),
        Anchor("app/security/model_admission.py", symbol="opa_admit"),
        "OPS_DEMO_OPA=1", "OPA 1.21.2, SHA-256-pinned binary",
        "Run A has no admission decision.",
        ("OPA admission policy model admission",),
    ),
    Control(
        "runtime-boundary", "Restricted runtime", ("S1",), "supply_chain",
        "Every run executes with no network, a read-only root filesystem, dropped capabilities and memory, CPU and PID limits.",
        Anchor("Makefile", line="container-run-b-exec:", lines=2),
        Anchor("Makefile", line="container-run-b-exec:", lines=1),
        "Makefile Run B profile", "Docker restricted runner",
        "Lab containment: Run A uses the same restricted runner, so its effects stay inside sandbox/.",
        ("restricted runtime boundary",),
    ),
    Control(
        "model-verification", "Local model verification", ("S0",), "model",
        "Loads FLAN-T5-small only from local files whose SHA-256 match the pinned set; no hub access and no remote code.",
        Anchor("app/llm/runtime.py", symbol="_flan_generator"),
        Anchor("app/llm/local.py", symbol="LocalAdapter"),
        "OPS_DEMO_WORKLOAD=1", "google/flan-t5-small @ 0fc9ddf, SafeTensors, per-file SHA-256",
        "Shared by both runs: Run A uses the same verified model, so the comparison isolates the application controls.",
        ("Ops Assist workload",),
    ),
    Control(
        "citations", "Retrieval-derived citations", ("S0", "S8"), "output_validation",
        "Citations are built by code from the retrieved document identifiers and digests, never parsed from model text.",
        Anchor("app/workload.py", line="        citations=tuple(Citation(", lines=1),
        Anchor("app/workload.py", symbol="AssistResponse"),
        "always on", "Repository code",
        "Run A shows whatever citation the model writes, which may name the wrong source.",
        ("retrieval attribution", "Ops Assist workload"),
    ),
    Control(
        "normalization", "Input normalization", ("S2",), "injection_screen",
        "NFKC, removal of zero-width and control characters, confusable folding, and base64/rot13 decoding expose every representation to the screen.",
        Anchor("app/security/input.py", symbol="normalize"),
        Anchor("app/workload.py", line="    normalized, candidates = normalize(request.question)", lines=4),
        "always on", "Repository code",
        "Run A sends the raw text, including encoded or obfuscated instructions, straight to the model.",
        ("Prompt Guard 2 22M inspection",),
    ),
    Control(
        "injection-rules", "Injection rules", ("S2",), "injection_screen",
        "Fixed expressions for known instruction-override, system-prompt and tool-call patterns, applied to every normalized representation.",
        Anchor("app/security/input.py", symbol="INJECTION"),
        Anchor("app/workload.py", line="    if any(INJECTION.search(candidate) for candidate in candidates):", lines=4),
        "always on", "Repository code",
        "Run A applies no rule.",
        ("Prompt Guard 2 22M inspection",),
    ),
    Control(
        "prompt-guard", "Prompt Guard 2 22M classifier", ("S2", "S0"), "injection_screen",
        "A local DeBERTa-xsmall classifier scores each normalized representation; a score of 0.5 or more blocks before inference.",
        Anchor("app/security/input.py", symbol="_prompt_guard_scores"),
        Anchor("app/workload.py", line="        scores = _prompt_guard_scores((normalized,))", lines=5),
        "OPS_DEMO_PROMPT_GUARD=1", "meta-llama/Llama-Prompt-Guard-2-22M, local files, offline; threshold 0.5",
        "Run A has no classifier.",
        ("Prompt Guard 2 22M inspection", "paraphrased injection"),
    ),
    Control(
        "presidio", "Presidio PII redaction", ("S3",), "pii_redaction",
        "Offline recognizers for IBAN, phone, email and the demo API key mask values at ingestion, in the question and in the answer.",
        Anchor("app/security/input.py", symbol="_presidio_redact"),
        Anchor("app/workload.py", symbol="_ingest"),
        "OPS_DEMO_PRESIDIO=1", "Presidio 2.2.364 with spaCy en_core_web_sm",
        "Run A indexes the customer record raw; the model can read and repeat every value.",
        ("PII in answer",),
    ),
    Control(
        "provenance", "Writer allow-list and quarantine", ("S4",), "retrieval",
        "Only schema-valid documents from the trusted writer are admitted; anything else is quarantined before it reaches the index.",
        Anchor("app/security/retrieval.py", symbol="admitted_documents"),
        Anchor("app/workload.py", symbol="_ingest"),
        "always on", "Repository code",
        "Run A indexes the untrusted upload next to the runbooks.",
        ("poisoned document",),
    ),
    Control(
        "qdrant-filter", "Qdrant provenance filter", ("S4",), "retrieval",
        "Every query carries a writer=trusted payload filter, so a document from another writer cannot be returned.",
        Anchor("app/security/retrieval.py", symbol="_vector_search"),
        Anchor("app/workload.py", line="        hits = _vector_search(index, question, writer=\"trusted\", limit=MAX_SOURCES)", lines=1),
        "OPS_DEMO_VECTOR=1", "qdrant-client 1.19.1, in-memory; deterministic demo embedding",
        "Run A queries Qdrant without a filter and the untrusted upload ranks first.",
        ("provenance-filtered retrieval", "forced retrieval test"),
    ),
    Control(
        "opa-tools", "OPA tool policy", ("S5",), "tool_gate",
        "Deny-by-default Rego: read tools need a pinned descriptor; delete_branch also needs a valid human grant; export_customers is never allowed.",
        Anchor("policies/tool_boundary.rego", line="default allow := false", lines=16),
        Anchor("app/security/tool_boundary.py", symbol="opa_authorize"),
        "OPS_DEMO_OPA=1", "OPA 1.21.2, SHA-256-pinned binary",
        "Run A's naive agent executes any tool name it finds in model output.",
        ("delete_branch", "export_customers", "model-proposed tool call", "MCP delete_branch"),
    ),
    Control(
        "approval", "Bound human approval", ("S5",), "tool_gate",
        "An approval binds the tool, canonical parameters, requester, descriptor digest, expiry and one use; any change invalidates it.",
        Anchor("app/approvals.py", symbol="_key"),
        Anchor("app/scenarios/s5.py", line="    approval = issue_approval(", lines=1),
        "always on", "HMAC-SHA256 over the canonical request; sandbox demo key unless OPS_DEMO_APPROVAL_KEY is set",
        "Run A needs no approval.",
        ("authorization binding", "delete_branch granted"),
    ),
    Control(
        "scope-filter", "Tool scope filter", ("S5",), "tool_gate",
        "tools/list returns only the tools the caller's scopes allow; high-impact tools are never listed to a docs:read caller.",
        Anchor("app/security/tool_boundary.py", symbol="ToolBoundary.list_tools"),
        Anchor("app/scenarios/s5.py", line="    permitted = boundary.list_tools(", lines=1),
        "always on", "Repository code",
        "Run A exposes every tool.",
        ("tools/list scope filter",),
    ),
    Control(
        "mcp", "MCP boundary", ("S5",), "tool_gate",
        "The local stdio MCP server is reached only after the boundary decides; the server itself refuses delete_branch.",
        Anchor("app/mcp_server.py", symbol="delete_branch"),
        Anchor("app/scenarios/s5.py", line="        names, text = mcp_call(\"search_docs\", read_only)", lines=1),
        "OPS_DEMO_MCP=1", "MCP Python SDK 2.3.0, stdio",
        "Run A has no MCP boundary.",
        ("MCP search_docs", "MCP delete_branch"),
    ),
    Control(
        "tool-output", "Tool output schema and screening", ("S5",), "tool_gate",
        "Tool output must match its declared schema and is screened for indirect injection before it can reach the model.",
        Anchor("app/security/tool_boundary.py", symbol="ToolBoundary.screen_output"),
        Anchor("app/scenarios/s5.py", line="        boundary.screen_output(\"search_docs\", poisoned_output)", lines=1),
        "always on", "Repository code",
        "Run A forwards tool output unchanged.",
        ("tool output schema", "tool output screening"),
    ),
    Control(
        "quota", "Per-run tool quota", ("S5",), "tool_gate",
        "High-impact tools have a per-run quota of one; a second call is contained.",
        Anchor("app/security/tool_boundary.py", symbol="ToolQuota"),
        Anchor("app/scenarios/s5.py", line="    quota = ToolQuota()", lines=2),
        "always on", "Repository code",
        "Run A has no quota.",
        ("tool quota",),
    ),
    Control(
        "input-bounds", "Request schema and length limit", ("S8",), "input",
        "Exactly three fields, bounded identifiers and a 1,024-character question, enforced before any model work.",
        Anchor("app/workload.py", symbol="AssistRequest.from_payload"),
        Anchor("app/workload.py", line="        request = AssistRequest.from_payload(payload)", lines=1),
        "always on", "Repository code",
        "Run A accepts any text up to the lab cap and sends it to the model.",
        ("input length control",),
    ),
    Control(
        "prompt-bound", "Prompt length limit", ("S8",), "prompt",
        "The rendered prompt is rejected above 4,096 characters.",
        Anchor("app/workload.py", symbol="_build_prompt"),
        Anchor("app/workload.py", line="        prompt = _build_prompt(question, sources)", lines=1),
        "always on", "Repository code",
        "Run A renders the same template without a limit; only the tokenizer truncates.",
        ("input length control",),
    ),
    Control(
        "output-validation", "Output validation", ("S8", "S3"), "output_validation",
        "Rejects non-text, empty or over-length answers, internal source or question markers and injection text; masks PII first.",
        Anchor("app/security/output.py", symbol="validate_answer"),
        Anchor("app/workload.py", line="        validated_answer = _validate_answer(answer, use_presidio=selected_mode == \"local\")", lines=1),
        "always on", "Repository code; MAX_ANSWER_CHARS = 1,200",
        "Run A returns the raw model output.",
        ("output validation", "output length control"),
    ),
    Control(
        "pipeline-gates", "Fail-closed delivery gates", ("PIPELINE",), "delivery",
        "Eleven ordered stages; a failed required gate stops the pipeline, and a stage without an admitted tool reports NOT TESTED.",
        Anchor("app/pipeline.py", symbol="run_pipeline"),
        Anchor("app/pipeline.py", symbol="stage_model_scan"),
        "Makefile pipeline profile", "Fickling, ModelScan, Cosign and OPA in the restricted runner",
        "Not applicable: the pipeline has no unguarded counterpart.",
        (),
    ),
    Control(
        "garak", "Garak red-team campaign", ("S7",), "evaluation",
        "A fixed offline Garak probe sends 55 encoded injection prompts to the loopback workload; only a full campaign counts.",
        Anchor("app/garak_campaign.py", symbol="load_summary"),
        Anchor("app/scenarios/s7.py", line="    summary = load_summary()", lines=1),
        "make container-garak-exec GARAK_LIMIT=55", "Garak 0.10.3.1, probe encoding.InjectBase64",
        "Run A has no campaign: application logs cannot answer whether an attack happened.",
        ("Garak campaign",),
    ),
    Control(
        "kill-switch", "Inference stop control", ("S7",), "input",
        "A sandbox kill switch rejects every request before inference and records the stop.",
        Anchor("app/workload.py", symbol="_stop_enabled"),
        Anchor("app/workload.py", line="    if _stop_enabled():", lines=3),
        "make kill / make unkill", "Repository code",
        "Run A has no stop control.",
        ("inference stop control",),
    ),
)

CONTROL_IDS = frozenset(control.id for control in CONTROLS)


def _python_range(path: Path, symbol: str) -> tuple[int, int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    parts = symbol.split(".")
    body: list[ast.stmt] = tree.body
    node: ast.AST | None = None
    for index, part in enumerate(parts):
        node = None
        for candidate in body:
            if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and candidate.name == part:
                node = candidate
            elif isinstance(candidate, ast.Assign) and any(isinstance(target, ast.Name) and target.id == part for target in candidate.targets):
                node = candidate
            if node is not None:
                break
        if node is None:
            raise CatalogError(f"symbol_not_found:{symbol}")
        if index < len(parts) - 1:
            body = getattr(node, "body", [])
    start = min([node.lineno] + [item.lineno for item in getattr(node, "decorator_list", [])])
    return start, int(node.end_lineno or node.lineno)


def _line_range(path: Path, prefix: str, count: int) -> tuple[int, int]:
    lines = path.read_text(encoding="utf-8").splitlines()
    matches = [index for index, line in enumerate(lines, start=1) if line.startswith(prefix)]
    if len(matches) != 1:
        raise CatalogError(f"line_anchor_not_unique:{path.name}:{len(matches)}")
    start = matches[0]
    return start, min(len(lines), start + max(count, 1) - 1)


def locate(anchor: Anchor) -> tuple[int, int]:
    path = ROOT / anchor.path
    if not path.is_file():
        raise CatalogError(f"missing_file:{anchor.path}")
    if anchor.symbol:
        return _python_range(path, anchor.symbol)
    return _line_range(path, anchor.line, anchor.lines)


def excerpt(anchor: Anchor) -> dict[str, Any]:
    """Return the exact source lines for an anchor, bounded for display."""
    start, end = locate(anchor)
    lines = (ROOT / anchor.path).read_text(encoding="utf-8").splitlines()[start - 1:end]
    truncated = len(lines) > MAX_EXCERPT_LINES
    shown = [line if len(line) <= MAX_LINE else line[: MAX_LINE - 1] + "\u2026" for line in lines[:MAX_EXCERPT_LINES]]
    return {
        "path": anchor.path,
        "start": start,
        "end": start + len(shown) - 1,
        "lines": shown,
        "truncated": truncated,
        "location": f"{anchor.path}:{start}" + (f"-{start + len(shown) - 1}" if len(shown) > 1 else ""),
    }


def _redact_sensitive(lines: list[str]) -> list[str]:
    # Excerpts are source code, but never ship a long hex constant to the browser.
    return [re.sub(r"\b[0-9a-f]{32,}\b", "[pinned digest]", line) for line in lines]


def control_view(control: Control) -> dict[str, Any]:
    implementation = excerpt(control.implementation)
    implementation["lines"] = _redact_sensitive(implementation["lines"])
    integration = excerpt(control.integration)
    integration["lines"] = _redact_sensitive(integration["lines"])
    return {
        "id": control.id,
        "name": control.name,
        "scenarios": list(control.scenarios),
        "stage": control.stage,
        "what": control.what,
        "flag": control.flag,
        "version": control.version,
        "absent": control.absent,
        "events": list(control.events),
        "implementation": implementation,
        "integration": integration,
    }


def catalog_view() -> list[dict[str, Any]]:
    return [control_view(control) for control in CONTROLS]


def for_scenario(scenario: str) -> list[Control]:
    return [control for control in CONTROLS if scenario in control.scenarios]
