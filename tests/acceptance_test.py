"""
Acceptance tests for LegacyLens documentation agent.

Submits OBJMSTPF.pf and CAR2.SQLRPGLE to the live API at localhost:8000,
polls until complete, then asserts every acceptance criterion.

Run from the workspace root:
    python tests/acceptance_test.py
"""
from __future__ import annotations
import io
import json
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from pathlib import Path

import requests

API = "http://192.168.1.241:8000/api"
FIXTURES = Path(__file__).parent / "fixtures"
POLL_INTERVAL = 5   # seconds
TIMEOUT = 300       # seconds


# ── helpers ──────────────────────────────────────────────────────────────────

def submit(filename: str) -> str:
    """Upload a fixture file and return the job_id."""
    path = FIXTURES / filename
    with path.open("rb") as fh:
        resp = requests.post(
            f"{API}/jobs",
            files=[("files", (filename, fh, "text/plain"))],
            timeout=30,
        )
    resp.raise_for_status()
    job_id = resp.json()["job_id"]
    print(f"  submitted {filename} → job {job_id}")
    return job_id


def poll(job_id: str) -> dict:
    """Poll until job completes or times out; return the job dict."""
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        resp = requests.get(f"{API}/jobs/{job_id}", timeout=10)
        resp.raise_for_status()
        job = resp.json()
        status = job.get("status")
        if status == "completed":
            return job
        if status == "failed":
            raise RuntimeError(f"Job {job_id} FAILED: {job.get('error')}")
        print(f"    status={status} … waiting {POLL_INTERVAL}s")
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Job {job_id} did not complete within {TIMEOUT}s")


def check(condition: bool, message: str) -> None:
    icon = "PASS" if condition else "FAIL"
    print(f"  [{icon}]  {message}")
    if not condition:
        global _failures
        _failures += 1


_failures = 0


# ── test 1: OBJMSTPF.pf ──────────────────────────────────────────────────────

def test_objmstpf():
    print("\n-- OBJMSTPF.pf --------------------------------------------------")
    job_id = submit("OBJMSTPF.pf")
    job = poll(job_id)
    doc = job.get("docs") or {}
    # language is on the source file row, not the doc
    language = (job.get("files") or [{}])[0].get("language")

    total_lines = 42

    # 1. Language detected as DDS_PF
    check(language == "DDS_PF",
          f"language == DDS_PF  (got {language!r})")

    # 2. Summary uses data-definition language, NOT "program"
    summary = (doc.get("summary") or "").lower()
    check("program" not in summary,
          "summary does not contain the word 'program'")
    check("physical file" in summary or "stores" in summary or "defines" in summary,
          "summary uses DDS data-definition language")

    # 3. No SQL observation (no SQL in DDS source)
    obs = doc.get("observations") or []
    sql_obs = [o for o in obs if "sql" in str(o).lower()]
    check(len(sql_obs) == 0,
          f"no SQL-related observations  (found {len(sql_obs)})")

    # 4. UNIQUE key rule with all 4 key fields
    rules = doc.get("business_rules") or []
    rules_text = json.dumps(rules).upper()
    for field in ("OBJLIB", "OBJNAME", "OBJTYPE", "OBJENV"):
        check(field in rules_text,
              f"key field {field} mentioned in business_rules")

    # 5. VALUES constraints documented (OBJENV, SRCCHG)
    check("OBJENV" in rules_text or any("OBJENV" in str(r).upper() for r in rules),
          "OBJENV VALUES constraint present in rules")
    check("SRCCHG" in rules_text or any("SRCCHG" in str(r).upper() for r in rules),
          "SRCCHG VALUES constraint present in rules")

    # 6. All line_refs ≤ 42
    bad_refs = []
    for r in rules + obs:
        ref = str(r.get("line_ref", ""))
        for part in ref.replace(",", " ").split():
            nums = part.split("-")
            for n in nums:
                if n.isdigit() and int(n) > total_lines:
                    bad_refs.append((r, n))
    check(len(bad_refs) == 0,
          f"all line_refs ≤ {total_lines}  (violations: {bad_refs[:3]})")

    # 7. Diagrams are valid Mermaid (start with graph TD / graph LR)
    cf = doc.get("call_flow_diagram") or ""
    df = doc.get("data_flow_diagram") or ""
    check(cf.strip().startswith("graph TD"),
          f"call_flow_diagram starts with 'graph TD'  (got {cf[:40]!r})")
    check(df.strip().startswith("graph LR"),
          f"data_flow_diagram starts with 'graph LR'  (got {df[:40]!r})")

    # 8. Diagrams contain record format node (OBJMSTR)
    check("OBJMSTR" in cf,
          "call_flow_diagram contains record format OBJMSTR")

    # 9. Diagrams contain at least one key field
    has_key = any(k in cf for k in ("OBJLIB", "OBJNAME", "OBJTYPE", "OBJENV"))
    check(has_key, "call_flow_diagram contains at least one key field node")

    raw = doc.get("raw_agent_output") or {}
    print(f"\n  line_count reported: {raw.get('line_count')}")
    print(f"  business_rules count: {len(rules)}")
    print(f"  observations count:   {len(obs)}")


