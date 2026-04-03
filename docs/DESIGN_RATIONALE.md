# AMAS Design Rationale

## Why Four Tiers

The four-tier hierarchy (CANONICAL / OPERATOR / SESSION / INFERRED) reflects the actual authority structure in deployed LLM systems:

- **Tier 0 exists** because every model has behavioral boundaries that should not be overridable by any user or developer. These are constitutional.
- **Tier 1 exists** because developers configure models for specific applications. Their instructions should constrain user behavior but not override platform safety.
- **Tier 2 exists** because runtime context (user messages, tool outputs, retrieved documents) is the operational environment. It should inform behavior but not override configuration.
- **Tier 3 exists** because models generate conclusions that are qualitatively different from their inputs. An inference is not a fact. Treating them identically is how hallucination propagates.

Three tiers would conflate developer and platform authority. Five or more tiers would add resolution complexity without matching real deployment patterns. Four is the minimum that captures the actual authority relationships.

## Why Deterministic Conflict Resolution

AMAS uses deterministic rules (applied in strict order) rather than probabilistic or learned arbitration for three reasons:

1. **Auditability.** A deterministic system produces the same resolution given the same inputs. An auditor can verify that the correct rule was applied. A probabilistic system may produce different results on different runs.

2. **Predictability.** Developers integrating AMAS need to know how conflicts will be resolved before they occur. "It depends on the model's judgment" is not a governance answer.

3. **Simplicity.** Five rules, applied in order, first match wins. Any developer can implement this. Any auditor can verify it. Complexity is the enemy of adoption.

## Why Explicit Inference Marking

The requirement that all Tier 3 content carry `inference_marker: true` exists because the most common authority failure in LLM systems is treating model-generated conclusions as established facts.

This happens in two ways:
- **Within a session:** The model states something in turn 3, then references it as fact in turn 7. The inference has been laundered through conversational context.
- **Across agents:** Agent A's output (which includes inferences) becomes Agent B's input context, where it is treated as Tier 2 source material.

Inference marking makes the epistemic status of every Memory Object visible. It does not prevent anyone from using inferences — it prevents anyone from accidentally treating them as something they are not.

## Why External Enforcement

AMAS is designed to be enforced outside the model, not inside it. This is a deliberate architectural choice:

- LLMs do not natively maintain authority graphs. Adding AMAS compliance to model training would be a research program, not a specification.
- External enforcement is auditable. The enforcement layer can be inspected, tested, and verified independently of the model.
- External enforcement is model-agnostic. AMAS works with any LLM that accepts structured input, not just models trained on AMAS concepts.

The cost of external enforcement is that it requires middleware. The benefit is that it works today, with existing models, without waiting for model providers to adopt the standard.

## Why Immutable Sealed Cells (AMCS)

The AMCS reference implementation uses immutable, hash-verified bundles rather than mutable databases for memory persistence. This choice reflects AMAS principles:

- **Immutability prevents silent revision.** Once sealed, a memory cell cannot be altered without detection. This is the persistence-layer equivalent of tier enforcement.
- **Hash verification prevents tampering.** SHA-256 content hashes allow any party to verify that a cell has not been modified since sealing.
- **Full-crawl prevents selective omission.** The requirement to include all messages (no pruning, no summarization) ensures that provenance chains are complete.

The tradeoff is storage efficiency. Immutable cells accumulate rather than consolidate. Delta cells and supercell assembly provide evolution without mutation.

## Why "Memory Object" Rather Than "Token" or "Message"

AMAS operates at the semantic level — a fact, an instruction, a constraint, a conclusion — rather than at the token or message level.

Tokens are model-internal representations with no stable semantic boundary. A single instruction may span hundreds of tokens. Governing authority at the token level would require attention-mechanism integration that does not exist.

Messages are too coarse. A single user message may contain a question, a correction, a new instruction, and a reference to prior context. Governing authority at the message level would force the entire message to one tier, losing the granularity needed for conflict resolution.

Memory Objects are the right unit because they match how authority actually works: a specific claim has a specific source at a specific authority level.
