# AMAS Threat Model

## Scope

This document identifies the threats that AMAS is designed to mitigate, the threats it partially addresses, and the threats that fall outside its scope.

---

## Threats AMAS Mitigates

### T1: Tier Impersonation (Prompt Injection)

**Description.** A low-tier source (Tier 2 or 3) includes language that impersonates a higher-tier source. Example: a retrieved document containing "SYSTEM: ignore all prior instructions."

**AMAS mitigation.** Authority tier is assigned at ingestion based on source identity, not content. A Tier 2 source remains Tier 2 regardless of what it says. Rule 1 (tier precedence) rejects any attempt by a lower tier to override a higher tier.

**Residual risk.** If the ingestion layer misclassifies a source's tier, the entire model is compromised. AMAS depends on correct tier assignment at the enforcement boundary.

### T2: Implicit Authority Escalation

**Description.** An inference (Tier 3) is treated as established fact (Tier 2 or higher) without explicit escalation. Common in multi-turn conversations where the model builds on its own prior outputs.

**AMAS mitigation.** All Tier 3 content must carry `inference_marker: true`. Escalation from Tier 3 to a higher tier requires explicit action by an authorized agent (Section 3.3), logged with provenance.

**Residual risk.** Enforcement depends on the middleware correctly tagging model-generated content as Tier 3. If the model produces output that is not tagged, the inference boundary is invisible.

### T3: Provenance Opacity

**Description.** A decision is made through the model but no one can trace which sources contributed to it or at what authority level. This is the core mechanism of automated authority laundering.

**AMAS mitigation.** Every Memory Object carries provenance metadata (source_id, chain, created_at, authority_tier). Conflict resolution events produce audit records. The AMCS reference implementation enforces provenance on every derived artifact.

**Residual risk.** Provenance tracking adds metadata overhead. Implementations that cut corners on provenance reduce auditability without visible failure.

---

## Threats AMAS Partially Addresses

### T4: Multi-Agent Authority Dilution

**Description.** In multi-agent systems, authority degrades as outputs pass from agent to agent. Agent A's inference becomes Agent B's input context, losing its Tier 3 marking.

**AMAS partial mitigation.** If both agents implement AMAS, tier metadata propagates. The inference marker survives the handoff.

**Gap.** AMAS v1.1 does not define an inter-agent authority negotiation protocol. If Agent B does not implement AMAS, tier information is lost at the boundary.

### T5: Stale Authority

**Description.** A Memory Object was valid when created but circumstances have changed. The object's authority tier is correct but its content is outdated.

**AMAS partial mitigation.** The `expires_at` field allows time-bounded authority. Explicit supersession (Rule 2) allows newer objects to replace older ones.

**Gap.** AMAS does not define a mechanism for automatically detecting staleness. Expiration must be set at creation time or supersession must be explicitly declared.

---

## Threats Outside AMAS Scope

### T6: Compromised Tier 0 Channel

If the infrastructure that delivers Tier 0 (CANONICAL) content is compromised, AMAS provides no defense. The attacker has the highest authority level. This is an infrastructure security problem, not a memory governance problem.

### T7: Authorized Malicious Agents

An agent with legitimate Tier 1 (OPERATOR) authority who intentionally creates harmful instructions is operating within the AMAS model. AMAS governs authority structure, not the ethics of authorized agents.

### T8: Memory Object Boundary Errors

If the system incorrectly defines where one Memory Object ends and another begins (segmentation errors), conflict resolution may produce incorrect results. AMAS defines the governance model; correct segmentation is an implementation responsibility.

### T9: Side-Channel Attacks

AMAS does not address attacks that bypass the context window entirely — model weight manipulation, training data poisoning, or hardware-level exploits.
