# AMCS Runtime — Reference Implementation

**Version:** 0.1.1  
**Implements:** AMCS v1.2.1 INTERNAL profile  
**Language:** Python 3.11+  
**Dependencies:** Standard library only (no external packages)

---

## Overview

This is the reference implementation of the Atticus Memory Cell Sealing Protocol (AMCS), which provides the enforcement and persistence layer for AMAS memory governance.

The runtime converts chat conversations into immutable, hash-verified memory cell bundles with full provenance tracking.

## Commands

### `seal` — Create a memory cell

```bash
python3 amcs.py seal \
    --input chat.json \
    --out-dir out \
    --cell-name MY_CELL \
    --scope "entire_chat" \
    --primary-narrative-source chat
```

Options:
- `--input PATH` — JSON or plain text chat file (required)
- `--out-dir DIR` — Output directory (required)
- `--cell-name NAME` — Cell identifier (required)
- `--scope STRING` — Scope declaration (default: `entire_chat`)
- `--primary-narrative-source {odt,chat,both}` — Canonical source (default: `chat`)
- `--odt PATH` — Optional ODT file to include as canonical narrative
- `--genesis-prompt TEXT` — Override the default AMCS_INIT_SEED
- `--parse-session-header / --no-parse-session-header` — Session header parsing (default: on)

### `verify` — Validate a sealed cell

```bash
python3 amcs.py verify --cell out/MY_CELL.tar.gz
```

Returns `PASS` or `FAIL` with details. Checks all SHA-256 hashes and referential integrity.

### `assemble-supercell` — Combine multiple cells

```bash
python3 amcs.py assemble-supercell \
    --cells cell_a.tar.gz cell_b.tar.gz \
    --out-dir out \
    --supercell-name COMBINED \
    --scope "project_analysis" \
    --mode research
```

Options:
- `--mode {analysis,research,consolidation,planning}` — Assembly mode (default: `research`)
- `--reason TEXT` — Assembly justification
- `--notes TEXT` — Free-text notes

## Input Formats

### JSON (recommended)

```json
[
  {"role": "user", "content": "What is the current status?"},
  {"role": "assistant", "content": "Here is the status report..."},
  {"role": "user", "content": "Thanks. Archive this."}
]
```

Optional fields per message: `timestamp` (ISO 8601), `attachments` (list of file paths).

### Plain text

```
USER:
What is the current status?

ASSISTANT:
Here is the status report...

USER:
Thanks. Archive this.
```

## What the Runtime Produces

A sealed `.tar.gz` containing:

| File | Purpose |
|------|---------|
| `data/prompt_log.json` | Verbatim record of all messages with SHA-256 hashes |
| `data/prompt_response_map.json` | Causal links: which response answers which prompt |
| `data/matrices/messages.csv` | Structured message matrix (+ `.jsonl`) |
| `data/case_study_map.json` | Node/edge graph of message relationships |
| `manifests/file_hashes.sha256` | Integrity checksums for every file in the cell |
| `manifests/seal_receipt.json` | Sealing metadata, content hash, provenance |
| `casefiles/CF_MESSAGES.md` | Human-readable case file |
| `README.md` | Read order and authority notes |
| `logs/verification.log` | Verification results |

## Provenance Guarantees

Every derived artifact references its source via `source_prompt_ids`, `source_response_ids`, and `source_message_hashes`. No derived content exists without traceable provenance.

## AMAS Conformance

This runtime demonstrates AMAS principles at the persistence layer:
- **Authority hierarchy** via the AMCS authority order (canonical > first-order > second-order > edges > rollups)
- **Provenance tracking** via mandatory source attribution on every artifact
- **Inference marking** via first-order / second-order separation
- **Immutability** via SHA-256 sealing with verification-before-load
