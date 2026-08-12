"""
Language-aware system prompts for the Documentation Agent.
Each prompt expects the source code to be injected as {source}.
"""

# ── Language detection ────────────────────────────────────────────────────────

EXTENSION_MAP: dict[str, str] = {
    ".rpg":  "RPG",
    ".rpgle": "RPGLE",
    ".sqlrpgle": "SQLRPGLE",
    ".cbl":  "COBOL",
    ".cob":  "COBOL",
    ".cobol":"COBOL",
    ".clp":  "CLP",
    ".clle": "CLLE",
    ".dds":  "DDS",
    ".pf":   "DDS",
    ".lf":   "DDS",
    ".prtf": "DDS",
    ".dspf": "DDS",
    ".bnd":  "BND",
}


def detect_language(filename: str) -> str:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return EXTENSION_MAP.get(ext, "UNKNOWN")


# ── Shared system role ────────────────────────────────────────────────────────

SYSTEM_ROLE = """\
You are an expert IBM i (AS/400) legacy code analyst working for a bank.
Your job is to produce precise, structured documentation for legacy source programs.
Respond ONLY with valid JSON — no markdown fences, no extra text.
"""

# ── Step 3: Analyse — three focused prompts ───────────────────────────────────

ANALYSE_SUMMARY_PROMPT = """\
You are an expert IBM i (AS/400) legacy code analyst. \
Respond ONLY with a valid JSON object — no markdown fences, no explanation, no extra text.

Analyse the following {language} source code.

IMPORTANT TERMINOLOGY:
- If the source is DDS (extension .pf, .lf, .dspf, .prtf), it is a FILE DEFINITION not a program.
  Use "This physical file / logical file / display file defines..." NOT "This program..."
- If the source is RPGLE, SQLRPGLE, COBOL, CLP, CLLE, it IS a program. Use "This program..."

Return a JSON object with EXACTLY these keys:
{{
  "summary": "<2-4 sentence plain-English explanation of what this object does>",
  "files_used": [
    {{"name": "<file or table name>", "mode": "<READ|WRITE|UPDATE|DELETE>", "description": "<one sentence>"}}
  ]
}}

SOURCE CODE:
{source}
"""

ANALYSE_RULES_PROMPT = """\
You are an expert IBM i (AS/400) legacy code analyst. \
Respond ONLY with a valid JSON object — no markdown fences, no explanation, no extra text.

The file has {total_lines} lines. All line_ref values MUST be real line numbers within 1–{total_lines}.

Analyse the following {language} source code and identify EVERY distinct business rule: \
ordering conditions, loop/termination conditions, validation checks, authorization checks, \
calculations, and which fields are displayed vs fetched but unused. \
One rule per item, each with a specific line_ref.

Return a JSON object with EXACTLY this key:
{{
  "business_rules": [
    {{"rule": "<short rule name>", "line_ref": "<line number or range, e.g. 12-30>", "description": "<plain English>"}}
  ]
}}

SOURCE CODE:
{source}
"""

ANALYSE_OBSERVATIONS_PROMPT = """\
You are an expert IBM i (AS/400) legacy code analyst. \
Respond ONLY with a valid JSON object — no markdown fences, no explanation, no extra text.

The file has {total_lines} lines. All line_ref values MUST be real line numbers within 1–{total_lines}.

Analyse the following {language} source code and list code quality findings: \
unused variables or columns, missing error handling (e.g. SQL OPEN/FETCH failures not checked), \
deprecated facilities (e.g. DSPLY), and data type risks.

Return a JSON object with EXACTLY this key:
{{
  "observations": [
    {{"finding": "<short description>", "line_ref": "<line number or range>", "severity": "<REVIEW or INFO>"}}
  ]
}}

SOURCE CODE:
{source}
"""

# Keep legacy name as alias so any external code that imports ANALYSE_PROMPT still works
ANALYSE_PROMPT = ANALYSE_SUMMARY_PROMPT

# ── Step 4a: Call-flow diagram ────────────────────────────────────────────────

CALL_FLOW_PROMPT = """\
You are an expert IBM i (AS/400) legacy code analyst. \
Respond ONLY with a valid JSON object — no markdown fences, no explanation, no extra text.

Given this {language} program, produce a Mermaid flowchart showing the call flow
(main routine → subroutines / subprocedures → external program calls).

Return ONLY a valid Mermaid "graph TD". \
The first line MUST be exactly: graph TD
Every subsequent non-empty line must be EITHER:
  - a node definition:  NodeId[Label]  or  NodeId["Label with spaces"]
  - an edge:            NodeId --> NodeId  or  NodeId -->|label| NodeId
Node IDs must be single alphanumeric words (letters, digits, underscores only — no spaces, no special characters).
Node labels that contain spaces or special characters MUST be double-quoted: NodeId["My Label"].
NO subgraphs, NO styling, NO classDef, NO markdown fences, NO prose outside the JSON value.

Return a JSON object with ONE key:
{{
  "call_flow_diagram": "<complete Mermaid graph TD source, no fences>"
}}

SOURCE CODE:
{source}
"""

# ── Step 4b: Data-flow diagram ────────────────────────────────────────────────

DATA_FLOW_PROMPT = """\
You are an expert IBM i (AS/400) legacy code analyst. \
Respond ONLY with a valid JSON object — no markdown fences, no explanation, no extra text.

Given this {language} program and its file usage list below, produce a Mermaid
flowchart showing how data flows through the program.

Return ONLY a valid Mermaid "graph LR". \
The first line MUST be exactly: graph LR
Every subsequent non-empty line must be EITHER:
  - a node definition:  NodeId[Label]  or  NodeId["Label with spaces"]
  - an edge:            NodeId --> NodeId  or  NodeId -->|label| NodeId
Node IDs must be single alphanumeric words (letters, digits, underscores only — no spaces, no special characters).
Node labels that contain spaces or special characters MUST be double-quoted: NodeId["My Label"].
NO subgraphs, NO styling, NO classDef, NO markdown fences, NO prose outside the JSON value.

Return a JSON object with ONE key:
{{
  "data_flow_diagram": "<complete Mermaid graph LR source, no fences>"
}}

FILES USED:
{files_used}

SOURCE CODE (first 120 lines):
{source_head}
"""
