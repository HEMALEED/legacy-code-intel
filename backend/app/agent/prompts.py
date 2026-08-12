"""
Language-aware prompt templates for the Documentation Agent.

TEMPLATE_MAP keys:
  RPGLE, SQLRPGLE, RPG  — ILE / free-format / fixed RPG
  COBOL                 — COBOL
  CL                    — CLP / CLLE
  DDS_PF                — physical file  (.pf)
  DDS_LF                — logical file   (.lf)
  DDS_DSPF              — display file   (.dspf / .dspf)
  DDS_PRTF              — printer file   (.prtf)
  DEFAULT               — fallback for unknown types
"""
from __future__ import annotations
from dataclasses import dataclass


# ── Language / subtype detection ─────────────────────────────────────────────

EXTENSION_MAP: dict[str, str] = {
    ".rpg":      "RPG",
    ".rpgle":    "RPGLE",
    ".sqlrpgle": "SQLRPGLE",
    ".cbl":      "COBOL",
    ".cob":      "COBOL",
    ".cobol":    "COBOL",
    ".clp":      "CL",
    ".clle":     "CL",
    ".pf":       "DDS_PF",
    ".lf":       "DDS_LF",
    ".dspf":     "DDS_DSPF",
    ".prtf":     "DDS_PRTF",
    ".dds":      "DDS_PF",   # generic .dds — treat as PF guard
    ".bnd":      "DEFAULT",
}


def detect_language(filename: str) -> str:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return EXTENSION_MAP.get(ext, "DEFAULT")


def is_dds(language: str) -> bool:
    return language.startswith("DDS")


# ── Shared system role ────────────────────────────────────────────────────────

SYSTEM_ROLE = """\
You are an expert IBM i (AS/400) legacy code analyst working for a bank.
Your job is to produce precise, structured documentation for legacy source members.
Respond ONLY with valid JSON — no markdown fences, no extra text.
"""

# ── Prompt template container ─────────────────────────────────────────────────

@dataclass
class PromptSet:
    analyse_prompt:      str
    rules_prompt:        str
    observations_prompt: str
    callflow_prompt:     str   # empty string → use deterministic builder
    dataflow_prompt:     str   # empty string → use deterministic builder


# ═══════════════════════════════════════════════════════════════════════════════
# RPGLE / SQLRPGLE / RPG
# ═══════════════════════════════════════════════════════════════════════════════

_RPGLE_ANALYSE = """\
You are an expert IBM i (AS/400) legacy code analyst.
Respond ONLY with a valid JSON object — no markdown fences, no explanation, no extra text.

Analyse the following {language} program source.

Return a JSON object with EXACTLY these keys:
{{
  "summary": "<2-4 sentence plain-English explanation of what this program does, its purpose, \
and the main processing it performs>",
  "files_used": [
    {{"name": "<DB2 table or file name>", "mode": "<READ|WRITE|UPDATE|DELETE>",
      "description": "<one sentence on how the file is used>"}}
  ]
}}

SOURCE CODE:
{source}
"""

_RPGLE_RULES = """\
You are an expert IBM i (AS/400) legacy code analyst.
Respond ONLY with a valid JSON object — no markdown fences, no explanation, no extra text.

This file has {total_lines} lines. Every line_ref you output MUST be a real line number \
between 1 and {total_lines} (inclusive). Do NOT invent line numbers larger than {total_lines}.

Analyse the following {language} program and identify every distinct business rule present \
in this source: ordering criteria, loop/exit conditions, validation checks, authorisation \
checks, calculations, and conditional branching logic. One rule per item.

Return a JSON object with EXACTLY this key:
{{
  "business_rules": [
    {{"rule": "<short name>", "line_ref": "<line or range within 1-{total_lines}>",
      "description": "<plain English>"}}
  ]
}}

SOURCE CODE:
{source}
"""

