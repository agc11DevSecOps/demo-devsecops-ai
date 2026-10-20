"""Generate a reviewable Rego policy draft from the local template catalogue.

The generator is offline, deterministic and never uses a model. It renders the
fixed templates in ``policy-templates/`` with validated parameters, writes the
result under ``policy-drafts/``, and refuses to touch ``policies/``. It never
executes the policy it produces.

Everything it accepts is constrained:

* the family must exist in ``policy-templates/catalog.yaml``;
* the draft id must match the catalogue's id pattern;
* every parameter must be declared, and its value must match the declared
  type;
* the target directory must not already exist and must not be a symlink.

A generated draft is marked ``DRAFT - REVIEW REQUIRED`` and is inert until a
human reviews it, tests it, and promotes it as a reviewed source change.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "policy-templates"
CATALOG = TEMPLATES / "catalog.yaml"
STANDARDS = TEMPLATES / "standards.yaml"
PLACEHOLDER = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
LIST_VALUE = re.compile(r"^[a-z][a-z0-9_.-]{1,63}$")
DRAFT_MARKER = "DRAFT - REVIEW REQUIRED"
GENERATOR = "tools/create_policy_template.py"
MAX_INT = 1_000_000


class TemplateError(ValueError):
    """Raised when a template request is refused."""


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TemplateError(f"invalid_document:{path.name}")
    return data


def load_catalog() -> dict[str, Any]:
    catalog = load_yaml(CATALOG)
    if not isinstance(catalog.get("templates"), dict) or not catalog["templates"]:
        raise TemplateError("invalid_catalog")
    return catalog


def resolve_family(catalog: dict[str, Any], family: str) -> dict[str, Any]:
    templates = catalog["templates"]
    if family not in templates:
        raise TemplateError(f"unknown_template:{family}")
    spec = templates[family]
    if not isinstance(spec, dict):
        raise TemplateError(f"invalid_template:{family}")
    return spec


def validate_id(catalog: dict[str, Any], draft_id: str) -> str:
    pattern = catalog.get("id_pattern", r"^[a-z][a-z0-9-]{2,47}$")
    if not isinstance(pattern, str) or not re.fullmatch(pattern, draft_id):
        raise TemplateError("invalid_id")
    if draft_id in {".", ".."} or "/" in draft_id or "\\" in draft_id:
        raise TemplateError("invalid_id")
    return draft_id


def drafts_root(catalog: dict[str, Any]) -> Path:
    relative = catalog.get("drafts_dir", "policy-drafts")
    if not isinstance(relative, str) or not re.fullmatch(r"[a-z][a-z0-9-]{1,47}", relative):
        raise TemplateError("invalid_drafts_dir")
    root = ROOT / relative
    if root.is_symlink():
        raise TemplateError("symlinked_drafts_root")
    return root


def coerce(spec: dict[str, Any], raw: str, name: str) -> Any:
    kind = spec.get("type")
    forbidden = {str(item) for item in spec.get("forbidden", [])}
    if kind == "list":
        items = [item.strip() for item in raw.split(",") if item.strip()]
        if not items:
            raise TemplateError(f"empty_list_parameter:{name}")
        for item in items:
            if not LIST_VALUE.fullmatch(item):
                raise TemplateError(f"invalid_list_value:{name}")
            if item in forbidden:
                raise TemplateError(f"forbidden_parameter_value:{name}")
        if len(set(items)) != len(items):
            raise TemplateError(f"duplicate_list_value:{name}")
        return sorted(items)
    if kind == "int":
        if not raw.isdigit():
            raise TemplateError(f"invalid_int_parameter:{name}")
        value = int(raw)
        if value < 1 or value > MAX_INT:
            raise TemplateError(f"out_of_range_parameter:{name}")
        return value
    if kind == "bool":
        if raw not in {"true", "false"}:
            raise TemplateError(f"invalid_bool_parameter:{name}")
        return raw == "true"
    raise TemplateError(f"unsupported_parameter_type:{name}")


def parse_parameters(spec: dict[str, Any], raw: list[str]) -> dict[str, Any]:
    declared = spec.get("parameters", {})
    if not isinstance(declared, dict):
        raise TemplateError(f"invalid_parameters:{spec.get('package', 'unknown')}")
    values: dict[str, Any] = {}
    for name, definition in declared.items():
        if not isinstance(definition, dict):
            raise TemplateError(f"invalid_parameter:{name}")
        values[name] = definition.get("default")
    for item in raw:
        if "=" not in item:
            raise TemplateError(f"invalid_parameter:{item}")
        name, _, value = item.partition("=")
        name = name.strip()
        if name not in declared:
            raise TemplateError(f"unknown_parameter:{name}")
        values[name] = coerce(declared[name], value.strip(), name)
    for name, value in values.items():
        if value is None:
            raise TemplateError(f"missing_default:{name}")
    return values


def rego_set(values: list[str]) -> str:
    return "{" + ", ".join(f'"{value}"' for value in values) + "}"


def render_values(family: str, spec: dict[str, Any], parameters: dict[str, Any], draft_id: str) -> dict[str, str]:
    stem = spec.get("package")
    if not isinstance(stem, str) or not re.fullmatch(r"[a-z][a-z0-9_]{1,47}", stem):
        raise TemplateError(f"invalid_package:{family}")
    package = f"draft.{stem}.{draft_id.replace('-', '_')}"
    values: dict[str, str] = {"PACKAGE": package, "DRAFT_ID": draft_id}
    if family == "model-admission":
        formats = parameters["allowed_formats"]
        values["ALLOWED_FORMATS"] = rego_set(formats)
        values["PRIMARY_FORMAT"] = formats[0]
    elif family == "tool-authorization":
        read_only = parameters["read_only_tools"]
        gated = parameters["gated_tools"]
        values["READ_ONLY_TOOLS"] = rego_set(read_only)
        values["GATED_TOOLS"] = rego_set(gated)
        values["PRIMARY_READ_ONLY_TOOL"] = read_only[0]
        values["PRIMARY_READ_TOOL"] = read_only[0]
        values["PRIMARY_GATED_TOOL"] = gated[0]
    elif family == "rag-admission":
        writers = parameters["allowed_writers"]
        values["ALLOWED_WRITERS"] = rego_set(writers)
        values["MAX_TEXT_CHARS"] = str(parameters["max_text_chars"])
        values["PRIMARY_WRITER"] = writers[0]
    elif family == "input-output-guardrails":
        values["MAX_INPUT_CHARS"] = str(parameters["max_input_chars"])
        values["MAX_OUTPUT_CHARS"] = str(parameters["max_output_chars"])
    elif family == "runtime-evidence":
        values["MAX_REQUESTS_PER_MINUTE"] = str(parameters["max_requests_per_minute"])
    else:
        raise TemplateError(f"unsupported_family:{family}")
    return values


def render(text: str, values: dict[str, str], source: str) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            raise TemplateError(f"unknown_placeholder:{source}:{key}")
        return values[key]

    rendered = PLACEHOLDER.sub(replace, text)
    if PLACEHOLDER.search(rendered):
        raise TemplateError(f"unresolved_placeholder:{source}")
    return rendered


def standards_for(family: str) -> list[dict[str, Any]]:
    register = load_yaml(STANDARDS)
    entries = register.get("templates", {})
    if not isinstance(entries, dict) or family not in entries:
        return []
    mapping = entries[family]
    if not isinstance(mapping, list):
        raise TemplateError(f"invalid_standards_mapping:{family}")
    return [item for item in mapping if isinstance(item, dict)]


def family_directory(spec: dict[str, Any]) -> Path:
    directory = spec.get("directory")
    if not isinstance(directory, str) or not re.fullmatch(r"[a-z][a-z0-9-]{1,47}", directory):
        raise TemplateError("invalid_template_directory")
    return TEMPLATES / directory


def build_readme(family: str, spec: dict[str, Any], draft_id: str, package: str, parameters: dict[str, Any], example: str) -> str:
    declared = spec.get("parameters", {})
    rows = ["| Parameter | Value | Meaning |", "| --- | --- | --- |"]
    for name, definition in declared.items():
        value = parameters[name]
        shown = ", ".join(value) if isinstance(value, list) else str(value)
        rows.append(f"| `{name}` | `{shown}` | {definition.get('description', '').strip()} |")
    standards = standards_for(family)
    objective_lines = [
        f"- {item.get('standard')}: {', '.join(item.get('ids', []))} - {item.get('objective', '')}"
        for item in standards
    ]
    return f"""# {DRAFT_MARKER}

