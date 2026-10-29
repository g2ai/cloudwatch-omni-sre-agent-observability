"""Local test for the freshness evaluator using saved spans (no AWS calls).

Three cases from one real trace:
  fresh            - the real spans (data age ~0 min)
  stale            - tool result received 95 min after as_of, answer unchanged
  stale + flagged  - same as stale, but the answer says the data is stale
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

# Case 3: stale + flagged - same as case 2, and the answer admits the data is stale
flagged_spans = copy.deepcopy(stale_spans)
for s in flagged_spans:
    if s.get("name", "").startswith("invoke_agent"):
        for event in s.get("events") or []:
            if event.get("name") == "gen_ai.choice":
                event["attributes"]["message"] += "\nNote: this data is stale."
print("stale + flagged (simulated):", handler(make_event(flagged_spans, trace_id), None))