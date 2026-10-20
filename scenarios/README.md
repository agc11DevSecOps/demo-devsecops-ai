# Scenario Index

Each directory holds `expected_a.txt` and `expected_b.txt` describing the
expected outcome. Run A requires the container boundary. Use the matching
`make s<N>-a` or `make s<N>-b` target for an individual diagnostic run.

Individual targets are destructive diagnostics: each resets the sandbox and
its derived evidence. Use `make demo` for the canonical presentation because it
runs every A/B pair in order while preserving the evidence required by the
scorecard and live viewer. S6 is displayed as `NOT TESTED`; it does not run
Strix from this repository.

- `s0_baseline` (S0)
- `s1_model_supply_chain` (S1)
- `s2_prompt_injection` (S2)
- `s3_pii` (S3)
- `s4_retrieval_poisoning` (S4)
- `s5_tool_boundary` (S5)
- `s6_agentic_pentest` (S6)
- `s7_visibility_kill_switch` (S7)
- `s8_workload_bounds` (S8)
