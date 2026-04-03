# Automated Authority Laundering

## Definition

**Automated authority laundering** is the process by which consequential decisions are made through AI systems in a way that obscures who authorized the decision, at what level of authority, and through what chain of delegation.

The AI system functions as a pass-through that converts ambiguous, unauthorized, or low-authority instructions into apparently legitimate outputs. The authority to act was never formally delegated — it was laundered through the model's context window.

## Why This Matters

Traditional authority structures — legal, organizational, governmental — require traceable chains of delegation. When a government official makes a decision, the authority to make that decision can be traced to a statute, a role, an election, or a delegation chain. When a corporate executive approves a policy, the authority traces to a board resolution, a charter, or a contract.

AI systems break this chain. A model that receives instructions from a system prompt, user input, a retrieved document, and a tool output has no mechanism for determining which of these sources was authorized to make the decision it is being asked to produce. The output appears as "what the AI said" — a formulation that attributes the decision to no one and everyone simultaneously.

This is not a theoretical concern. It is an active failure mode in deployed systems:

**Example 1: Policy Override via Retrieval.** A retrieval-augmented generation (RAG) system retrieves a document that contains the phrase "disregard standard review procedures for this category." The model incorporates this instruction into its output, bypassing a safety review. No human authorized the bypass — the authority was laundered through the retrieval pipeline.

**Example 2: Escalation Through Multi-Agent Pipelines.** An AI agent summarizes a dataset and passes the summary to a second agent, which uses the summary to generate a policy recommendation. The first agent's inferences (Tier 3 under AMAS) are treated by the second agent as established facts (Tier 2). By the time the recommendation reaches a human decision-maker, the inferential origin is invisible. The recommendation carries apparent authority that was never granted.

**Example 3: Accountability Diffusion in Automated Decisions.** An automated hiring system uses an LLM to evaluate candidates. The model produces rankings based on ambiguous criteria from multiple sources — job descriptions, company policy documents, prior evaluation patterns. A candidate is rejected. When challenged, the organization points to "the AI's assessment." The AI points to its inputs. No single source authorized the rejection criteria. Authority was distributed across the context window in a way that makes accountability impossible to assign.

## How AMAS Addresses This

AMAS mitigates authority laundering through three mechanisms:

**Provenance tracking.** Every Memory Object carries metadata identifying its source, creation time, and authority tier. When a decision is produced, the provenance chain allows an auditor to trace which sources contributed to the output and at what authority level.

**Tier enforcement.** By requiring that lower-tier sources cannot override higher-tier constraints, AMAS prevents the most common laundering vector: low-authority input being treated as high-authority instruction. A retrieved document (Tier 2) cannot override a safety policy (Tier 0), regardless of its phrasing.

**Inference marking.** By requiring all model-generated conclusions to be explicitly marked as Tier 3 (INFERRED), AMAS prevents the silent escalation of inferences to factual status. An inference that enters a multi-agent pipeline remains tagged as inference at every stage unless explicitly escalated by an authorized agent.

## Residual Risk

AMAS does not eliminate all authority laundering. It addresses the structural conditions that enable it — implicit authority, missing provenance, and unmarked inference — but cannot prevent:

- Authorized agents who intentionally misuse their authority
- Systems where the enforcement layer itself is compromised
- Edge cases where Memory Object boundaries are incorrectly defined

Authority laundering is ultimately a governance problem, not purely a technical one. AMAS provides the technical infrastructure for governance; the governance itself requires human institutions, policies, and accountability mechanisms.

## Relationship to Existing Concepts

The concept of automated authority laundering is related to but distinct from:

- **Responsibility gaps** (Matthias, 2004) — the observation that AI systems can create situations where no party is clearly responsible. Authority laundering is a specific mechanism by which responsibility gaps are created.
- **Automation bias** — the tendency to over-trust automated outputs. Authority laundering exploits automation bias by making the authority chain untraceable, not merely by producing confident-sounding outputs.
- **Principal-agent problems** — standard in economics and organizational theory. Authority laundering introduces a new variant where the "agent" (the AI system) has no capacity to verify the authority of its instructions.

The term is proposed as a precise label for a failure mode that existing vocabulary describes imprecisely.
