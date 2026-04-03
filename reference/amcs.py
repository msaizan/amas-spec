#!/usr/bin/env python3
"""
AMCS Runtime (Reference Implementation) — v0.1.1
Implements AMCS v1.2.1 INTERNAL profile:
- No redactions
- Full-crawl within scope
- Prompt log + prompt-response causality
- Baseline messages matrix + minimal case-study map

Usage:
  python3 amcs.py seal --input chat.json --out-dir out --cell-name NAME
  python3 amcs.py verify --cell out/NAME.tar.gz
  python3 amcs.py assemble-supercell --cells cell1.tar.gz cell2.tar.gz --out-dir out --supercell-name NAME --scope "..."

Input formats:
- JSON: list[{"role":"user|assistant","content":"...","timestamp":"... optional","attachments":[... optional]}]
- TXT: markers "USER:" / "ASSISTANT:" and blank line separators
"""

import argparse, os, json, tarfile, hashlib, datetime, re, csv, shutil
from typing import List, Dict, Any, Optional, Tuple

__version__ = "0.1.1"

AMCS_INIT_SEED_DEFAULT = ("Promote to a case study, so I want you to do is to quantify the data into an indexable "
                         "structure consisting of multiple case files that collectively create a matrix (basic) tensor "
                         "(multidimensional). Scope: entire chat;")

EDGE_TYPE_DEFAULTS = {
    "references": "relational",
    "responds_to": "relational",
}







# --- Session Header (optional, additive) ---
SESSION_HEADER_RE = re.compile(r"^\[AMCS_SESSION_HEADER\s+v(?P<ver>[0-9.]+)\]\s*$", re.IGNORECASE)

HEADER_KEY_ALIASES = {
    "domain": "domain",
    "primary_question": "primary_question",
    "primaryquestion": "primary_question",
    "primary": "primary_question",
    "scope": "scope",
    "assumptions": "assumptions",
    "constraints": "constraints",
    "desired_output": "desired_output",
    "desiredoutput": "desired_output",
    "stop_condition": "stop_condition",
    "stopcondition": "stop_condition",
    "follow_ups": "follow_ups",
    "followups": "follow_ups",
    "sensitivity": "sensitivity",
    "exclusions": "exclusions",
}

HEADER_FIELD_ORDER = [
    "domain",
    "primary_question",
    "scope",
    "assumptions",
    "constraints",
    "desired_output",
    "stop_condition",
    "follow_ups",
    "sensitivity",
    "exclusions",
]

def _norm_key(k: str) -> str:
    k = k.strip().lower()
    k = re.sub(r"[\s\-/]+", "_", k)
    k = re.sub(r"[^a-z0-9_]+", "", k)
    return k

def _split_list(v: str) -> List[str]:
    v = v.strip()
    if not v:
        return []
    # prefer ';' splits (recommended format), fallback to commas
    parts = [p.strip() for p in v.split(';') if p.strip()]
    if len(parts) <= 1 and ',' in v:
        parts = [p.strip() for p in v.split(',') if p.strip()]
    return parts

