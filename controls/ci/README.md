# CI Gate Thresholds

`gates.yaml` holds the thresholds enforced by the pipeline. Each gate becomes
executable only after the named external tool is admitted in
`third_party_tools.md`; until then the corresponding stage reports `NOT TESTED`
and never silently passes. Thresholds are never edited during a live run.