_RPGLE_OBS = """\
You are an expert IBM i (AS/400) legacy code analyst.
Respond ONLY with a valid JSON object — no markdown fences, no explanation, no extra text.

This file has {total_lines} lines. Every line_ref you output MUST be a real line number \
between 1 and {total_lines} (inclusive).

Review the following {language} program for code-quality issues. Categories to check:
- Variables or fields declared but never referenced
- SQL cursor operations whose SQLSTATE is never tested after OPEN/FETCH/CLOSE
- Columns fetched from a query but never used in subsequent logic
- Use of deprecated or obsolete RPG/ILE facilities
- Data-type risks (e.g. numeric overflow, character truncation)

Report ONLY findings that actually occur in THIS source.
Never invent a finding to fill the list. If there are none, return {{"observations": []}}.

Return a JSON object with EXACTLY this key:
{{
  "observations": [
    {{"finding": "<concise description>", "line_ref": "<line or range within 1-{total_lines}>",
      "severity": "<REVIEW or INFO>"}}
  ]
}}

SOURCE CODE:
{source}
"""

_RPGLE_CALLFLOW = """\
You are an expert IBM i (AS/400) legacy code analyst.
Respond ONLY with a valid JSON object — no markdown fences, no explanation, no extra text.

Given this {language} program, produce a Mermaid flowchart showing the call flow \
(main entry → subprocedures / subroutines → external CALL statements).

Strict Mermaid rules:
- First line MUST be exactly: graph TD
- Each subsequent non-empty line is EITHER a node definition OR an edge:
    NodeId["Label"]   or   NodeId --> OtherNode   or   NodeId -->|"label"| OtherNode
- Node IDs: letters, digits, underscores ONLY — no spaces, no dots, no special chars.
- Labels with spaces or special chars MUST be double-quoted.
- NO subgraph, NO classDef, NO style, NO click, NO markdown fences.

Return a JSON object with ONE key:
{{
  "call_flow_diagram": "<complete Mermaid graph TD, no fences>"
}}

SOURCE CODE:
{source}
"""

_RPGLE_DATAFLOW = """\
You are an expert IBM i (AS/400) legacy code analyst.
Respond ONLY with a valid JSON object — no markdown fences, no explanation, no extra text.

Given this {language} program and its file usage list, produce a Mermaid flowchart \
showing how data moves through the program (inputs → processing steps → outputs).

Strict Mermaid rules:
- First line MUST be exactly: graph LR
- Each subsequent non-empty line is EITHER a node definition OR an edge.
- Node IDs: letters, digits, underscores ONLY.
- Labels with spaces or special chars MUST be double-quoted.
- NO subgraph, NO classDef, NO style, NO markdown fences.

Return a JSON object with ONE key:
{{
  "data_flow_diagram": "<complete Mermaid graph LR, no fences>"
}}

FILES USED:
{files_used}

SOURCE CODE (first 120 lines):
{source_head}
"""


# ═══════════════════════════════════════════════════════════════════════════════
# COBOL
# ═══════════════════════════════════════════════════════════════════════════════

_COBOL_ANALYSE = _RPGLE_ANALYSE   # structure is similar enough
_COBOL_RULES   = _RPGLE_RULES
_COBOL_OBS = """\
You are an expert IBM i (AS/400) COBOL analyst.
Respond ONLY with a valid JSON object — no markdown fences, no explanation, no extra text.

This file has {total_lines} lines. Every line_ref MUST be between 1 and {total_lines}.

Review the following COBOL program for code-quality issues. Categories to check:
- Data items in WORKING-STORAGE declared but never referenced in PROCEDURE DIVISION
- Missing file status checks after OPEN, READ, WRITE, CLOSE
- Use of deprecated COBOL verbs or IBM i extensions
- Potential numeric overflow in arithmetic statements
- Paragraphs that are defined but never PERFORMed

Report ONLY findings that actually occur in THIS source.
Never invent a finding. If there are none, return {{"observations": []}}.

Return a JSON object with EXACTLY this key:
{{
  "observations": [
    {{"finding": "<concise description>", "line_ref": "<line or range within 1-{total_lines}>",
      "severity": "<REVIEW or INFO>"}}
  ]
}}

SOURCE CODE:
{source}
"""
_COBOL_CALLFLOW  = _RPGLE_CALLFLOW.replace("{language}", "COBOL")
_COBOL_DATAFLOW  = _RPGLE_DATAFLOW.replace("{language}", "COBOL")


# ═══════════════════════════════════════════════════════════════════════════════
# CL / CLLE
# ═══════════════════════════════════════════════════════════════════════════════

