# Atticus Memory Cell Sealing Protocol (AMCS) v1.2.1 (INTERNAL)
Status: Default-ready (governance-hardened)  
Supersedes: AMCS v1.1  
Primary goal: short, focused chats → sealed epistemic “memory cells” → selective rehydration → durable library → supercell assembly for complex work.

---

## 0) Genesis (mandatory, verbatim)

### 0.1 Fixed Init Seed Prompt (AMCS_INIT_SEED)
**MUST be recorded verbatim in every sealed memory cell:**

> Promote to a case study, so I want you to do is to quantify the data into an indexable structure consisting of multiple case files that collectively create a matrix (basic) tensor (multidimensional). Scope: entire chat;

---

## 1) Core Concept Model

### 1.1 Definitions
- **Memory Cell**  
  An immutable, sealed, portable bundle (`.tar.gz`) containing all artifacts required to rehydrate meaning, evidence, structure, and provenance.

- **Case File**  
  A narrative + evidence-anchored “node.” Narrative is the canonical human meaning for its associated structured artifacts.

- **Matrix**  
  A structured table of *FIRST-ORDER atomic observations* for a single coherent row semantics (one data type). Multiple matrices are allowed and expected when row semantics differ.

- **Tensor (AMCS definition)**  
  A governed collection of multiple case files and their matrices, bound together by a case study that defines how the data may be indexed, cross-referenced, and traversed nonlinearly across the corpus.

- **Case Study**  
  The connective “extra dimension” layer: a typed relationship graph plus the indexing/traversal rules that bind matrices/case files/evidence.

### 1.2 Authority Order (HARD RULE)
If artifacts disagree, resolve authority strictly in this order:
1. Canonical Narrative (ODT + Case File narrative text)
2. FIRST-ORDER observations (matrix rows)
3. SECOND-ORDER interpretations (explicitly labeled)
4. Graph relationships (edges)
5. Tensor rollups/metrics

**No derived artifact may override canonical narrative meaning.** Conflicts are logged, not silently resolved.

### 1.3 Epistemic Strata (HARD RULE)
- **FIRST-ORDER:** direct observations (what was said/shown, what artifact exists)
- **SECOND-ORDER:** interpretations (labeled, traceable to FIRST-ORDER)
- **THIRD-ORDER:** limited implications (optional; traceable downward)
- FOURTH+ is disallowed by default unless explicitly authorized for system-feedback analysis.

---

## 2) Inputs, Scope, and Full-Crawl Rule

### 2.1 Inputs
AMCS consumes a *chat session* consisting of:
- Messages (user + assistant)
- Attachments (ODT, images, PDFs, etc.)
- External references (links, citations, quoted text)

### 2.2 Scope
Default scope is `entire_chat` unless explicitly constrained by operator.

### 2.3 Full-Chat Crawl (HARD RULE)
On invocation:
- The program MUST crawl the entire chat within scope
- Nothing is excluded or omitted
- No pruning/summarization at crawl time
- Both user and assistant messages are FIRST-ORDER artifacts

---

## 3) Default Workflow (ODT-first)

1. Operator drops an `.odt` into the chat (preferred, but optional).
2. The `.odt` becomes the **primary canonical narrative seed** (unless operator says otherwise).
3. Chat artifacts become evidence + observations.
4. AMCS produces:
   - one or more matrices
   - one case file per matrix (minimum)
   - case study graph outputs
   - tensors/rollups derived mechanically
5. Seal everything into a single `.tar.gz` memory cell + seal receipt.

---

## 4) Matrix Construction Rules

### 4.1 When to use multiple matrices
Use multiple matrices when:
- data types differ (different row semantics)
- mixing would reduce clarity or introduce ambiguity
- different schemas/columns are required

### 4.2 Matrix invariants (HARD RULE)
Each matrix row MUST:
- be FIRST-ORDER only (no inferred intent)
- reference its source prompts/responses and any evidence artifacts
- be traceable via stable IDs

Recommended minimal columns/fields:
- `matrix_row_id`
- `row_type` (data-type label)
- `observation_text`
- `timestamp_or_order`
- `source_prompt_ids`
- `source_response_ids`
- `source_artifact_refs`
- `confidence` (optional; ONLY if explicitly defined as mechanical, not interpretive)

---

## 5) Case Files

### 5.1 Minimum: one case file per matrix
Each matrix MUST have a corresponding case file that contains:
- Narrative meaning and boundaries
- Schema reference(s)
- Provenance summary (prompt_id range, response_id range)
- Known gaps / TODOs
- Cross-links to related case files (if any)

### 5.2 Canonical Narrative Rule (HARD RULE)
Case file narrative is authoritative over derived artifacts. If a derived artifact contradicts narrative meaning, log a conflict.