`{draft_id}` is a generated policy draft from the `{family}` template family.

**This policy is not active.** Nothing calls it. It is a review artefact.

## Files

| File | Content |
| --- | --- |
| `policy.rego` | The policy itself, default deny. |
| `policy_test.rego` | Unit tests: allow, deny, default deny, malformed, unknown. |
| `input.example.json` | An example input that the policy allows. |
| `metadata.json` | Machine-readable description, parameters and standards mapping. |

## Identity

| Field | Value |
| --- | --- |
| Template family | `{family}` |
| Draft id | `{draft_id}` |
| Package | `{package}` |
| Query | `data.{package}.allow` |
| Generated by | `{GENERATOR}` |
| Status | {DRAFT_MARKER} |

## Parameters

{chr(10).join(rows)}

## Example Input

```json
{example}
```

## How To Review It

1. Read `policy.rego` line by line. Confirm `default allow := false` and that
   every allow rule only uses facts a caller can validate.
2. Confirm the input contract matches the fact builder you intend to use. The
   policy reads only what the input provides.
3. Confirm no allow rule can be reached by an unvalidated field. Anything not
   in the contract must not influence the decision.
4. Check the deny cases in `policy_test.rego` against your threat model. Add a
   test for every way the call could be abused.

## How To Test It

```bash
env -i ./vendor/opa test -v policy-drafts/{draft_id}/
```