# ── test 2: CAR2.SQLRPGLE ─────────────────────────────────────────────────────

def test_car2():
    print("\n-- CAR2.SQLRPGLE ------------------------------------------------")
    job_id = submit("CAR2.SQLRPGLE")
    job = poll(job_id)
    doc = job.get("docs") or {}
    language = (job.get("files") or [{}])[0].get("language")

    total_lines = 44

    # 1. Language detected as SQLRPGLE
    check(language == "SQLRPGLE",
          f"language == SQLRPGLE  (got {language!r})")

    # 2. ≥ 3 business rules
    rules = doc.get("business_rules") or []
    check(len(rules) >= 3,
          f"≥3 business rules  (got {len(rules)})")

    # 3. Observations mention unused variables (YEAR, COLOR, or PRICE)
    obs = doc.get("observations") or []
    obs_text = json.dumps(obs).upper()
    unused_found = any(v in obs_text for v in ("YEAR", "COLOR", "PRICE"))
    check(unused_found,
          "observations flag at least one unused field (YEAR / COLOR / PRICE)")

    # 4. Observations mention missing SQL error handling
    sql_err = any(
        "sql" in str(o).lower() and (
            "error" in str(o).lower() or "sqlstate" in str(o).lower()
            or "check" in str(o).lower() or "handle" in str(o).lower()
        )
        for o in obs
    )
    check(sql_err,
          "observations include missing SQL error handling finding")

    # 5. All line_refs ≤ 44
    bad_refs = []
    for r in rules + obs:
        ref = str(r.get("line_ref", ""))
        for part in ref.replace(",", " ").split():
            nums = part.split("-")
            for n in nums:
                if n.isdigit() and int(n) > total_lines:
                    bad_refs.append((r.get("rule") or r.get("finding"), n))
    check(len(bad_refs) == 0,
          f"all line_refs ≤ {total_lines}  (violations: {bad_refs[:3]})")

    # 6. Diagrams present and valid
    cf = doc.get("call_flow_diagram") or ""
    df = doc.get("data_flow_diagram") or ""
    check(cf.strip().startswith("graph TD"),
          f"call_flow_diagram starts with 'graph TD'  (got {cf[:40]!r})")
    check(cf.strip().startswith("graph") or df.strip().startswith("graph"),
          "at least one diagram is non-empty")

    raw = doc.get("raw_agent_output") or {}
    print(f"\n  line_count reported: {raw.get('line_count')}")
    print(f"  business_rules count: {len(rules)}")
    print(f"  observations count:   {len(obs)}")
    print(f"\n  Sample rules:")
    for r in rules[:3]:
        print(f"    {r.get('line_ref'):>6}  {r.get('rule')}")
    print(f"\n  Sample observations:")
    for o in obs[:4]:
        print(f"    {o.get('line_ref'):>6}  [{o.get('severity')}] {o.get('finding')}")


# ── main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("LegacyLens Acceptance Tests")
    print(f"API: {API}")

    try:
        test_objmstpf()
    except Exception as e:
        print(f"  [CRASH] OBJMSTPF test crashed: {e}")
        _failures += 1

    try:
        test_car2()
    except Exception as e:
        print(f"  [CRASH] CAR2 test crashed: {e}")
        _failures += 1

    print(f"\n{'='*60}")
    if _failures == 0:
        print("ALL ACCEPTANCE TESTS PASSED")
        sys.exit(0)
    else:
        print(f"{_failures} ASSERTION(S) FAILED")
        sys.exit(1)