---

## 6) Case Study Graph (“Extra Dimension”)

### 6.1 Graph definition
Graph is a typed relationship layer on top of matrices and artifacts.

- **Nodes:** case_files, evidence_items, actors, claims, events
- **Edges:** append-only, typed, auditable

### 6.2 Required outputs
- `data/case_study_nodes.csv`
- `data/case_study_edges.csv`
- `data/case_study_map.json`
- `data/case_study_adjacency.json` (optional if sparse)

### 6.3 Minimum edge types (controlled vocabulary)
- `references` (A cites B)
- `supports` (A supports B)
- `contradicts` (A contradicts B)
- `responds_to` (reply linkage)
- `same_actor`
- `same_platform`
- `same_frame`
- `timeline_adjacent`
- `evidence_anchor` (claim ↔ evidence artifact)

### 6.4 Edge epistemic class (REQUIRED; HARD RULE)
Every edge MUST declare `edge_epistemic_class`:
- `observational`
- `relational`
- `interpretive`
- `analytical`

Default mappings:
- `evidence_anchor` → observational
- `references`, `responds_to` → relational
- `supports`, `contradicts` → interpretive
- `same_frame`, `timeline_adjacent` → analytical

This prevents graph traversal from being misread as fact.

---

## 7) Tensor Rules (Mechanical Derivation Only)

### 7.1 Tensor derivation constraints (HARD RULE)
Tensors:
- MAY aggregate counts, co-occurrence, adjacency, time buckets
- MUST reference source matrix row IDs
- MUST declare an allowed operation type
- MUST NOT introduce new actors/claims/events
- MUST NOT collapse epistemic strata

Required tensor metadata:
```yaml
tensor_derivation_note:
  source_matrix_rows: [...]
  allowed_operation: count | group | adjacency | temporal
```

---

## 8) Prompt–Response Causality Encoding (REQUIRED)

### 8.1 Prompt Log (canonical conversational order)
File: `data/prompt_log.json`

Each entry MUST include:
- `prompt_id` (stable, sequential)
- `role` (`user`|`assistant`)
- `timestamp` (if available; else null)
- `chat_index` (absolute order)
- `message_text` (verbatim)
- `message_hash` (sha256)

### 8.2 Prompt–Response Map
File: `data/prompt_response_map.json`

Each response MUST declare which prompt(s) it responds to:
- `response_id`
- `responds_to_prompt_ids` (one-to-many allowed)
- `response_text_hash`
- `response_scope_note`

### 8.3 Artifact Attribution (HARD RULE)
Every derived artifact MUST include:
- `source_prompt_ids`
- `source_response_ids`
- `source_message_hashes`

No artifact may exist without causality attribution.

### 8.4 Omission detection (coverage guarantee)
- Every prompt must be linked to a response OR marked `no_response_required`
- Every response must link to ≥1 prompt
- Unlinked items are errors, logged in `logs/causality_verification.log`

---

## 9) Immutability, Delta Cells, and Continuity

### 9.1 Immutability
A sealed memory cell is immutable.

### 9.2 Delta cells (append-only evolution)
New material creates a new cell. Continuity is via references, not mutation.

Delta invariants:
- MUST include `parent_cell_hash`
- MUST share stable `case_study_id`
- MUST declare `delta_type`: `additive` | `corrective` | `contextual`
- MUST NOT rewrite or delete prior artifacts

---

## 10) Library & Supercell Assembly (Selective Rehydration)

### 10.1 Memory Cell Library
A directory/database of immutable sealed memory cells. The library provides lookup and retrieval only.

### 10.2 Required per-cell index record
Each cell MUST publish `cell_index.json` containing:
- `cell_id`, `content_hash`, `created_at`
- `domains`, `topics`
- `entities`, `claims`, `evidence_types`
- `parent_cell_hashes` + `delta_type` (if delta)
- `case_study_id`

Index records are non-authoritative; retrieval aid only.

### 10.3 Supercell definition
A supercell is a task-scoped bundle containing multiple memory cells (copies or references) assembled for a specific job/session.

### 10.4 Supercell assembly constraints (HARD RULE)
- Retrieval-only (no mutation)
- Scope-bounded (no over-inclusion)
- Lineage preserved (hashes + ids retained)
- Contradictions exposed (labeled; not resolved)
- Authority order maintained

### 10.5 Supercell manifest
Every supercell MUST include `supercell_manifest.json`:
- `supercell_id`, `assembly_timestamp`, `assembly_reason`
- `included_cell_hashes`, `assembly_scope`, `assembly_mode`, `notes`

### 10.6 Consolidation passes
Explicit operator-initiated compression with traceability; no overwrites.

---