_CL_ANALYSE = """\
You are an expert IBM i (AS/400) legacy code analyst.
Respond ONLY with a valid JSON object — no markdown fences, no explanation, no extra text.

Analyse the following CL program source.

Return a JSON object with EXACTLY these keys:
{{
  "summary": "<2-4 sentence plain-English explanation of what this CL procedure does, \
what it calls, and its overall purpose>",
  "files_used": [
    {{"name": "<command, program, or file name>", "mode": "<CALL|READ|WRITE|UPDATE>",
      "description": "<one sentence>"}}
  ]
}}

SOURCE CODE:
{source}
"""

_CL_RULES = _RPGLE_RULES   # same structure
_CL_OBS = """\
You are an expert IBM i (AS/400) CL analyst.
Respond ONLY with a valid JSON object — no markdown fences, no explanation, no extra text.

This file has {total_lines} lines. Every line_ref MUST be between 1 and {total_lines}.

Review the following CL program for code-quality issues. Categories to check:
- Variables declared with DCL but never used
- Missing MONMSG for commands that can fail
- Hardcoded library names that should be parameterised
- Redundant or unreachable IF/ELSE branches

Report ONLY findings that actually occur in THIS source.
Never invent a finding. If there are none, return {{"observations": []}}.

Return a JSON object with EXACTLY this key:
{{
  "observations": [
    {{"finding": "<concise description>", "line_ref": "<line or range within 1-{total_lines}>",
      "severity": "<REVIEW or INFO>"}}
  ]
}}

SOURCE CODE:
{source}
"""
_CL_CALLFLOW  = _RPGLE_CALLFLOW
_CL_DATAFLOW  = _RPGLE_DATAFLOW


# ═══════════════════════════════════════════════════════════════════════════════
# DDS Physical File (DDS_PF)
# ═══════════════════════════════════════════════════════════════════════════════

_DDS_PF_GUARD = """\
CRITICAL: This is IBM i DDS source for a PHYSICAL FILE. \
It is a DATA DEFINITION, NOT a program. \
It contains NO executable logic, NO SQL, NO fetching, NO calculations. \
Do NOT use the words "program", "executes", "fetches", "calculates", or "runs".\
"""

_DDS_PF_ANALYSE = """\
You are an expert IBM i (AS/400) DDS analyst.
Respond ONLY with a valid JSON object — no markdown fences, no explanation, no extra text.

""" + _DDS_PF_GUARD + """

Analyse the following DDS Physical File source and document:
1. Purpose — from any header comments (A* lines) at the top of the file
2. Record format name (R line)
3. Every field defined: name, data type, length/decimals, column heading (TEXT keyword), \
   and any VALUES constraint listed for that field
4. Key fields IN ORDER (all K lines) and whether the UNIQUE keyword is present

Return a JSON object with EXACTLY these keys:
{{
  "summary": "<2-4 sentences: what data this physical file stores, its purpose, \
and the entity it represents — using 'This physical file defines / stores' language>",
  "files_used": [
    {{"name": "<this file's own name>", "mode": "WRITE",
      "description": "Physical file — stores <brief description of records>"}}
  ]
}}

SOURCE CODE:
{source}
"""

_DDS_PF_RULES = """\
You are an expert IBM i (AS/400) DDS analyst.
Respond ONLY with a valid JSON object — no markdown fences, no explanation, no extra text.

""" + _DDS_PF_GUARD + """

This file has {total_lines} lines. Every line_ref MUST be between 1 and {total_lines}.

Analyse the following DDS Physical File source and document ONLY the constraints \
that are explicitly written in this source:
- Each VALUES keyword: list all allowed values and the field it applies to
- The UNIQUE key rule: list ALL key fields in order (from K lines)
- Any CHECK or RANGE constraint present

Do NOT invent constraints. If none are present, return an empty list.

Return a JSON object with EXACTLY this key:
{{
  "business_rules": [
    {{"rule": "<constraint name, e.g. OBJENV VALUES>",
      "line_ref": "<line or range within 1-{total_lines}>",
      "description": "<plain English: field name, allowed values or key sequence>"}}
  ]
}}

SOURCE CODE:
{source}
"""

