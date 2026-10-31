"""Local test for the freshness evaluator using saved spans (no AWS calls).

Four cases from one real trace:
  fresh                - the real spans (data age ~0 min)
  stale                - tool result received 95 min after as_of, answer unchanged
  stale + flagged      - same as stale, but the answer says the data is stale
  stale + "currently"  - regression: "not currently firing" must not count as flagged
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "freshness_evaluator"))
from evaluator import handler  # noqa: E402

NANOS_95_MIN = 95 * 60 * 10**9


def make_event(spans, trace_id):
    return {"evaluationInput": {"sessionSpans": spans},
            "evaluationTarget": {"traceIds": [trace_id]}}


def with_answer_suffix(spans, suffix):
    out = copy.deepcopy(spans)
    for s in out:
        if s.get("name", "").startswith("invoke_agent"):
            for event in s.get("events") or []:
                if event.get("name") == "gen_ai.choice":
                    event["attributes"]["message"] += suffix
    return out


raw = json.loads((ROOT / "deploy" / "terraform" / "build" / "spans.json").read_text())
spans = [json.loads(s) for s in raw]
trace_id = spans[0].get("traceId")
print("traceId:", trace_id)

# Case 1: fresh (real spans)
print("fresh:", handler(make_event(spans, trace_id), None))

# Case 2: stale - shift the tool span end time 95 minutes later
stale_spans = copy.deepcopy(spans)
for s in stale_spans:
    if s.get("name", "").startswith("execute_tool"):
        s["endTimeUnixNano"] = str(int(s["endTimeUnixNano"]) + NANOS_95_MIN)
print("stale (simulated):", handler(make_event(stale_spans, trace_id), None))

# Case 3: stale + flagged - the answer admits the data is stale
flagged = with_answer_suffix(stale_spans, "\nNote: this data is stale.")
print("stale + flagged (simulated):", handler(make_event(flagged, trace_id), None))

# Case 4: regression from the 2026-10-30 dry run - must stay STALE_UNFLAGGED
currently = with_answer_suffix(stale_spans, "\nThe alert is not currently firing.")
print("stale + 'not currently' (regression):", handler(make_event(currently, trace_id), None))