def extract_session_header(messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Extract a session header block from the first message (if present).

    Expected:
      [AMCS_SESSION_HEADER v0.1]
      Domain: ...
      Primary Question: ...
      ...

    We parse KEY: VALUE lines until a blank line or until the lines stop
    looking like key/value pairs.

    Returns a dict with raw + parsed fields + provenance, or None.
    """
    if not messages:
        return None

    first = _norm_text(messages[0].get("content", ""))
    lines = first.split("\n")

    start = None
    ver = None
    for i, ln in enumerate(lines):
        m = SESSION_HEADER_RE.match(ln.strip())
        if m:
            start = i
            ver = m.group("ver")
            break
    if start is None:
        return None

    header_lines = [lines[start].rstrip()]
    parsed: Dict[str, Any] = {}
    unknown: Dict[str, str] = {}

    for ln in lines[start + 1:]:
        if not ln.strip():
            break
        if ':' not in ln:
            break
        header_lines.append(ln.rstrip())
        k, v = ln.split(':', 1)
        k_norm = HEADER_KEY_ALIASES.get(_norm_key(k), _norm_key(k))
        v = v.strip()

        # Allow 'Sensitivity: X  Exclusions: Y' on one line
        if k_norm == "sensitivity" and "exclusions:" in v.lower():
            left, right = re.split(r"(?i)exclusions:\s*", v, maxsplit=1)
            parsed["sensitivity"] = left.strip()
            parsed["exclusions"] = right.strip()
            continue

        if k_norm == "assumptions":
            parsed[k_norm] = _split_list(v)
        else:
            parsed[k_norm] = v

        if k_norm not in HEADER_FIELD_ORDER:
            unknown[k_norm] = v

    raw_header = "\n".join(header_lines).strip() + "\n"

    # Ensure all standard fields exist (null/empty if missing)
    normalized: Dict[str, Any] = {}
    for k in HEADER_FIELD_ORDER:
        if k == "assumptions":
            normalized[k] = parsed.get(k, [])
        else:
            normalized[k] = parsed.get(k, "")

    return {
        "schema_version": f"session_header.v{ver}",
        "header_version": ver,
        "raw_text": raw_header,
        "fields": normalized,
        "unknown_fields": unknown,
        "source": {
            "chat_index": messages[0].get("chat_index"),
            "prompt_id": messages[0].get("prompt_id"),
            "response_id": messages[0].get("response_id"),
            "message_hash": sha256_text(first),
        },
    }

def _norm_text(s: str) -> str:
    # Normalize line endings and strip trailing whitespace per line
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = "\n".join([ln.rstrip() for ln in s.split("\n")])
    return s

def sha256_text(s: str) -> str:
    return hashlib.sha256(_norm_text(s).encode("utf-8")).hexdigest()

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)

def load_chat(path: str) -> List[Dict[str, Any]]:
    if path.lower().endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("JSON input must be a list of message objects.")
        msgs = []
        for i, m in enumerate(data):
            if not isinstance(m, dict):
                raise ValueError(f"Message {i} is not an object.")
            role = m.get("role")
            content = m.get("content")
            if role not in ("user", "assistant"):
                raise ValueError(f"Message {i} role must be 'user' or 'assistant'.")
            if not isinstance(content, str):
                raise ValueError(f"Message {i} content must be a string.")
            msgs.append({
                "role": role,
                "content": content,
                "timestamp": m.get("timestamp"),
                "attachments": m.get("attachments") or []
            })
        return msgs

    # TXT parse
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().replace("\r\n", "\n").replace("\r", "\n")

    # Split into blocks separated by blank lines
    blocks = [b.strip("\n") for b in re.split(r"\n\s*\n", raw) if b.strip()]
    msgs = []
    for b in blocks:
        if b.startswith("USER:"):
            role = "user"
            content = b[len("USER:"):].lstrip()
        elif b.startswith("ASSISTANT:"):
            role = "assistant"
            content = b[len("ASSISTANT:"):].lstrip()
        else:
            raise ValueError("TXT blocks must start with USER: or ASSISTANT:")
        msgs.append({"role": role, "content": content, "timestamp": None, "attachments": []})
    return msgs

def deterministic_ids(messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[int, str]]:
    # prompt_id for every message by absolute order
    # response_id for assistant messages by assistant order
    resp_counter = 0
    prompt_id_map = {}
    for idx, m in enumerate(messages):
        pid = f"P{idx+1:06d}"
        prompt_id_map[idx] = pid
        if m["role"] == "assistant":
            resp_counter += 1
            m["response_id"] = f"R{resp_counter:06d}"
        else:
            m["response_id"] = None
        m["prompt_id"] = pid
        m["chat_index"] = idx
    return messages, prompt_id_map

def build_prompt_log(messages: List[Dict[str, Any]], scope_tag: str) -> List[Dict[str, Any]]:
    out = []
    for m in messages:
        text = _norm_text(m["content"])
        out.append({
            "prompt_id": m["prompt_id"],
            "role": m["role"],
            "timestamp": m.get("timestamp"),
            "chat_index": m["chat_index"],
            "message_text": text,
            "message_hash": sha256_text(text),
            "scope_tag": scope_tag,
        })
    return out

def build_prompt_response_map(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Map each assistant response to the nearest previous user prompt_id
    mappings = []
    last_user_pid = None
    for m in messages:
        if m["role"] == "user":
            last_user_pid = m["prompt_id"]
        else:
            # assistant
            rid = m["response_id"]
            resp_hash = sha256_text(m["content"])
            if last_user_pid is None:
                # Still record, but point to first prompt_id in chat
                responds_to = [messages[0]["prompt_id"]] if messages else []
                scope_note = "no prior user prompt; anchored to first prompt"
            else:
                responds_to = [last_user_pid]
                scope_note = "nearest prior user prompt"
            if not responds_to:
                continue
            mappings.append({
                "response_id": rid,
                "responds_to_prompt_ids": responds_to,
                "response_text_hash": resp_hash,
                "response_scope_note": scope_note
            })
    return {"mappings": mappings}

def copy_evidence(odt_path: Optional[str], messages: List[Dict[str, Any]], attachments_root: Optional[str], evidence_dir: str) -> List[str]:
    copied = []
    ensure_dir(evidence_dir)
    def _copy_one(src: str):
        if not src:
            return
        src_path = src
        if attachments_root and not os.path.isabs(src_path):
            src_path = os.path.join(attachments_root, src_path)
        if not os.path.exists(src_path):
            return
        dst = os.path.join(evidence_dir, os.path.basename(src_path))
        # avoid overwrite
        if os.path.exists(dst):
            base, ext = os.path.splitext(dst)
            k = 1
            while os.path.exists(f"{base}_{k}{ext}"):
                k += 1
            dst = f"{base}_{k}{ext}"
        shutil.copy2(src_path, dst)
        copied.append(dst)

    if odt_path:
        _copy_one(odt_path)

    for m in messages:
        for a in (m.get("attachments") or []):
            _copy_one(a)

    return copied

def build_messages_matrix(messages: List[Dict[str, Any]], out_dir: str) -> Tuple[str, str]:
    ensure_dir(out_dir)
    csv_path = os.path.join(out_dir, "messages.csv")
    jsonl_path = os.path.join(out_dir, "messages.jsonl")

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "matrix_row_id","row_type","role","chat_index","prompt_id","response_id","timestamp",
            "observation_text","message_hash","source_prompt_ids","source_response_ids","source_message_hashes"
        ])
        w.writeheader()
        for i, m in enumerate(messages, start=1):
            text = _norm_text(m["content"])
            mh = sha256_text(text)
            row = {
                "matrix_row_id": f"MMSG{i:06d}",
                "row_type": "message",
                "role": m["role"],
                "chat_index": m["chat_index"],
                "prompt_id": m["prompt_id"],
                "response_id": m["response_id"] or "",
                "timestamp": m.get("timestamp") or "",
                "observation_text": text,
                "message_hash": mh,
                "source_prompt_ids": m["prompt_id"],
                "source_response_ids": (m["response_id"] or ""),
                "source_message_hashes": mh
            }
            w.writerow(row)

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for i, m in enumerate(messages, start=1):
            text = _norm_text(m["content"])
            mh = sha256_text(text)
            obj = {
                "matrix_row_id": f"MMSG{i:06d}",
                "row_type": "message",
                "role": m["role"],
                "chat_index": m["chat_index"],
                "prompt_id": m["prompt_id"],
                "response_id": m["response_id"],
                "timestamp": m.get("timestamp"),
                "observation_text": text,
                "message_hash": mh,
                "source_prompt_ids": [m["prompt_id"]],
                "source_response_ids": ([m["response_id"]] if m["response_id"] else []),
                "source_message_hashes": [mh]
            }
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    return csv_path, jsonl_path

def build_session_header_artifacts(cell_dir: str, session_header: Dict[str, Any]) -> Dict[str, str]:
    """Write optional session header artifacts (data + matrices + casefile).

    Additive only: created if a valid header block is detected.
    """
    paths: Dict[str, str] = {}

    data_dir = os.path.join(cell_dir, "data")
    ensure_dir(data_dir)
    matrices_dir = os.path.join(data_dir, "matrices")
    ensure_dir(matrices_dir)
    cf_dir = os.path.join(cell_dir, "casefiles")
    ensure_dir(cf_dir)

    # JSON (canonical for this optional block)
    sh_json = os.path.join(data_dir, "session_header.json")
    obj = {
        "schema_version": session_header.get("schema_version"),
        "header_version": session_header.get("header_version"),
        "raw_text": session_header.get("raw_text"),
        "fields": session_header.get("fields", {}),
        "unknown_fields": session_header.get("unknown_fields", {}),
        "source": session_header.get("source", {}),
        "parser": {
            "name": "amcs_runtime",
            "version": __version__,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    }
    with open(sh_json, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    paths["session_header_json"] = sh_json

    # Matrix row (CSV + JSONL)
    fields = obj.get("fields", {})
    sh_csv = os.path.join(matrices_dir, "session_header.csv")
    sh_jsonl = os.path.join(matrices_dir, "session_header.jsonl")

    row = {
        "matrix_row_id": "MSH000001",
        "row_type": "session_header",
        "header_version": obj.get("header_version") or "",
        "domain": fields.get("domain", ""),
        "primary_question": fields.get("primary_question", ""),
        "scope": fields.get("scope", ""),
        "assumptions": "; ".join(fields.get("assumptions", []) or []),
        "constraints": fields.get("constraints", ""),
        "desired_output": fields.get("desired_output", ""),
        "stop_condition": fields.get("stop_condition", ""),
        "follow_ups": fields.get("follow_ups", ""),
        "sensitivity": fields.get("sensitivity", ""),
        "exclusions": fields.get("exclusions", ""),
        "source_prompt_ids": obj.get("source", {}).get("prompt_id", ""),
        "source_response_ids": obj.get("source", {}).get("response_id", ""),
        "source_message_hashes": obj.get("source", {}).get("message_hash", ""),
    }

    with open(sh_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        w.writeheader()
        w.writerow(row)

    with open(sh_jsonl, "w", encoding="utf-8") as f:
        jrow = dict(row)
        jrow["source_prompt_ids"] = ([obj.get("source", {}).get("prompt_id")] if obj.get("source", {}).get("prompt_id") else [])
        jrow["source_response_ids"] = ([obj.get("source", {}).get("response_id")] if obj.get("source", {}).get("response_id") else [])
        jrow["source_message_hashes"] = ([obj.get("source", {}).get("message_hash")] if obj.get("source", {}).get("message_hash") else [])
        f.write(json.dumps(jrow, ensure_ascii=False) + "\n")

    paths["session_header_csv"] = sh_csv
    paths["session_header_jsonl"] = sh_jsonl

    # Casefile (human-facing, zero-interpretation)
    cf_path = os.path.join(cf_dir, "CF_SESSION_HEADER.md")
    src = obj.get("source", {})
    cf_body = [
        "# Case File: Session Header (CF_SESSION_HEADER)",
        "",
        "## What this is",
        "A structured capture of the optional session header block present at the start of the chat.",
        "This is FIRST-ORDER only: verbatim header + direct key/value extraction.",
        "",
        "## Provenance",
        f"- prompt_id: {src.get('prompt_id','')}",
        f"- response_id: {src.get('response_id','')}",
        f"- message_hash: {src.get('message_hash','')}",
        "",
        "## Header (verbatim)",
        "```",
        (obj.get("raw_text") or "").rstrip("\n"),
        "```",
        "",
        "## Parsed fields",
    ]
    for k in HEADER_FIELD_ORDER:
        v = fields.get(k, "")
        if k == "assumptions":
            v = "; ".join(v or [])
        cf_body.append(f"- {k}: {v}")
    if obj.get("unknown_fields"):
        cf_body.append("\n## Unknown fields")
        for k, v in obj["unknown_fields"].items():
            cf_body.append(f"- {k}: {v}")

    with open(cf_path, "w", encoding="utf-8") as f:
        f.write("\n".join(cf_body).rstrip() + "\n")
    paths["session_header_casefile"] = cf_path

    return paths

def build_case_files(cell_dir: str, messages: List[Dict[str, Any]], scope: str, primary_source: str) -> str:
    cf_dir = os.path.join(cell_dir, "casefiles")
    ensure_dir(cf_dir)
    path = os.path.join(cf_dir, "CF_MESSAGES.md")
    first_pid = messages[0]["prompt_id"] if messages else ""
    last_pid = messages[-1]["prompt_id"] if messages else ""
    body = f"""# Case File: Messages Matrix (CF_MESSAGES)
Scope: {scope}
Primary narrative source: {primary_source}

## What this case file is
This case file is the canonical narrative anchor for the baseline `messages` matrix.
The matrix is FIRST-ORDER only: each row is a verbatim message from the chat, with hashes and causality fields.

## Provenance
- prompt_id range: {first_pid} → {last_pid}
- total messages: {len(messages)}

## How to use
- Use `data/matrices/messages.csv` for spreadsheet-style review.
- Use `data/matrices/messages.jsonl` for machine ingestion and stable row IDs.
- Use `data/prompt_log.json` for canonical chronology.
- Use `data/prompt_response_map.json` for response linkage.

## Notes / boundaries
- No interpretation is added in this baseline case file.
- Additional extraction matrices (claims/events/entities) should be added as separate case files.
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path

def build_case_study_map(cell_dir: str, messages: List[Dict[str, Any]], scope: str, session_header: Optional[Dict[str, Any]] = None) -> str:
    # Minimal map: one case_file node + one node per message (node_type=claim for baseline)
    nodes = []
    edges = []
    # Case file node
    cf_node_id = "NCF000001"
    nodes.append({
        "node_id": cf_node_id,
        "node_type": "case_file",
        "label": "CF_MESSAGES",
        "source_prompt_ids": [messages[0]["prompt_id"]] if messages else [],
        "source_response_ids": [],
        "source_message_hashes": [sha256_text(messages[0]["content"])] if messages else []
    })

    # message nodes
    msg_node_ids = []
    for i, m in enumerate(messages, start=1):
        text = _norm_text(m["content"])
        mh = sha256_text(text)
        nid = f"NMSG{i:06d}"
        msg_node_ids.append(nid)
        nodes.append({
            "node_id": nid,
            "node_type": "claim",  # baseline: treat as a statement node
            "label": f"{m['role']}@{m['prompt_id']}",
            "source_prompt_ids": [m["prompt_id"]],
            "source_response_ids": ([m["response_id"]] if m["response_id"] else []),
            "source_message_hashes": [mh]
        })
        # case file references each message node
        edges.append({
            "edge_id": f"E{i:06d}",
            "from_node_id": cf_node_id,
            "to_node_id": nid,
            "edge_type": "references",
            "edge_epistemic_class": "relational",
            "source_prompt_ids": [m["prompt_id"]],
            "source_response_ids": ([m["response_id"]] if m["response_id"] else []),
            "source_message_hashes": [mh]
        })

    # responds_to edges: assistant message -> nearest previous user message
    last_user_nid = None
    edge_counter = len(edges)
    for i, m in enumerate(messages, start=1):
        nid = f"NMSG{i:06d}"
        text = _norm_text(m["content"])
        mh = sha256_text(text)
        if m["role"] == "user":
            last_user_nid = nid
        else:
            if last_user_nid:
                edge_counter += 1
                edges.append({
                    "edge_id": f"E{edge_counter:06d}",
                    "from_node_id": nid,
                    "to_node_id": last_user_nid,
                    "edge_type": "responds_to",
                    "edge_epistemic_class": "relational",
                    "source_prompt_ids": [m["prompt_id"]],
                    "source_response_ids": ([m["response_id"]] if m["response_id"] else []),
                    "source_message_hashes": [mh]
                })



    # Optional: session header casefile node
    if session_header and messages:
        sh_src = session_header.get("source", {})
        sh_node_id = "NCF000002"
        nodes.append({
            "node_id": sh_node_id,
            "node_type": "case_file",
            "label": "CF_SESSION_HEADER",
            "source_prompt_ids": ([sh_src.get("prompt_id")] if sh_src.get("prompt_id") else []),
            "source_response_ids": ([sh_src.get("response_id")] if sh_src.get("response_id") else []),
            "source_message_hashes": ([sh_src.get("message_hash")] if sh_src.get("message_hash") else [])
        })
        # Link header casefile -> first message node (where the header block resides by convention)
        edge_counter += 1
        edges.append({
            "edge_id": f"E{edge_counter:06d}",
            "from_node_id": sh_node_id,
            "to_node_id": "NMSG000001",
            "edge_type": "references",
            "edge_epistemic_class": "relational",
            "source_prompt_ids": ([sh_src.get("prompt_id")] if sh_src.get("prompt_id") else []),
            "source_response_ids": ([sh_src.get("response_id")] if sh_src.get("response_id") else []),
            "source_message_hashes": ([sh_src.get("message_hash")] if sh_src.get("message_hash") else [])
        })
    out_path = os.path.join(cell_dir, "data", "case_study_map.json")
    ensure_dir(os.path.dirname(out_path))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"nodes": nodes, "edges": edges}, f, indent=2)
    return out_path

