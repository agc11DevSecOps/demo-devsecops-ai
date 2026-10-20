# Cosign

## What Problem It Solves

A hash proves that a file did not change. It does not prove who produced it.
Cosign signs and verifies blobs with a key pair, so the demo can show that a
one-byte modification breaks the signature and that the admission path refuses
the modified artifact.

## Where It Lives In This Repository

| Path | Role |
| --- | --- |
| `vendor/cosign` | The pinned binary (git-ignored, fetched) |
| `app/security/model_admission.py` | `cosign_keypair`, `cosign_sign`, `cosign_verify` |
| `app/scenarios/s1.py` | Signs the AI BOM and the model, then shows the tamper detection |
| `Dockerfile` | Installs the binary and verifies its hash |

## Pinned Version And Provenance

- Tool: Cosign
- Version: 3.1.3
- SHA-256: `4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71`
- Artifact: `cosign-linux-amd64` from release `v3.1.3`
- Provenance: `third_party_tools.md` → `C1-2026-10-17-Cosign-Admitted`

## Prerequisites

- `make fetch-tools` has been run.
- Write access to `sandbox/`, where the demo-only key pair is created.

## Install

```bash
make fetch-tools
```

## Verify The Installation

```bash
env -i ./vendor/cosign version
```

Expected: `v3.1.3`. The image build also verifies the SHA-256 with
`sha256sum` before installing the binary.

## Supported Configuration

| Setting | Value | Why |
| --- | --- | --- |
| Key pair | `sandbox/model/cosign.key` and `.pub` | Generated locally, never committed |
| Key password | `COSIGN_PASSWORD`, a fixed demo value | There is no real secret here |
| Transparency log | `--use-signing-config=false --tlog-upload=false` | Fully offline |
| Log verification | `--insecure-ignore-tlog` | Nothing to verify offline |
| Bundle | `<blob>.cosign.bundle` next to the artifact | Local, inspectable |
| Environment | `HOME=/tmp`, fixed `PATH` | No inherited credentials |
| Timeout | 30 seconds per call | A hang must not stall the run |

The key files are git-ignored through the `*.key` rule, and they never leave
the sandbox mount.

## Example Run

Sign and verify a file by hand:

```bash
printf 'synthetic demo blob\n' > /tmp/opencode/blob.bin
COSIGN_PASSWORD=demo-only COSIGN_PUBLIC_KEY="" \
  env -i HOME=/tmp PATH=/usr/local/bin:/usr/bin:/bin COSIGN_PASSWORD=demo-only \
  ./vendor/cosign generate-key-pair --output-key-prefix /tmp/opencode/demo
env -i HOME=/tmp PATH=/usr/local/bin:/usr/bin:/bin COSIGN_PASSWORD=demo-only \
  ./vendor/cosign sign-blob --yes --use-signing-config=false --tlog-upload=false \
  --key /tmp/opencode/demo.key --bundle /tmp/opencode/blob.bundle /tmp/opencode/blob.bin
env -i HOME=/tmp PATH=/usr/local/bin:/usr/bin:/bin \
  ./vendor/cosign verify-blob --key /tmp/opencode/demo.pub \
  --bundle /tmp/opencode/blob.bundle --insecure-ignore-tlog /tmp/opencode/blob.bin
```

Inside the demo, the same three steps run automatically in scenario S1.

## Expected Result

```text
[B] [S1] [MEASURED] Cosign integrity admission -> ALLOWED :: safe format, digest and Cosign signature verified
[B] [S1] [MEASURED] tampered model -> DENIED :: Cosign signature mismatch
```

The verification command exits zero for the intact file and non-zero after a
single byte is flipped.

## Evidence And Artifacts

| Path | Content |
| --- | --- |
| `sandbox/model/cosign.key` | The demo-only private key |
| `sandbox/model/cosign.pub` | The demo-only public key |
| `artifacts/aibom.json.cosign.bundle` | The AI BOM signature bundle |
| `evidence/B/s1.jsonl` | The admission and tamper events |

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `error generating keys` | `sandbox/` is not writable | Check the directory permissions, then `make reset` |
| `no matching signatures` | The bundle and the blob do not match | Re-sign the blob; a modified blob needs a new signature |
| `private key is encrypted` | The password is wrong | The demo uses the fixed value `demo-only` |
| `unexpected exit status` | The binary is missing or drifted | `make fetch-tools` and check the hash |

## Security Limits

- The key pair is a **demo** key pair with a public password. It proves
  mechanics, not identity. A real deployment needs a real key, a real
  password source and a real transparency log.
- Cosign is admitted only for offline blob integrity on the fixed fixture.
- A successful verification is integrity evidence. It never authorizes loading
  a model, and it never authorizes a deployment.
- A failed or missing verification denies admission.

## When A Change Needs A New Review

- A new Cosign version, URL or hash: a new pinned entry, a new admission
  record and a rebuild.
- Enabling the transparency log or signing configuration: a new review,
  because it changes the network boundary.
- Moving the key pair out of the sandbox: a new review.
- Signing a different artifact: a new scope entry in
  `third_party_tools.md`.

## Official Documentation

- Cosign documentation: <https://docs.sigstore.dev/cosign/>
- Blob signing and verification: <https://docs.sigstore.dev/cosign/signing/signing_with_blobs/>
- Key management: <https://docs.sigstore.dev/cosign/key_management/overview/>

## Local Source

- `app/security/model_admission.py`
- `app/scenarios/s1.py`
- `Dockerfile`
- `third_party_tools.md` → `C1-2026-10-17-Cosign-Admitted`