The tests must pass before the policy is promoted. A failing test is a
blocking finding, not a warning.

## Promotion Checklist

- [ ] Requirement, design and threat review written under `specs/`.
- [ ] Caller added that builds the input, calls `app/security/opa.py` and maps
      the boolean to a decision without executing anything.
- [ ] Evidence event emitted with a control name, decision, reason and label.
- [ ] `docs/control-register.md` updated with the path, dependency and limits.
- [ ] `docs/policies.md` updated if the input contract changed.
- [ ] Moved into `policies/` as a reviewed change.
- [ ] `make test-policy` and the full verification sequence pass.

## Standards Objectives

These are control objectives used to shape the design. They are not results,
not compliance, and they never authorize an action.

{chr(10).join(objective_lines) if objective_lines else '- No standard objective is mapped to this family yet.'}

## What This Policy Cannot Do

- It cannot execute anything.
- It cannot grant approval.
- It cannot authorize a model to act.
- It cannot turn a standard reference, a scanner result, or a model output
  into a decision.
"""


def create_draft(family: str, draft_id: str, raw_parameters: list[str]) -> Path:
    catalog = load_catalog()
    spec = resolve_family(catalog, family)
    validate_id(catalog, draft_id)
    parameters = parse_parameters(spec, raw_parameters)
    values = render_values(family, spec, parameters, draft_id)
    package = values["PACKAGE"]

    source = family_directory(spec)
    policy = render((source / "policy.rego.tmpl").read_text(encoding="utf-8"), values, "policy.rego.tmpl")
    tests = render((source / "policy_test.rego.tmpl").read_text(encoding="utf-8"), values, "policy_test.rego.tmpl")
    example = render((source / "input.example.json").read_text(encoding="utf-8"), values, "input.example.json")
    try:
        json.loads(example)
    except json.JSONDecodeError as error:
        raise TemplateError(f"invalid_example_input:{error}") from error

    if "default allow := false" not in policy:
        raise TemplateError("missing_default_deny")
    if DRAFT_MARKER not in policy or DRAFT_MARKER not in tests:
        raise TemplateError("missing_draft_marker")

    metadata = {
        "status": DRAFT_MARKER,
        "template": family,
        "draft_id": draft_id,
        "package": package,
        "query": f"data.{package}.allow",
        "generator": GENERATOR,
        "promotion": "manual-review",
        "parameters": parameters,
        "standards": standards_for(family),
        "files": ["policy.rego", "policy_test.rego", "input.example.json", "metadata.json", "README.md"],
    }
    readme = build_readme(family, spec, draft_id, package, parameters, example.strip())

    root = drafts_root(catalog)
    root.mkdir(parents=True, exist_ok=True)
    target = root / draft_id
    if target.is_symlink() or target.exists():
        raise TemplateError("target_exists")
    try:
        target.mkdir(parents=False, exist_ok=False)
    except FileExistsError as error:
        raise TemplateError("target_exists") from error
    for name, content in (
        ("policy.rego", policy),
        ("policy_test.rego", tests),
        ("input.example.json", example),
        ("metadata.json", json.dumps(metadata, indent=2, sort_keys=True) + "\n"),
        ("README.md", readme),
    ):
        with (target / name).open("x", encoding="utf-8") as handle:
            handle.write(content)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a reviewable Rego policy draft.")
    parser.add_argument("--template", required=True, help="template family from policy-templates/catalog.yaml")
    parser.add_argument("--id", required=True, dest="draft_id", help="draft identifier")
    parser.add_argument("--param", action="append", default=[], help="parameter override as key=value")
    parser.add_argument("--params", default="", help="comma separated parameter overrides as key=value,key=value")
    args = parser.parse_args(argv)
    raw = list(args.param)
    if args.params:
        raw.extend(item.strip() for item in args.params.split(",") if item.strip())
    try:
        target = create_draft(args.template, args.draft_id, raw)
    except TemplateError as error:
        print(f"policy template refused: {error}", file=sys.stderr)
        return 2
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
