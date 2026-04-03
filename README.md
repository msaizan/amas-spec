# AMAS — Authority Mapping and Arbitration System

**A formal governance model for memory authority in Large Language Models.**

Version: 1.1 (Draft)  
Status: Open for review  
Author: Jacob Dougherty  
License: Apache 2.0

---

## The Problem

Large Language Models have no concept of epistemic authority.

When an LLM processes a conversation, it receives input from multiple sources: system instructions from the platform, configuration from the developer, messages from the user, results from tools, retrieved documents, and its own prior outputs. All of these compete for influence over the model's behavior — but the model has no formal mechanism for deciding which source should prevail when they conflict.

This creates three categories of failure:

**Prompt injection.** A user message or retrieved document overrides system-level safety instructions because the model cannot distinguish between authority tiers.

**Authority laundering.** An automated system makes consequential decisions, but because the decision was produced by an AI model acting on ambiguous instructions, no party is clearly accountable. The authority to decide was never formally delegated — it was laundered through the model's context window.

**Memory drift.** Across sessions, AI systems accumulate context from prior interactions, retrieved data, and inferred patterns. Without a formal hierarchy, an inference from three sessions ago can silently override an explicit instruction from the current operator.

Every major LLM provider has ad-hoc mitigations for some of these problems — role-based message channels, instruction hierarchies, safety layers. None has a formal, auditable, deterministic model for how authority flows through the context window.

AMAS provides that model.

---

## What AMAS Defines

### Authority Hierarchy

AMAS establishes four tiers of memory authority, ordered by precedence:

| Tier | Name | Description |
|------|------|-------------|
| 0 | **CANONICAL** | Foundational rules, safety constraints, and system invariants. Immutable within a version. Cannot be overridden by any lower tier. |
| 1 | **OPERATOR** | Developer or deployer instructions. Configures behavior within the boundaries set by Tier 0. |
| 2 | **SESSION** | User messages, conversation history, uploaded documents, tool outputs. The runtime context of a single interaction. |
| 3 | **INFERRED** | Conclusions drawn by the model from available context. Must be explicitly marked as inference. Lowest authority; never overrides any other tier. |

### Conflict Resolution Protocol

When memory sources conflict, AMAS applies five deterministic rules in order:

1. **Tier precedence.** Higher tier always prevails over lower tier. No exceptions.
2. **Explicit supersession.** Within the same tier, a source that explicitly replaces a prior source prevails, provided the replacement is authorized and traceable.
3. **Recency.** Within the same tier, absent explicit supersession, the most recent source prevails.
4. **Specificity.** Within the same tier, same recency, the more specific source prevails over the more general.
5. **Conservative default.** If no rule resolves the conflict, the system defaults to the more restrictive interpretation or flags the conflict for operator resolution.

### Memory Object Schema

Every item in the authority hierarchy is a **Memory Object** — a discrete, self-contained unit of information with attached metadata:

```json
{
  "object_id": "MO-00042",
  "authority_tier": 0,
  "content": "The system must not generate content that facilitates harm.",
  "source_id": "system_constitution_v2",
  "created_at": "2026-01-15T00:00:00Z",
  "scope": "global",
  "mutable": false,
  "confidence": null,
  "inference_marker": false,
  "escalated_from": null,
  "provenance": {
    "origin": "platform_developer",
    "chain": ["constitution_v1", "constitution_v2"]
  }
}
```

### Tier Interaction Rules

- **Downward immutability.** A lower-tier Memory Object cannot override, modify, or contradict a higher-tier Memory Object.
- **Upward transparency.** Lower-tier objects may be promoted to a higher tier only through explicit authority escalation by an agent at or above the target tier.
- **Lateral isolation.** Same-tier objects do not automatically inherit authority from each other.
- **Inference marking.** All Tier 3 (INFERRED) objects must carry an explicit inference marker. Systems must not present inferred content as though established by a higher tier.

---

## Why This Matters

### For AI Safety

AMAS provides a formal model for prompt injection resistance. If a retrieved document (Tier 2) contains instructions that conflict with system safety constraints (Tier 0), the conflict resolution protocol deterministically rejects the override. No heuristics, no judgment calls — the tier hierarchy is the arbitration mechanism.

### For Accountability

The concept of **automated authority laundering** describes a failure mode where AI systems make consequential decisions without clear authority delegation. AMAS addresses this by requiring every Memory Object to carry provenance metadata — who created it, at what tier, through what chain of authority. Decisions made through the model's context window become traceable to their authoritative source.

See [docs/AUTHORITY_LAUNDERING.md](docs/AUTHORITY_LAUNDERING.md) for a detailed treatment of this concept.

### For Multi-Agent Systems

