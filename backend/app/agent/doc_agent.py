"""
Documentation Agent — LangGraph 5-step graph.

Steps:
  1. parse    — detect language, basic structure info
  2. chunk    — split source into ≤2 000-token sections
  3. analyse  — LLM → summary, files_used, business_rules  (JSON)
  4. diagram  — LLM → call_flow_diagram + data_flow_diagram (JSON)
  5. assemble — merge all outputs into DocumentationResult dict

The graph state is a plain TypedDict; each node receives and returns it.
"""
from __future__ import annotations

import json
import logging
import re
import textwrap
from typing import Any, TypedDict

logger = logging.getLogger(__name__)

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.prompts import (
    ANALYSE_SUMMARY_PROMPT,
    ANALYSE_RULES_PROMPT,
    ANALYSE_OBSERVATIONS_PROMPT,
    CALL_FLOW_PROMPT,
    DATA_FLOW_PROMPT,
    SYSTEM_ROLE,
    detect_language,
)
from app.config import settings


# ── LLM factory ──────────────────────────────────────────────────────────────

def _build_llm():
    if settings.llm_provider == "watsonx":
        from langchain_ibm import ChatWatsonx
        return ChatWatsonx(
            model_id=settings.watsonx_model,
            url=settings.watsonx_url,
            apikey=settings.watsonx_api_key,
            project_id=settings.watsonx_project_id,
            max_new_tokens=4096,   # langchain-ibm >=0.3 — top-level args, not params={}
            temperature=0,
        )
    if settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            temperature=0,
            max_tokens=4096,
        )
    if settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0,
            format="json",          # forces JSON output — Ollama native feature
        )
    # default: openai
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
        response_format={"type": "json_object"},
    )


_llm = None

def get_llm():
    global _llm
    if _llm is None:
        _llm = _build_llm()
    return _llm


# ── State ─────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    # Inputs
    filename: str
    source: str

    # Step outputs
    language: str
    line_count: int
    chunks: list[str]
    summary: str
    files_used: list[dict]
    business_rules: list[dict]
    observations: list[dict]
    call_flow_diagram: str
    data_flow_diagram: str
    call_flow_fallback: bool
    data_flow_fallback: bool

    # Final
    error: str | None


# ── Helpers ───────────────────────────────────────────────────────────────────

_CHUNK_TOKENS = 2_000          # conservative; ~1 500 source chars ≈ 500 tokens
_CHARS_PER_CHUNK = 6_000       # rough char limit per chunk

def _split_chunks(source: str) -> list[str]:
    """Split source into chunks that respect line boundaries."""
    lines = source.splitlines(keepends=True)
    chunks, current, current_len = [], [], 0
    for line in lines:
        current.append(line)
        current_len += len(line)
        if current_len >= _CHARS_PER_CHUNK:
            chunks.append("".join(current))
            current, current_len = [], 0
    if current:
        chunks.append("".join(current))
    return chunks or [source]


def _extract_json(raw: str) -> dict:
    """
    Robustly extract the first valid JSON object from LLM output.
    Handles: plain JSON, ```json fences, ```  fences, and prose before/after.
    """
    raw = raw.strip()

    # 1. Strip any markdown code fence (```json ... ``` or ``` ... ```)
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fence_match:
        return json.loads(fence_match.group(1))

    # 2. Try the whole string first (clean JSON response)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 3. Find the first { ... } block in the output (Granite adds prose around JSON)
    brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if brace_match:
        return json.loads(brace_match.group(0))

    raise ValueError(f"No JSON object found in LLM response. Raw output: {raw[:500]!r}")


def _llm_json(prompt_text: str) -> dict:
    """Call the LLM with a JSON-mode prompt and return parsed dict."""
    llm = get_llm()
    if settings.llm_provider == "watsonx":
        # Granite does not honour SystemMessage; fold the system role into the human turn
        messages = [HumanMessage(content=f"{SYSTEM_ROLE}\n\n{prompt_text}")]
    else:
        messages = [
            SystemMessage(content=SYSTEM_ROLE),
            HumanMessage(content=prompt_text),
        ]
    response = llm.invoke(messages)
    raw = response.content if hasattr(response, "content") else str(response)
    logger.debug("LLM raw response (first 300 chars): %s", raw[:300])
    return _extract_json(raw)


# ── Graph nodes ───────────────────────────────────────────────────────────────

def node_parse(state: AgentState) -> AgentState:
    """Step 1 — detect language and count lines."""
    language = detect_language(state["filename"])
    line_count = state["source"].count("\n") + 1
    return {**state, "language": language, "line_count": line_count}


def node_chunk(state: AgentState) -> AgentState:
    """Step 2 — split into LLM-sized chunks."""
    chunks = _split_chunks(state["source"])
    return {**state, "chunks": chunks}


