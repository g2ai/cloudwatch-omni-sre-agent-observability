"""POST an alert to the sre-agent function URL, signed with SigV4.

Usage: python scripts/invoke_agent.py <url> <alert_id> [prompt_version] [profile]
"""
import json
import sys
import time
import urllib.error
import urllib.request

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


def invoke(url, alert_id, session, prompt_version=None):
    payload = {"alert_id": alert_id}
    if prompt_version:
        payload["prompt_version"] = prompt_version
    body = json.dumps(payload)
    signed = AWSRequest(method="POST", url=url, data=body,
                        headers={"content-type": "application/json"})
    creds = session.get_credentials().get_frozen_credentials()
    SigV4Auth(creds, "lambda", session.region_name).add_auth(signed)
    request = urllib.request.Request(url, data=body.encode(),
                                     headers=dict(signed.headers), method="POST")
    start = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=70) as resp:
            status, text = resp.status, resp.read().decode()
    except urllib.error.HTTPError as err:
        status, text = err.code, err.read().decode()
    return status, text, time.monotonic() - start


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: invoke_agent.py <url> <alert_id> [prompt_version] [profile]")
    url, alert_id = sys.argv[1], sys.argv[2]
    prompt_version = sys.argv[3] if len(sys.argv) > 3 else None
    profile = sys.argv[4] if len(sys.argv) > 4 else "build04"
    session = boto3.Session(profile_name=profile)
    status, text, seconds = invoke(url, alert_id, session, prompt_version)
    print(f"{status} in {seconds:.1f}s")
    try:
        print(json.dumps(json.loads(text), indent=2))
    except ValueError:
        print(text)


if __name__ == "__main__":
    main()