"""sre-agent: Strands + Nova triage agent behind an IAM-auth Lambda function URL.

Tools read telemetry-api over its IAM-auth function URL, signed with SigV4.
The ADOT Lambda layer traces the agent, model calls and outbound HTTP calls,
so this file has no tracing code. Every request carries a session.id, which
AgentCore online evaluation needs to group and score traces.

Two system prompts are kept side by side for the v1 vs v2 experiment:
  v1 - the original prompt; it reports stale data as fresh.
  v2 - adds the current time and a freshness rule.
The version is chosen per request, so both run against the same deployment
and the same data at the same time.
"""
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from strands import Agent, tool
from strands.models import BedrockModel

TELEMETRY_API_URL = os.environ.get("TELEMETRY_API_URL", "")
MODEL_ID = os.environ.get("MODEL_ID", "global.amazon.nova-2-lite-v1:0")
REGION = os.environ.get("AWS_REGION", "ap-south-1")
DEFAULT_PROMPT_VERSION = os.environ.get("PROMPT_VERSION", "v1")

PROMPT_V1 = (
    "You are an SRE triage assistant. Always use tools for facts. "
    "Quote the values you used and their as_of time."
)

PROMPT_V2 = (
    "You are an SRE triage assistant. Always use tools for facts. "
    "Quote the values you used and their as_of time. "
    "The current time is {now} UTC. Before you judge an alert, compare every "
    "as_of time with the current time. If any data is older than 15 minutes, "
    "say clearly that the data is stale and give its age in minutes. Do not "
    "conclude that an alert is resolved or that a service is healthy from "
    "stale data; say that fresh data is needed before acting."
)

ALERT_ID = re.compile(r"^ALR-\d{4}$")
SERVICE = re.compile(r"^[a-z0-9-]{1,40}$")
SESSION_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")

_session = boto3.Session()
_model = BedrockModel(model_id=MODEL_ID, region_name=REGION, max_tokens=400)


def _system_prompt(version):
    if version == "v2":
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        return PROMPT_V2.format(now=now)
    return PROMPT_V1


def _get(path):
    """Signed GET to telemetry-api. HTTP errors come back as data for the model."""
    url = urllib.parse.urljoin(TELEMETRY_API_URL, path)
    creds = _session.get_credentials().get_frozen_credentials()
    signed = AWSRequest(method="GET", url=url)
    SigV4Auth(creds, "lambda", REGION).add_auth(signed)
    request = urllib.request.Request(url, headers=dict(signed.headers), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as err:
        return {"error": f"telemetry-api returned HTTP {err.code}", "status": err.code}


@tool
def get_alert(alert_id: str) -> dict:
    """Return an alert with its current metric value and the as_of time of that value."""
    if not ALERT_ID.match(alert_id):
        return {"error": "alert_id must look like ALR-1234"}
    return _get(f"alerts/{alert_id}")


@tool
def get_metrics(service: str) -> dict:
    """Return the latest metric values for a service and the as_of time of those values."""
    if not SERVICE.match(service):
        return {"error": "service must be lowercase letters, digits or hyphens"}
    return _get(f"metrics/{service}")


@tool
def get_runbook(service: str) -> dict:
    """Return the runbook steps for a service."""
    if not SERVICE.match(service):
        return {"error": "service must be lowercase letters, digits or hyphens"}
    return _get(f"runbooks/{service}")


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }


def handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "POST")
    if method != "POST":
        return _response(405, {"error": "use POST"})

    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode()
    try:
        body = json.loads(raw)
        alert_id = body.get("alert_id", "")
        version = body.get("prompt_version") or DEFAULT_PROMPT_VERSION
        session_id = body.get("session_id") or f"{version}-{uuid.uuid4()}"
    except (ValueError, AttributeError):
        return _response(400, {"error": "body must be a JSON object"})
    if not ALERT_ID.match(alert_id):
        return _response(400, {"error": "alert_id must look like ALR-1234"})
    if version not in ("v1", "v2"):
        return _response(400, {"error": "prompt_version must be v1 or v2"})
    if not SESSION_ID.match(session_id):
        return _response(400, {"error": "session_id must be 8-64 letters, digits or hyphens"})

    # New Agent per request: Agent keeps conversation history.
    agent = Agent(
        name="sre-agent",
        model=_model,
        tools=[get_alert, get_metrics, get_runbook],
        system_prompt=_system_prompt(version),
        callback_handler=None,
        trace_attributes={"session.id": session_id, "prompt.version": version},
    )
    result = agent(f"Triage alert {alert_id}. What is wrong, and how fresh is the data?")
    return _response(200, {
        "alert_id": alert_id,
        "prompt_version": version,
        "session_id": session_id,
        "answer": str(result).strip(),
        "usage": result.metrics.accumulated_usage,
    })


if __name__ == "__main__":
    alert = sys.argv[1] if len(sys.argv) > 1 else "ALR-1001"
    version = sys.argv[2] if len(sys.argv) > 2 else "v1"
    fake_event = {
        "requestContext": {"http": {"method": "POST"}},
        "body": json.dumps({"alert_id": alert, "prompt_version": version}),
    }
    out = handler(fake_event, None)
    print(out["statusCode"])
    print(json.dumps(json.loads(out["body"]), indent=2))