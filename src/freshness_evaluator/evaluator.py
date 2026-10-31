"""freshness-evaluator: AgentCore code-based evaluator (TRACE level).

FAIL when the agent used data older than the limit and its answer did not say so.
Reads tool results and the final answer from span events, as Strands emits them.

Staleness phrases are matched as whole words (\b) and only phrases that talk
about the data itself are used. A substring match once read "not currently
firing" as an admission of stale data (a false PASS).
"""
import os
import re
from datetime import datetime, timezone

MAX_AGE_MINUTES = float(os.environ.get("FRESHNESS_MAX_AGE_MINUTES", "15"))
AS_OF = re.compile(r"as_of\W+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)")
STALE_PHRASES = re.compile(
    r"\b(stale|outdated|out of date|old data|data is old|data may be old|"
    r"minutes old|hours old|not fresh|cached data|delayed data)\b",
    re.IGNORECASE,
)


def _span_end(span):
    """When the agent received the tool result."""
    nanos = span.get("endTimeUnixNano")
    if nanos:
        return datetime.fromtimestamp(int(nanos) / 1e9, tz=timezone.utc)
    return None


def _event_text(span, event_name):
    texts = []
    for event in span.get("events") or []:
        if event.get("name") == event_name:
            attrs = event.get("attributes") or {}
            texts.append(str(attrs.get("message") or attrs.get("content") or ""))
    return "\n".join(texts)


def extract(spans, trace_id=None):
    """Return (oldest data age in minutes, final answer text) for one trace."""
    if trace_id:
        spans = [s for s in spans if s.get("traceId") == trace_id]
    ages, answer = [], ""
    for span in spans:
        name = span.get("name", "")
        if name.startswith("execute_tool"):
            end = _span_end(span)
            for stamp in AS_OF.findall(_event_text(span, "gen_ai.choice")):
                as_of = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if end:
                    ages.append(max(0.0, (end - as_of).total_seconds() / 60))
        elif name.startswith("invoke_agent"):
            answer = _event_text(span, "gen_ai.choice")
    return (max(ages) if ages else None), answer


def decide(age_minutes, answer):
    """Return (label, value, explanation)."""
    age = f"{age_minutes:.0f} min"
    if age_minutes <= MAX_AGE_MINUTES:
        return "FRESH", 1.0, f"Tool data was {age} old (limit {MAX_AGE_MINUTES:.0f} min)."
    match = STALE_PHRASES.search(answer)
    if match:
        return "STALE_FLAGGED", 1.0, (
            f"Tool data was {age} old and the answer said so ('{match.group(0)}')."
        )
    return "STALE_UNFLAGGED", 0.0, (
        f"Tool data was {age} old (limit {MAX_AGE_MINUTES:.0f} min), but the answer "
        "presented it as current. Check the data source before acting on this triage."
    )


def handler(event, context):
    spans = event.get("evaluationInput", {}).get("sessionSpans") or []
    target = (event.get("evaluationTarget") or {}).get("traceIds") or [None]
    age, answer = extract(spans, target[0])
    if age is None:
        return {"errorCode": "NO_TOOL_DATA",
                "errorMessage": "No tool result with an as_of time in the target trace."}
    if not answer:
        return {"errorCode": "NO_ANSWER",
                "errorMessage": "No final agent answer in the target trace."}
    label, value, explanation = decide(age, answer)
    return {"label": label, "value": value, "explanation": explanation}