def _validate_line_refs(rules: list[dict], total_lines: int) -> list[dict]:
    """
    Check each rule's line_ref against total_lines.
    Clamps out-of-range numbers and sets line_ref_verified accordingly.
    Accepts single numbers ("5") and ranges ("12-30").
    """
    validated = []
    for rule in rules:
        line_ref = str(rule.get("line_ref", "")).strip()
        in_range = True
        clamped_parts = []
        for part in re.split(r"[\s,]+", line_ref):
            # Each part may be "N" or "N-M"
            range_match = re.fullmatch(r"(\d+)(?:-(\d+))?", part)
            if range_match:
                lo = int(range_match.group(1))
                hi = int(range_match.group(2)) if range_match.group(2) else lo
                if lo > total_lines or hi > total_lines:
                    in_range = False
                    lo = min(lo, total_lines)
                    hi = min(hi, total_lines)
                if range_match.group(2):
                    clamped_parts.append(f"{lo}-{hi}")
                else:
                    clamped_parts.append(str(lo))
            else:
                clamped_parts.append(part)  # non-numeric — leave as-is
        new_rule = dict(rule)
        new_rule["line_ref_verified"] = in_range
        if not in_range:
            new_rule["line_ref"] = ", ".join(clamped_parts)
        validated.append(new_rule)
    return validated


def node_analyse(state: AgentState) -> AgentState:
    """Step 3 — three focused LLM calls: summary/files, business rules, observations.

    For multi-chunk files we analyse each chunk and merge the results.
    """
    language = state["language"]
    total_lines = state["line_count"]
    all_files: dict[str, dict] = {}   # keyed by file name to deduplicate
    all_rules: list[dict] = []
    all_observations: list[dict] = []
    summaries: list[str] = []

    for chunk in state["chunks"]:
        # Call 1 — summary + files_used
        try:
            summary_result = _llm_json(
                ANALYSE_SUMMARY_PROMPT.format(language=language, source=chunk)
            )
        except Exception as exc:
            return {**state, "error": f"analyse (summary) step failed: {exc}"}
        summaries.append(summary_result.get("summary", ""))
        for fu in summary_result.get("files_used", []):
            all_files[fu.get("name", "")] = fu

        # Call 2 — business rules
        try:
            rules_result = _llm_json(
                ANALYSE_RULES_PROMPT.format(
                    language=language, total_lines=total_lines, source=chunk
                )
            )
        except Exception as exc:
            return {**state, "error": f"analyse (rules) step failed: {exc}"}
        all_rules.extend(rules_result.get("business_rules", []))

        # Call 3 — observations (non-fatal: bad JSON just gives empty list)
        try:
            obs_result = _llm_json(
                ANALYSE_OBSERVATIONS_PROMPT.format(
                    language=language, total_lines=total_lines, source=chunk
                )
            )
            all_observations.extend(obs_result.get("observations", []))
        except Exception as exc:
            logger.warning("observations step failed (non-fatal): %s", exc)

    # Combine summary sentences; deduplicate similar ones naively
    combined_summary = " ".join(s for s in summaries if s)[:1500]

    # Validate + clamp line refs
    validated_rules = _validate_line_refs(all_rules, total_lines)

    return {
        **state,
        "summary": combined_summary,
        "files_used": list(all_files.values()),
        "business_rules": validated_rules,
        "observations": all_observations,
    }


# Regex for valid Mermaid graph lines: node defs and edges only (no subgraphs/styling)
_MERMAID_LINE_RE = re.compile(
    r"^\s*(?:"
    r"[A-Za-z0-9_]+(?:\[.*?\]|(?:\(.*?\))|(?:\{.*?\}))?"        # node definition (optional label)
    r"(?:\s*-->(?:\|.*?\|)?\s*[A-Za-z0-9_]+(?:\[.*?\]|(?:\(.*?\))|(?:\{.*?\})?)?)?"  # optional edge
    r")\s*$"
)


def _validate_mermaid(diagram: str) -> tuple[bool, str]:
    """
    Validate that every non-empty, non-header line is a simple node/edge.
    Returns (is_valid, first_error_message).
    """
    lines = diagram.strip().splitlines()
    if not lines:
        return False, "empty diagram"
    header = lines[0].strip()
    if not re.match(r"^graph\s+(TD|LR|RL|BT|TB)$", header):
        return False, f"first line must be 'graph TD' or 'graph LR', got: {header!r}"
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        if not _MERMAID_LINE_RE.match(stripped):
            return False, f"invalid Mermaid line: {stripped!r}"
    return True, ""


