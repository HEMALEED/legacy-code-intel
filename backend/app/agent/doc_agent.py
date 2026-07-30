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
    ANALYSE_PROMPT,
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
            params={"max_new_tokens": 4096, "temperature": 0},
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
    call_flow_diagram: str
    data_flow_diagram: str

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


def node_analyse(state: AgentState) -> AgentState:
    """Step 3 — extract summary, files_used, business_rules from all chunks.

    For multi-chunk files we analyse each chunk and merge the results,
    then do a final consolidation pass on the combined summary text.
    """
    language = state["language"]
    all_files: dict[str, dict] = {}   # keyed by file name to deduplicate
    all_rules: list[dict] = []
    summaries: list[str] = []

    for chunk in state["chunks"]:
        prompt = ANALYSE_PROMPT.format(language=language, source=chunk)
        try:
            result = _llm_json(prompt)
        except Exception as exc:
            return {**state, "error": f"analyse step failed: {exc}"}

        summaries.append(result.get("summary", ""))
        for fu in result.get("files_used", []):
            all_files[fu.get("name", "")] = fu
        all_rules.extend(result.get("business_rules", []))

    # Combine summary sentences; deduplicate similar ones naively
    combined_summary = " ".join(s for s in summaries if s)[:1500]

    return {
        **state,
        "summary": combined_summary,
        "files_used": list(all_files.values()),
        "business_rules": all_rules,
    }


def node_diagram(state: AgentState) -> AgentState:
    """Step 4 — generate call-flow and data-flow Mermaid diagrams."""
    language = state["language"]
    # Use only first chunk for diagram generation to stay within context limits
    source_head = state["chunks"][0] if state["chunks"] else state["source"]
    source_head_truncated = source_head[:4000]

    # Call-flow diagram
    call_flow = ""
    try:
        cf_result = _llm_json(CALL_FLOW_PROMPT.format(
            language=language,
            source=source_head_truncated,
        ))
        call_flow = cf_result.get("call_flow_diagram", "")
    except Exception as exc:
        call_flow = f"graph TD\n    ERROR[\"{exc}\"]"

    # Data-flow diagram
    data_flow = ""
    try:
        files_used_text = json.dumps(state.get("files_used", []), indent=2)
        df_result = _llm_json(DATA_FLOW_PROMPT.format(
            language=language,
            files_used=files_used_text,
            source_head=source_head_truncated[:2000],
        ))
        data_flow = df_result.get("data_flow_diagram", "")
    except Exception as exc:
        data_flow = f"graph LR\n    ERROR[\"{exc}\"]"

    return {**state, "call_flow_diagram": call_flow, "data_flow_diagram": data_flow}


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
        "call_flow_diagram": "",
        "data_flow_diagram": "",
        "error": None,
    }
    final_state = get_graph().invoke(initial)
    return final_state