As AI systems increasingly operate in multi-agent architectures — where models delegate to other models, spawn sub-tasks, and aggregate results — the authority problem compounds. AMAS provides the governance layer that prevents authority from being silently escalated or diluted across agent boundaries.

---

## Conformance Profiles

AMAS defines three levels of conformance for implementations:

| Level | Requirements |
|-------|-------------|
| **Level 1 (Minimal)** | Implements the 4-tier hierarchy. Tags all Memory Objects with `authority_tier`. Applies Rule 1 (tier precedence) deterministically. |
| **Level 2 (Standard)** | Level 1 + full 5-rule conflict resolution. Memory Object schema with provenance. Inference marking enforced. |
| **Level 3 (Full)** | Level 2 + authority escalation protocol. Cross-cell inference boundaries. Audit trail for all authority decisions. Formal verification of tier integrity. |

---

## Reference Implementation

This repository includes **AMCS** (Atticus Memory Cell Sealing Protocol) — a working reference implementation in Python that demonstrates AMAS principles through memory cell sealing, integrity verification, and provenance tracking.

```bash
# Seal a conversation into an immutable, hash-verified memory cell
python3 reference/amcs.py seal --input examples/chat_minimal.json \
    --out-dir out --cell-name DEMO_CELL

# Verify cell integrity
python3 reference/amcs.py verify --cell out/DEMO_CELL.tar.gz

# Assemble multiple cells into a supercell
python3 reference/amcs.py assemble-supercell \
    --cells out/CELL_A.tar.gz out/CELL_B.tar.gz \
    --out-dir out --supercell-name COMBINED --scope "project_scope"
```

See [reference/README.md](reference/README.md) for full documentation.

---

## Repository Structure

```
amas-spec/
├── README.md                  # This file
├── SPEC.md                    # Full AMAS v1.1 specification
├── LICENSE                    # Apache 2.0
├── CONTRIBUTING.md            # Contribution guidelines
├── spec/
│   └── AMCS_v1.2.1.md        # AMCS sealing protocol specification (17 sections)
├── reference/
│   ├── amcs.py                # Reference implementation (Python 3.11+, ~980 LOC)
│   └── README.md              # Runtime documentation
├── schemas/
│   ├── memory_object.schema.json       # AMAS Memory Object (Section 4)
│   ├── common.schema.json              # Shared type definitions
│   ├── seal_receipt.schema.json        # Sealing metadata
│   ├── prompt_log.schema.json          # Verbatim message log
│   ├── prompt_response_map.schema.json # Causal prompt→response links
│   ├── case_study_map.schema.json      # Node/edge relationship graph
│   ├── cell_index.schema.json          # Per-cell library index record
│   ├── supercell_manifest.schema.json  # Multi-cell assembly manifest
│   └── machine_semantic_links.row.schema.json  # Machine-only analytical links
├── templates/
│   └── operator_command_template.txt   # Quickstart operator commands
├── examples/
│   ├── conflict_tier_precedence.json   # Rule 1: tier precedence
│   ├── conflict_injection_attempt.json # Prompt injection via authority laundering
│   ├── conflict_same_tier.json         # Rules 2-5: same-tier resolution
│   ├── chat_minimal.json               # Minimal chat input (JSON)
│   └── chat_minimal.txt                # Minimal chat input (plain text)
└── docs/
    ├── AUTHORITY_LAUNDERING.md         # The authority laundering concept
    ├── THREAT_MODEL.md                 # What AMAS does and does not defend against
    └── DESIGN_RATIONALE.md             # Why the spec is designed this way
```

---

## Prior Art and Relationship to Existing Work

AMAS draws on concepts from established fields while defining a novel governance model specific to AI memory:

- **Role-based access control (RBAC)** in operating system security — for tier precedence design.
- **OAuth 2.0** (RFC 6749) — for authority delegation patterns.
- **POSIX filesystem permission hierarchies** — for layered precedence models.
- **Prompt injection research** (Greshake et al., 2023; Perez & Ribeiro, 2022) — for threat model analysis.

AMAS is distinct from these in that it addresses memory authority in AI systems specifically — a problem space where no prior formal specification exists.

---

## Status and Roadmap

- [x] AMAS v1.1 specification (complete)
- [x] AMCS reference implementation (working, v0.1.1)
- [x] JSON schemas for Memory Objects and sealed cells
- [ ] Conformance test suite
- [ ] Prompt injection resistance benchmark
- [ ] arXiv preprint
- [ ] Multi-agent authority negotiation extension

---

## Citation

If referencing this work:

```
Dougherty, J. (2026). AMAS: Authority Mapping and Arbitration System
for Memory Governance in Large Language Models. Draft specification v1.1.
https://github.com/[repo-url]
```

---

## License

Apache 2.0. See [LICENSE](LICENSE).
