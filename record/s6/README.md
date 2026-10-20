# S6 Recorded Evidence Package

Place the reviewed external recording outside Git or as a GitHub Release asset.
Commit only its SHA-256 manifest and normalized findings. The manifest is not
accepted unless `validate.py` accepts its exact schema. No raw prompt, model
transcript, customer data or credential belongs in this directory.

Recorded findings carry their AISVS identifiers in the validated manifest. A
recorded finding can only corroborate or fail a requirement; it never creates a
B PASS on its own. A B pass still requires independent local control evidence.