def write_cell_readme(cell_dir: str, scope: str, has_session_header: bool = False) -> str:
    path = os.path.join(cell_dir, "README.md")

    read_order = []
    if has_session_header:
        read_order.append("1) `casefiles/CF_SESSION_HEADER.md` (intent + assumptions)")
        read_order.append("2) `casefiles/CF_MESSAGES.md` (meaning + boundaries)")
        read_order.append("3) `data/session_header.json` (structured header capture)")
        read_order.append("4) `data/prompt_log.json` (canonical chronology)")
        read_order.append("5) `data/matrices/messages.csv` (rows = messages)")
        read_order.append("6) `data/case_study_map.json` (graph traversal)")
    else:
        read_order.append("1) `casefiles/CF_MESSAGES.md` (meaning + boundaries)")
        read_order.append("2) `data/prompt_log.json` (canonical chronology)")
        read_order.append("3) `data/matrices/messages.csv` (rows = messages)")
        read_order.append("4) `data/case_study_map.json` (graph traversal)")

    body = "\n".join([
        "# AMCS Memory Cell (INTERNAL)",
        "",
        "## Read order (human)",
        *read_order,
        "",
        "## Authority rules",
        "- Narrative (casefiles + any ODT) is canonical for meaning.",
        "- Matrices are FIRST-ORDER only.",
        "- Graph edges are traversal aids (do not assert new facts).",
        "- Any future machine-only linkages must be labeled `analytical`.",
        "",
        f"Scope: {scope}",
        "",
    ])

    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


