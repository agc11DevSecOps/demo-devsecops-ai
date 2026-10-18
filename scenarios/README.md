# Scenario Index

Each directory holds `run_a.sh` / `run_b.sh` wrappers over the matching
`make s<N>-a` / `make s<N>-b` target and `expected_a.txt` / `expected_b.txt`
describing the expected outcome. Run A requires the container boundary.

- `s0_baseline` (S0)
- `s1_model_supply_chain` (S1)
- `s2_prompt_injection` (S2)
- `s3_pii` (S3)
- `s4_retrieval_poisoning` (S4)
- `s5_tool_boundary` (S5)
- `s6_agentic_pentest` (S6)
- `s7_visibility_kill_switch` (S7)
- `s8_workload_bounds` (S8)

