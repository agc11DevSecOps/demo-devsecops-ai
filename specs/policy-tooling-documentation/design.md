# Policy And Tooling Documentation Design

## Trust Boundaries

| Boundary | Input | Trusted producer | Decision owner |
| --- | --- | --- | --- |
| Scenario fact builder | Fixed synthetic fixtures | Python control code | Scenario handler |
| OPA process | Machine-built JSON over stdin | `app/security/opa.py` | OPA policy result, interpreted fail-closed |
| Policy draft generator | Catalog entry, validated ID, typed parameters | `tools/create_policy_template.py` | Human reviewer at promotion |
| Standards mapping | Reviewed immutable source metadata | Maintainer | Human reviewer, never runtime |
| Tool guide | Repository source, pinned manifests | Documentation reviewer | Never a runtime authority |

The policy engine is a decision function over already-validated facts. It does
not parse free-form prompts, call models, or execute tools.

## Active Policy Flow

```text
fixture / request
   -> Python validates shape and builds booleans
   -> app/security/opa.py
   -> opa eval (fixed query, fixed data file, 10 s timeout, 64 KiB cap)
   -> boolean true only, otherwise deny
   -> caller maps allow to the scenario outcome
   -> app/evidence.py records decision and reason
```

`admission.rego` receives `artifact.safe_format`, `artifact.signature_ok`, and
`artifact.aibom_complete`. `tool_boundary.rego` receives `action` plus
`context.descriptor_ok` and `context.grant_valid`. An allowed high-impact tool
becomes `REVIEW`, not execution.

## Template Catalogue

`policy-templates/catalog.yaml` is the only accepted template registry. Each
family directory contains:

- `README.md`: purpose, matrix, non-goals, promotion steps.
- `metadata.yaml`: package stem, parameters, defaults, types, and standards.
- `policy.rego.tmpl`: default-deny policy with explicit placeholders.
- `policy_test.rego.tmpl`: generated tests.
- `input.example.json`: contract example.

Templates are text, never executable catalogue entries. The generator renders
only declared `{{PLACEHOLDER}}` tokens and rejects any unknown token.

## Generator Safety

`tools/create_policy_template.py`:

1. Loads `policy-templates/catalog.yaml`.
2. Rejects an unknown family.
3. Validates `ID` with `^[a-z][a-z0-9-]{2,47}$`.
4. Parses only declared parameters and validates their declared types.
5. Validates list values against `^[a-z][a-z0-9_.-]{1,63}$`.
6. Resolves `policy-drafts/` and refuses a symlinked drafts root.
7. Refuses an existing target, including a dangling symlink.
8. Creates the target exclusively and writes files with exclusive creation.
9. Emits metadata, README, policy, tests, and example input.
10. Never invokes OPA on generated output.

The generated package name is
`draft.<package_stem>.<id_with_underscores>`; the test package is
`<package>.test`.

## Promotion Flow

```text
requirement -> threat review -> choose family -> generate draft
-> review input contract and placeholders -> opa test policy-drafts/<id>
-> add scenario fact builder and caller mapping -> add evidence event
-> update control register and standard mapping -> human approval
-> manual copy into policies/ -> make test-policy -> full verification
```

Generated drafts are not active. Promotion is a reviewed source change.

## Demo Visibility

`make demo-10m` runs `opa test -v policies/` before the strict scenario
sequence. S1 emits an explicit SafeTensors format event. S0 names the verified
SafeTensors model load. S2, S3, S4, and S5 keep their named integrations in the
event control and reason fields.

## Documentation Structure

`docs/tools/` is a guided portal, not a copy of upstream manuals. Each page uses
the same section order and links to the official upstream documentation. The
admission record in `third_party_tools.md` remains the source of truth for
security review.

`docs/standards-and-policy-mapping.md` maps control objectives; it does not
assert compliance. `policy-templates/standards.yaml` is the machine-readable
register used by tests.