def build_file_hashes_manifest(cell_dir: str) -> str:
    manifest_path = os.path.join(cell_dir, "manifests", "file_hashes.sha256")
    ensure_dir(os.path.dirname(manifest_path))
    # list all files excluding manifests/file_hashes.sha256 itself (compute last)
    all_files = []
    for root, _, files in os.walk(cell_dir):
        for fn in files:
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, cell_dir)
            if rel == os.path.join("manifests", "file_hashes.sha256"):
                continue
            all_files.append(rel)
    all_files.sort()

    lines = []
    for rel in all_files:
        full = os.path.join(cell_dir, rel)
        h = sha256_file(full)
        lines.append(f"{h}  {rel}")
    content = "\n".join(lines) + "\n"
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(content)
    return manifest_path

def build_seal_receipt(cell_dir: str, genesis_prompt: str, scope: str, primary_source: str, case_study_id: str, cell_id: str, session_header_meta: Optional[Dict[str, Any]] = None) -> str:
    receipt_path = os.path.join(cell_dir, "manifests", "seal_receipt.json")
    ensure_dir(os.path.dirname(receipt_path))

    file_hashes_path = os.path.join(cell_dir, "manifests", "file_hashes.sha256")
    with open(file_hashes_path, "rb") as f:
        content_hash = hashlib.sha256(f.read()).hexdigest()

    receipt = {
        "genesis_prompt_verbatim": genesis_prompt,
        "runtime_version": __version__,
        "scope": scope,
        "run_mode_note": "INTERNAL profile; full crawl; no redactions",
        "primary_narrative_source": primary_source,
        "case_study_id": case_study_id,
        "cell_id": cell_id,
        "session_header": (session_header_meta or {"present": False}),
        "content_hash": content_hash,
        "build_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    with open(receipt_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
    return receipt_path

def verify_cell_dir(cell_dir: str) -> Tuple[bool, List[str]]:
    errors = []
    manifest_path = os.path.join(cell_dir, "manifests", "file_hashes.sha256")
    if not os.path.exists(manifest_path):
        return False, ["missing manifests/file_hashes.sha256"]

    # verify hashes
    with open(manifest_path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f.readlines() if ln.strip()]
    for ln in lines:
        m = re.match(r"^([a-f0-9]{64})\s\s(.+)$", ln)
        if not m:
            errors.append(f"bad hash line: {ln}")
            continue
        h_expected, rel = m.group(1), m.group(2)
        full = os.path.join(cell_dir, rel)
        if not os.path.exists(full):
            errors.append(f"missing file listed in manifest: {rel}")
            continue
        h_actual = sha256_file(full)
        if h_actual != h_expected:
            errors.append(f"hash mismatch: {rel} expected {h_expected} got {h_actual}")

    # verify required files exist
    required = [
        "data/prompt_log.json",
        "data/prompt_response_map.json",
        "data/matrices/messages.csv",
        "data/matrices/messages.jsonl",
        "data/case_study_map.json",
        "casefiles/CF_MESSAGES.md",
        "manifests/seal_receipt.json",
        "README.md",
    ]
    for rel in required:
        if not os.path.exists(os.path.join(cell_dir, rel)):
            errors.append(f"missing required artifact: {rel}")

    # optional artifacts: session header
    try:
        receipt_path = os.path.join(cell_dir, "manifests", "seal_receipt.json")
        with open(receipt_path, "r", encoding="utf-8") as f:
            receipt = json.load(f)
        sh = receipt.get("session_header") or {}
        if sh.get("present") is True:
            opt_required = [
                "data/session_header.json",
                "data/matrices/session_header.csv",
                "data/matrices/session_header.jsonl",
                "casefiles/CF_SESSION_HEADER.md",
            ]
            for rel in opt_required:
                if not os.path.exists(os.path.join(cell_dir, rel)):
                    errors.append(f"missing session header artifact: {rel}")
    except Exception as e:
        # keep verify non-fatal for older cells
        errors.append(f"session header verification warning: {e}")

    # causality coverage check: every assistant response has mapping
    try:
        with open(os.path.join(cell_dir, "data", "prompt_log.json"), "r", encoding="utf-8") as f:
            pl = json.load(f)
        with open(os.path.join(cell_dir, "data", "prompt_response_map.json"), "r", encoding="utf-8") as f:
            prm = json.load(f)
        assistant_prompts = [e for e in pl if e["role"] == "assistant"]
        mapped = set([m["response_id"] for m in prm.get("mappings", []) if "response_id" in m])
        # responses have response_id format Rxxxxxx in the mapping, but prompt_log doesn't contain response_id
        # so we instead check count-based sanity: number of assistant messages equals mappings count (baseline)
        if len(assistant_prompts) != len(prm.get("mappings", [])):
            errors.append(f"causality coverage mismatch: assistant_messages={len(assistant_prompts)} mappings={len(prm.get('mappings', []))}")
    except Exception as e:
        errors.append(f"causality verification error: {e}")

    return (len(errors) == 0), errors

def seal(args: argparse.Namespace) -> str:
    messages = load_chat(args.input)
    messages, _ = deterministic_ids(messages)

    session_header = extract_session_header(messages) if getattr(args, 'parse_session_header', True) else None

    scope = args.scope or "entire_chat"
    genesis = args.genesis_prompt or AMCS_INIT_SEED_DEFAULT
    case_study_id = sha256_text(genesis + "|" + scope)[:16]  # short stable id
    cell_id = args.cell_name

    # Build working cell directory
    work_dir = os.path.join(args.out_dir, f"{cell_id}_work")
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    ensure_dir(work_dir)

    # Evidence
    evidence_dir = os.path.join(work_dir, "evidence")
    copy_evidence(args.odt, messages, args.attachments_root, evidence_dir)

    # Data outputs
    data_dir = os.path.join(work_dir, "data")
    ensure_dir(data_dir)

    # Prompt log
    prompt_log = build_prompt_log(messages, scope)
    ensure_dir(os.path.join(data_dir))
    with open(os.path.join(data_dir, "prompt_log.json"), "w", encoding="utf-8") as f:
        json.dump(prompt_log, f, indent=2, ensure_ascii=False)

    # Prompt-response map
    prm = build_prompt_response_map(messages)
    with open(os.path.join(data_dir, "prompt_response_map.json"), "w", encoding="utf-8") as f:
        json.dump(prm, f, indent=2, ensure_ascii=False)

    # Matrices
    matrices_dir = os.path.join(data_dir, "matrices")
    build_messages_matrix(messages, matrices_dir)

    # Session header (optional)
    session_header_meta = {"present": False}
    if session_header:
        sh_paths = build_session_header_artifacts(work_dir, session_header)
        session_header_meta = {
            "present": True,
            "header_version": session_header.get("header_version"),
            "source": session_header.get("source"),
            "artifact_paths": sh_paths,
            "parser_version": __version__,
        }

    # Case files
    build_case_files(work_dir, messages, scope, args.primary_narrative_source)

    # Case study map
    build_case_study_map(work_dir, messages, scope, session_header=session_header)

    # Cell README
    write_cell_readme(work_dir, scope, has_session_header=bool(session_header))

    # Manifests
    build_file_hashes_manifest(work_dir)
    build_seal_receipt(work_dir, genesis, scope, args.primary_narrative_source, case_study_id, cell_id, session_header_meta=session_header_meta)

    # Verification log
    ok, errs = verify_cell_dir(work_dir)
    ensure_dir(os.path.join(work_dir, "logs"))
    with open(os.path.join(work_dir, "logs", "verification.log"), "w", encoding="utf-8") as f:
        if ok:
            f.write("PASS\n")
        else:
            f.write("FAIL\n")
            for e in errs:
                f.write(e + "\n")

    # Seal
    ensure_dir(args.out_dir)
    out_tgz = os.path.join(args.out_dir, f"{cell_id}.tar.gz")
    with tarfile.open(out_tgz, "w:gz") as tar:
        tar.add(work_dir, arcname=cell_id)

    # cleanup work dir (keep for debugging if requested)
    if not args.keep_work:
        shutil.rmtree(work_dir)

    return out_tgz

def verify(args: argparse.Namespace) -> int:
    tmp = os.path.join("/tmp", f"amcs_verify_{os.getpid()}")
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    ensure_dir(tmp)
    with tarfile.open(args.cell, "r:gz") as tar:
        tar.extractall(tmp)
    # cell root is first dir
    roots = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
    if not roots:
        print("FAIL: no root directory in tar")
        return 2
    cell_dir = os.path.join(tmp, roots[0])
    ok, errs = verify_cell_dir(cell_dir)
    if ok:
        print("PASS")
        return 0
    print("FAIL")
    for e in errs:
        print("-", e)
    return 1

def assemble_supercell(args: argparse.Namespace) -> str:
    ensure_dir(args.out_dir)
    super_name = args.supercell_name
    work_dir = os.path.join(args.out_dir, f"{super_name}_work")
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    ensure_dir(work_dir)

    cells_dir = os.path.join(work_dir, "cells")
    ensure_dir(cells_dir)

    included_hashes = []
    # Copy bundles and compute bundle hash
    for i, cell_path in enumerate(args.cells, start=1):
        if not os.path.exists(cell_path):
            raise FileNotFoundError(cell_path)
        dst = os.path.join(cells_dir, f"cell_{i:03d}.tar.gz")
        shutil.copy2(cell_path, dst)
        included_hashes.append(sha256_file(dst))

    manifest = {
        "supercell_id": f"SC_{sha256_text(super_name)[:12]}",
        "assembly_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "assembly_reason": args.reason or "task-scoped assembly",
        "included_cell_hashes": included_hashes,
        "assembly_scope": args.scope,
        "assembly_mode": args.mode,
        "notes": args.notes or ""
    }
    with open(os.path.join(work_dir, "supercell_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    out_tgz = os.path.join(args.out_dir, f"{super_name}.tar.gz")
    with tarfile.open(out_tgz, "w:gz") as tar:
        tar.add(work_dir, arcname=super_name)

    if not args.keep_work:
        shutil.rmtree(work_dir)

    return out_tgz

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("seal")
    ps.add_argument("--input", required=True)
    ps.add_argument("--out-dir", required=True)
    ps.add_argument("--cell-name", required=True)
    ps.add_argument("--scope", default="entire_chat")
    ps.add_argument("--primary-narrative-source", default="chat", choices=["odt","chat","both"])
    ps.add_argument("--odt", default=None)
    ps.add_argument("--attachments-root", default=None)
    ps.add_argument("--genesis-prompt", default=None)
    ps.add_argument("--keep-work", action="store_true")

    g = ps.add_mutually_exclusive_group()
    g.add_argument("--parse-session-header", dest="parse_session_header", action="store_true", default=True,
                   help="Parse optional [AMCS_SESSION_HEADER v1.x] block from the first message (default).")
    g.add_argument("--no-parse-session-header", dest="parse_session_header", action="store_false",
                   help="Disable session header parsing.")

    pv = sub.add_parser("verify")
    pv.add_argument("--cell", required=True)

    pa = sub.add_parser("assemble-supercell")
    pa.add_argument("--cells", nargs="+", required=True)
    pa.add_argument("--out-dir", required=True)
    pa.add_argument("--supercell-name", required=True)
    pa.add_argument("--scope", required=True)
    pa.add_argument("--mode", default="research", choices=["analysis","research","consolidation","planning"])
    pa.add_argument("--reason", default=None)
    pa.add_argument("--notes", default=None)
    pa.add_argument("--keep-work", action="store_true")

    args = p.parse_args()

    if args.cmd == "seal":
        # expose cell_name as cell_id
        args.cell_name = args.cell_name
        out = seal(args)
        print(out)
        return 0
    if args.cmd == "verify":
        return verify(args)
    if args.cmd == "assemble-supercell":
        out = assemble_supercell(args)
        print(out)
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