## 11) Internal-Only Assumption (No Redaction)

AMCS v1.2.1 (INTERNAL) assumes this memory structure is used in a private, operator-controlled environment.

- No redaction pass exists in this profile.
- No content is removed, masked, or deleted.
- Sealed cells are treated as sensitive internal artifacts by default.

**Export boundary rule:** If a cell must be shared outside the trusted environment, create a separate *export artifact* under a distinct protocol/profile.
Do not retrofit masking into an existing internal cell.


## 12) Bundle Layout (Required)

```
/casefiles/         # narrative nodes (canonical meaning)
/data/              # matrices, tensors, graph outputs, prompt logs
/evidence/           # original artifacts (including .odt, screenshots)
/schemas/            # JSON Schemas + CSV column specs
/manifests/          # file hashes + seal receipt + index records
/logs/               # build, verification, redaction, causality checks
/README.md           # read-order + authority rules + how to use
```

`README.md` MUST include:
- Read order (human rehydration path)
- Authority and strata rules
- “What this is NOT” (no silent inference, no rewriting)

---

## 13) Sealing and Verification

### 13.1 Required manifests
- `manifests/file_hashes.sha256` (sha256 for every file)
- `manifests/seal_receipt.json` (required fields below)

### 13.2 seal_receipt.json required fields
- `genesis_prompt_verbatim` (must equal AMCS_INIT_SEED)
- `scope`
- `run_mode_note` (free text; context note only)
- `primary_narrative_source` (`odt`|`chat`|`both`)
- `case_study_id`
- `cell_id`
- `content_hash`
- `build_timestamp`
- `parent_cell_hash` + `delta_type` (if delta)

### 13.3 Verification steps (minimum)
- Verify all hashes match manifests
- Verify referential integrity (no dangling IDs)
- Verify causality coverage (no unlinked prompts/responses)
- Log results to `logs/verification.log`

---

## 14) Trigger Contract

### 14.1 Hard trigger (sealing allowed)
- AMCS_INIT_SEED verbatim OR explicit phrase “Seal as AMCS memory cell”

### 14.2 Soft trigger (prep only; no sealing)
- “form the memory cell”
- “promote to case study”

Soft triggers may generate structures and previews but may not seal.

---

## 15) Operator Quickstart (ODT-first)

1. Attach `.odt` (canonical narrative seed).
2. Paste AMCS_INIT_SEED.
3. Add: “Form the memory cell; ODT is canonical; scope entire chat; include case_study_map outputs; seal to .tar.gz.”

---

## 16) Conformance Checklist (PASS/FAIL)

- [ ] AMCS_INIT_SEED recorded verbatim in seal_receipt.json
- [ ] Entire chat crawled; no omissions
- [ ] prompt_log.json exists and is chronological
- [ ] prompt_response_map.json links every response to ≥1 prompt
- [ ] Every matrix row has source prompt/response attribution
- [ ] Case study nodes/edges files exist + valid references
- [ ] Edge epistemic classes present for all edges
- [ ] Tensors reference matrix row IDs + allowed_operation declared
- [ ] file hashes manifest present and verifies
- [ ] seal_receipt.json complete and consistent
- [ ] If delta: parent hash + delta_type present
- [ ] README.md includes read order + authority rules

---

## 17) Machine-Only Linkages and Indexes (RECOMMENDED)

This section formalizes machine-oriented connections that may be difficult for humans to enumerate manually.
These outputs MUST remain *derived/analytical* and MUST NOT be treated as first-order facts.

### 17.1 Allowed machine-only link types
- **semantic_similarity** (message/claim/row similarity)
- **topic_cluster** (unsupervised grouping)
- **entity_cooccurrence** (windowed co-mention)
- **graph_motif** (structural patterns: triangles, hubs, bridges)
- **path_hint** (shortest-path / high-probability traversal suggestions)

### 17.2 Required labeling (HARD RULE)
All machine-only links MUST be labeled:
- `edge_epistemic_class = analytical`
- `derivation_method` (free text; algorithm name + parameters if known)
- `source_matrix_rows` or `source_prompt_ids/response_ids`

### 17.3 Recommended files (optional but standardized)
- `data/machine_index/semantic_links.csv`
- `data/machine_index/topic_clusters.json`
- `data/machine_index/entity_cooccurrence.csv`
- `data/machine_index/graph_features.json`
- `data/machine_index/path_hints.json`

If present, these files MUST be included in `manifests/file_hashes.sha256` and referenced from `README.md`.

## 17) Non-normative: “Tesseract” framing
“Tesseract” is metaphorical: a graph-of-graphs enabling multi-layer traversal across:
cells → case files → matrices → evidence → entities → cross-cell links.
No implicit inference or mysticism is implied.