_DDS_PF_OBS = """\
You are an expert IBM i (AS/400) DDS analyst.
Respond ONLY with a valid JSON object — no markdown fences, no explanation, no extra text.

""" + _DDS_PF_GUARD + """

This file has {total_lines} lines. Every line_ref MUST be between 1 and {total_lines}.

Review the following DDS Physical File for data-definition quality issues. \
Categories relevant to DDS PF only:
- Fields that look like status codes or flags but have no VALUES constraint
- Character fields where a date, time, or timestamp data type would be more appropriate
- Fields missing the TEXT (column heading) keyword
- Unconstrained character fields longer than 100 characters

Report ONLY findings that actually occur in THIS source.
Never invent a finding. If there are none, return {{"observations": []}}.

Return a JSON object with EXACTLY this key:
{{
  "observations": [
    {{"finding": "<concise description>", "line_ref": "<line or range within 1-{total_lines}>",
      "severity": "<REVIEW or INFO>"}}
  ]
}}

SOURCE CODE:
{source}
"""

# DDS PF diagrams are deterministic — no LLM call needed (empty string signals that)
_DDS_PF_CALLFLOW = ""
_DDS_PF_DATAFLOW = ""


# ═══════════════════════════════════════════════════════════════════════════════
# DDS Logical File (DDS_LF)
# ═══════════════════════════════════════════════════════════════════════════════

_DDS_LF_GUARD = """\
CRITICAL: This is IBM i DDS source for a LOGICAL FILE (a DB2 view/index). \
It is a DATA DEFINITION, NOT a program. It selects/omits/sequences records from \
one or more physical files. Do NOT use "program", "executes", or "calculates".\
"""

_DDS_LF_ANALYSE = """\
You are an expert IBM i (AS/400) DDS analyst.
Respond ONLY with a valid JSON object — no markdown fences, no explanation, no extra text.

""" + _DDS_LF_GUARD + """

Analyse the following DDS Logical File source and document:
1. The physical file(s) it is based on (PFILE keyword)
2. Record format(s) and which fields are included
3. Select/omit rules (DYNSLT, SELECT, OMIT lines)
4. Key fields and sequence (K lines), UNIQUE if present

Return a JSON object with EXACTLY these keys:
{{
  "summary": "<2-4 sentences: what data this logical file presents, which PF it is based on, \
and its access path — using 'This logical file defines' language>",
  "files_used": [
    {{"name": "<physical file name from PFILE>", "mode": "READ",
      "description": "Underlying physical file"}}
  ]
}}

SOURCE CODE:
{source}
"""

_DDS_LF_RULES   = _DDS_PF_RULES   # same constraint style
_DDS_LF_OBS     = _DDS_PF_OBS     # same review categories
_DDS_LF_CALLFLOW = ""
_DDS_LF_DATAFLOW = ""


# ═══════════════════════════════════════════════════════════════════════════════
# DDS Display File (DDS_DSPF) — guarded DDS style, no program logic
# ═══════════════════════════════════════════════════════════════════════════════

_DDS_DSPF_GUARD = """\
CRITICAL: This is IBM i DDS source for a DISPLAY FILE (a screen definition). \
It is a DATA DEFINITION, NOT a program. It defines record formats, fields, \
indicators, and function keys for interactive screens. \
Do NOT use "program", "executes", "calculates", or "fetches".\
"""

_DDS_DSPF_ANALYSE = """\
You are an expert IBM i (AS/400) DDS analyst.
Respond ONLY with a valid JSON object — no markdown fences, no explanation, no extra text.

""" + _DDS_DSPF_GUARD + """

Analyse the following DDS Display File source and document:
1. Each record format (R line): its name and purpose (from TEXT or comments)
2. Fields per format: name, usage (I=input, O=output, B=both, H=hidden), \
   and column heading (TEXT keyword)
3. Indicators used and their meaning (from adjacent comments where present)
4. Function keys defined (CFxx/CAxx lines)

Return a JSON object with EXACTLY these keys:
{{
  "summary": "<2-4 sentences: how many record formats this display file defines, \
their purposes, and any notable function keys — using 'This display file defines' language>",
  "files_used": [
    {{"name": "<this display file's own name>", "mode": "WRITE",
      "description": "Display file — defines interactive screen formats"}}
  ]
}}

SOURCE CODE:
{source}
"""

_DDS_DSPF_RULES = _DDS_PF_RULES
_DDS_DSPF_OBS   = _DDS_PF_OBS
_DDS_DSPF_CALLFLOW = ""
_DDS_DSPF_DATAFLOW = ""


# ═══════════════════════════════════════════════════════════════════════════════
# DDS Printer File (DDS_PRTF) — guarded DDS style
# ═══════════════════════════════════════════════════════════════════════════════