def _build_fallback_diagram(direction: str, prog_name: str, files_used: list[dict]) -> str:
    """Build a minimal but valid Mermaid diagram from structured data."""
    safe_name = re.sub(r"[^A-Za-z0-9_]", "_", prog_name) or "PROG"
    lines = [f"graph {direction}", f'    {safe_name}["{prog_name}"]']
    seen: set[str] = set()
    for fu in files_used:
        raw = fu.get("name", "")
        node_id = re.sub(r"[^A-Za-z0-9_]", "_", raw) or "FILE"
        if node_id in seen:
            continue
        seen.add(node_id)
        mode = fu.get("mode", "")
        label = f"{raw} ({mode})" if mode else raw
        lines.append(f'    {node_id}["{label}"]')
        if direction == "TD":
            lines.append(f"    {safe_name} --> {node_id}")
        else:
            if mode in ("WRITE", "UPDATE", "DELETE"):
                lines.append(f"    {safe_name} --> {node_id}")
            else:
                lines.append(f"    {node_id} --> {safe_name}")
    return "\n".join(lines)


def _llm_mermaid(prompt_text: str, key: str, retry_on_error: bool = True) -> tuple[str, bool]:
    """
    Call LLM for a Mermaid diagram. Validate; retry once on failure.
    Returns (diagram_string, is_fallback).
    """
    try:
        result = _llm_json(prompt_text)
        diagram = result.get(key, "")
        valid, err = _validate_mermaid(diagram)
        if valid:
            return diagram, False
        if retry_on_error:
            retry_prompt = (
                prompt_text
                + f"\n\nYour previous response failed validation. Error: {err}. "
                "Try again, strictly following the format."
            )
            result2 = _llm_json(retry_prompt)
            diagram2 = result2.get(key, "")
            valid2, _ = _validate_mermaid(diagram2)
            if valid2:
                return diagram2, False
    except Exception:
        pass
    return "", True  # signal caller to use fallback


def node_diagram(state: AgentState) -> AgentState:
    """Step 4 — generate call-flow and data-flow Mermaid diagrams."""
    language = state["language"]
    filename = state["filename"]
    files_used = state.get("files_used", [])
    # Use only first chunk for diagram generation to stay within context limits
    source_head = state["chunks"][0] if state["chunks"] else state["source"]
    source_head_truncated = source_head[:4000]

    prog_name = filename.rsplit(".", 1)[0] if "." in filename else filename

    # Call-flow diagram
    cf_diagram, cf_fallback = _llm_mermaid(
        CALL_FLOW_PROMPT.format(language=language, source=source_head_truncated),
        key="call_flow_diagram",
    )
    if cf_fallback:
        cf_diagram = _build_fallback_diagram("TD", prog_name, files_used)

    # Data-flow diagram
    files_used_text = json.dumps(files_used, indent=2)
    df_diagram, df_fallback = _llm_mermaid(
        DATA_FLOW_PROMPT.format(
            language=language,
            files_used=files_used_text,
            source_head=source_head_truncated[:2000],
        ),
        key="data_flow_diagram",
    )
    if df_fallback:
        df_diagram = _build_fallback_diagram("LR", prog_name, files_used)

    return {
        **state,
        "call_flow_diagram": cf_diagram,
        "data_flow_diagram": df_diagram,
        "call_flow_fallback": cf_fallback,
        "data_flow_fallback": df_fallback,
    }


def node_assemble(state: AgentState) -> AgentState:
    """Step 5 — nothing to compute; state IS the result."""
    return state


# ── Graph wiring ──────────────────────────────────────────────────────────────

from langgraph.graph import StateGraph, END, START  # noqa: E402


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("parse",    node_parse)
    g.add_node("chunk",    node_chunk)
    g.add_node("analyse",  node_analyse)
    g.add_node("diagram",  node_diagram)
    g.add_node("assemble", node_assemble)

    g.add_edge(START,      "parse")
    g.add_edge("parse",    "chunk")
    g.add_edge("chunk",    "analyse")
    g.add_edge("analyse",  "diagram")
    g.add_edge("diagram",  "assemble")
    g.add_edge("assemble", END)

    return g.compile()


_graph = None

def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# ── Public entry point ────────────────────────────────────────────────────────

def run_documentation_agent(filename: str, source: str) -> dict[str, Any]:
    """
    Run the 5-step documentation agent and return the final state dict.
    Raises on unrecoverable errors; returns state with error key on partial failures.
    """
    initial: AgentState = {
        "filename": filename,
        "source": source,
        "language": "",
        "line_count": 0,
        "chunks": [],
        "summary": "",
        "files_used": [],
        "business_rules": [],
        "observations": [],
        "call_flow_diagram": "",
        "data_flow_diagram": "",
        "call_flow_fallback": False,
        "data_flow_fallback": False,
        "error": None,
    }
    final_state = get_graph().invoke(initial)
    return final_state
