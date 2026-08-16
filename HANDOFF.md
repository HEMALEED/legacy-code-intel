# LegacyLens — Handoff Note
_Last updated: 2026-08-12_

---

## What Was Done

### Prompt System (Tasks 1, 3, 4)
- Rewrote `backend/app/agent/prompts.py` with a full `TEMPLATE_MAP` keyed by language subtype.
- Added a `PromptSet` dataclass with five fields: `analyse_prompt`, `rules_prompt`, `observations_prompt`, `callflow_prompt`, `dataflow_prompt`.
- Languages covered: `RPGLE`, `SQLRPGLE`, `RPG`, `COBOL`, `CL`, `DDS_PF`, `DDS_LF`, `DDS_DSPF`, `DDS_PRTF`, `DEFAULT`.
- DDS types each have a guard clause (`CRITICAL: This is a DATA DEFINITION, NOT a program`) injected at the top of every prompt.
- All observation prompts use **abstract categories only** — no concrete invented examples. Every prompt ends with: _"Report ONLY findings that actually occur in THIS source. Never invent a finding."_
- `callflow_prompt = ""` and `dataflow_prompt = ""` on all DDS types signals the agent to skip the LLM and use the deterministic builder instead.

### Agent Wiring (Task 2)
- `backend/app/agent/doc_agent.py` now calls `get_prompts(language)` in both `node_analyse` and `node_diagram` instead of using hardcoded RPGLE constants.
- Added `_build_dds_diagram(direction, filename, source)` — a deterministic Mermaid builder that parses `R` (record format) and `K` (key field) lines directly from the DDS source. Always produces valid `graph TD` / `graph LR`. No LLM involved.
- `node_diagram` checks `prompts.callflow_prompt == ""` and routes DDS files to `_build_dds_diagram()`, bypassing `_llm_mermaid()` entirely.

### Line Reference Fixes (Task 5)
- `node_parse` now normalises `\r\n` → `\n` before counting lines, so Windows-saved files report the correct line count.
- `_validate_line_refs` clamps to `1 ≤ lo ≤ hi ≤ total_lines` (previously only clamped the upper bound; `lo=0` was possible).

### Schema Fix (Hotfix)
- `FileUsed.description` and `FileUsed.mode` made optional (`= ""` default) in `backend/app/schemas.py`.
- Old DB rows stored `files_used` entries without a `description` key; this caused `GET /api/jobs` to return HTTP 500 for every request until the fix was deployed.

### Acceptance Tests
- `tests/fixtures/OBJMSTPF.pf` — 42-line DDS physical file with UNIQUE key, VALUES on `OBJENV`/`SRCCHG`/`OBJTYPE`, four K-lines.
- `tests/fixtures/CAR2.SQLRPGLE` — 44-line SQL RPG with unused declared fields and a SQL cursor missing OPEN/FETCH error handling.
- `tests/acceptance_test.py` — 22 assertions, all passing against the live `mistral:7b` model on the RHEL server.

### Git Commits (in order)
| Hash | Description |
|------|-------------|
| `708a9b4` | feat: wire per-language prompts, deterministic DDS diagrams, CRLF fix, line_ref clamp |
| `9f6c1f2` | test: add acceptance tests + fixtures for OBJMSTPF.pf and CAR2.SQLRPGLE |
| `a67cee1` | fix: make FileUsed.description optional to handle old DB rows missing the field |

---

## What Still Needs Doing

### Nice-to-Have / Next Session
- **Multi-file jobs** — `celery_worker.py` only processes `job.files[0]`. If multiple files are uploaded in one job, only the first is documented. Track 2 work.
- **DDS_LF diagrams** — `_build_dds_diagram()` works for PF/LF/DSPF/PRTF but for logical files it would be better to also show the `PFILE` (underlying physical file) as a parent node. Currently shows only record format + key fields.
- **Observation deduplication** — multi-chunk files (>6 000 chars) run the observation prompt once per chunk; identical findings can appear twice. A simple dedup pass by `finding` text would clean this up.
- **`line_ref: "0"`** — the CRLF+clamp fix ensures `lo ≥ 1` going forward, but old DB rows may still have `"0"` stored. A one-time DB migration `UPDATE documentation_results SET observations = ...` could clean historical data if needed.
- **Stale DB rows** — jobs processed before `708a9b4` used RPGLE prompts for all languages. Re-processing old DDS jobs would give correct DDS-guarded documentation. No automation exists for this yet.

---

## Important Decisions & Context

### Deployment
- **RHEL server**: `192.168.1.241`, project at `/ai-data/projects/legacy-code-intel/`
- **Python venv**: `backend/.venv/`
- **Services**: `sudo systemctl restart lcip-api lcip-worker` (never start uvicorn manually — port 8000 conflict)
- **LLM**: Ollama on `localhost:11434`, model `mistral:7b` (also available: `gemma4:12b`, `llama3:8b`, `qwen2.5:3b`)
- **DB**: PostgreSQL in Docker, Redis in Docker (both via `docker-compose.yml`)
- **Frontend**: built React dist served by nginx; SELinux label `httpd_sys_content_t` required on the dist folder

### Key Design Decisions
- `callflow_prompt = ""` is the sentinel that means "use deterministic builder, no LLM" — applies to all four DDS subtypes.
- Language detection is purely by **file extension** (see `EXTENSION_MAP` in `prompts.py`). The `language` field on `SourceFile` rows is written by the Celery worker after the agent runs.
- The `FileUsed`, `BusinessRule`, and `Observation` Pydantic models all have defensive defaults (`= ""`) so old DB rows with missing keys never crash the API.
- `line_ref_verified: bool` is stored per rule/observation — `False` means the LLM gave an out-of-range number that was clamped. The UI does not currently display this flag but it is in the DB.

### Known Gotchas
- PowerShell does not support `&&` — use `;` or `if ($?) { ... }` for sequential commands.
- `git push` exit code is 1 on Windows PowerShell even on success (stderr goes to stdout). Check the SHA range in the output, not the exit code.
- `GET /api/jobs` 500 errors are almost always a `ResponseValidationError` from stale DB data not matching the current Pydantic schema. Fix pattern: add `= ""` or `Optional` default to the offending field in `schemas.py`.
- The Celery worker retries failed tasks twice (10 s countdown). A job stuck in `processing` for >5 min likely hit max retries and is marked `failed` — check `job.error` in the DB or via `GET /api/jobs/{id}`.