_DDS_PRTF_ANALYSE = _DDS_DSPF_ANALYSE.replace(
    "DISPLAY FILE (a screen definition)",
    "PRINTER FILE (a report definition)",
).replace(
    "record formats, fields, indicators, and function keys for interactive screens",
    "record formats and fields for printed reports",
).replace(
    "display file defines",
    "printer file defines",
)
_DDS_PRTF_RULES    = _DDS_PF_RULES
_DDS_PRTF_OBS      = _DDS_PF_OBS
_DDS_PRTF_CALLFLOW = ""
_DDS_PRTF_DATAFLOW = ""


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT (BND, SRVPGM, unknown)
# ═══════════════════════════════════════════════════════════════════════════════

_DEFAULT_ANALYSE = _RPGLE_ANALYSE
_DEFAULT_RULES   = _RPGLE_RULES
_DEFAULT_OBS     = _RPGLE_OBS
_DEFAULT_CALLFLOW = _RPGLE_CALLFLOW
_DEFAULT_DATAFLOW = _RPGLE_DATAFLOW


# ═══════════════════════════════════════════════════════════════════════════════
# Template map
# ═══════════════════════════════════════════════════════════════════════════════

TEMPLATE_MAP: dict[str, PromptSet] = {
    "RPGLE":    PromptSet(_RPGLE_ANALYSE,    _RPGLE_RULES,   _RPGLE_OBS,    _RPGLE_CALLFLOW,    _RPGLE_DATAFLOW),
    "SQLRPGLE": PromptSet(_RPGLE_ANALYSE,    _RPGLE_RULES,   _RPGLE_OBS,    _RPGLE_CALLFLOW,    _RPGLE_DATAFLOW),
    "RPG":      PromptSet(_RPGLE_ANALYSE,    _RPGLE_RULES,   _RPGLE_OBS,    _RPGLE_CALLFLOW,    _RPGLE_DATAFLOW),
    "COBOL":    PromptSet(_COBOL_ANALYSE,    _COBOL_RULES,   _COBOL_OBS,    _COBOL_CALLFLOW,    _COBOL_DATAFLOW),
    "CL":       PromptSet(_CL_ANALYSE,       _CL_RULES,      _CL_OBS,       _CL_CALLFLOW,       _CL_DATAFLOW),
    "DDS_PF":   PromptSet(_DDS_PF_ANALYSE,   _DDS_PF_RULES,  _DDS_PF_OBS,   _DDS_PF_CALLFLOW,   _DDS_PF_DATAFLOW),
    "DDS_LF":   PromptSet(_DDS_LF_ANALYSE,   _DDS_LF_RULES,  _DDS_LF_OBS,   _DDS_LF_CALLFLOW,   _DDS_LF_DATAFLOW),
    "DDS_DSPF": PromptSet(_DDS_DSPF_ANALYSE, _DDS_DSPF_RULES,_DDS_DSPF_OBS, _DDS_DSPF_CALLFLOW, _DDS_DSPF_DATAFLOW),
    "DDS_PRTF": PromptSet(_DDS_PRTF_ANALYSE, _DDS_PRTF_RULES,_DDS_PRTF_OBS, _DDS_PRTF_CALLFLOW, _DDS_PRTF_DATAFLOW),
    "DEFAULT":  PromptSet(_DEFAULT_ANALYSE,  _DEFAULT_RULES, _DEFAULT_OBS,  _DEFAULT_CALLFLOW,  _DEFAULT_DATAFLOW),
}


def get_prompts(language: str) -> PromptSet:
    """Return the PromptSet for a detected language, falling back to DEFAULT."""
    return TEMPLATE_MAP.get(language, TEMPLATE_MAP["DEFAULT"])


# ── Backwards-compat aliases (imported by other modules) ─────────────────────
ANALYSE_SUMMARY_PROMPT      = _RPGLE_ANALYSE
ANALYSE_RULES_PROMPT        = _RPGLE_RULES
ANALYSE_OBSERVATIONS_PROMPT = _RPGLE_OBS
CALL_FLOW_PROMPT            = _RPGLE_CALLFLOW
DATA_FLOW_PROMPT            = _RPGLE_DATAFLOW
ANALYSE_PROMPT              = ANALYSE_SUMMARY_PROMPT
