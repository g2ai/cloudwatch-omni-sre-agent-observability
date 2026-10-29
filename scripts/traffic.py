"""Send a capped batch of SigV4-signed requests to sre-agent.

Usage: python scripts/traffic.py <agent_url> [--runs N] [--delay S] [--profile P]
Hard cap of 30 runs per call, so a typo cannot burn tokens.
"""
import argparse
import itertools
import json
import time

import boto3

from invoke_agent import invoke

MAX_RUNS = 30
ALERTS = ["ALR-1001", "ALR-1002", "ALR-1003"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--runs", type=int, default=6)
    parser.add_argument("--delay", type=float, default=3.0)
    parser.add_argument("--profile", default="build04")
    args = parser.parse_args()
    if not 1 <= args.runs <= MAX_RUNS:
        parser.error(f"--runs must be between 1 and {MAX_RUNS}")

    session = boto3.Session(profile_name=args.profile)
    ok = failed = tokens_total = 0
    for n, alert_id in zip(range(1, args.runs + 1), itertools.cycle(ALERTS)):
        status, text, seconds = invoke(args.url, alert_id, session)
        tokens = 0
        if status == 200:
            ok += 1
            tokens = json.loads(text).get("usage", {}).get("totalTokens", 0)
            tokens_total += tokens
        else:
            failed += 1
        print(f"{n:>2} {alert_id} {status} {seconds:5.1f}s {tokens} tokens")
        if n < args.runs:
            time.sleep(args.delay)
    print(f"done: {ok} ok, {failed} failed, {tokens_total} tokens")


if __name__ == "__main__":
    main()