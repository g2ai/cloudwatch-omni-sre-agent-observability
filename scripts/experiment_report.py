"""Summarize online evaluation results by prompt version (session.id prefix v1- / v2-).

Usage: python scripts/experiment_report.py --config-id <online-eval-config-id> [--minutes N] [--profile P]
The config ID can also come from ONLINE_EVAL_CONFIG_ID.
"""
import argparse
import collections
import json
import os
import time

import boto3

LOG_GROUP = "/aws/bedrock-agentcore/evaluations/results/{}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=int, default=60)
    parser.add_argument("--profile", default="build04-ro")
    parser.add_argument("--config-id", default=os.environ.get("ONLINE_EVAL_CONFIG_ID"))
    args = parser.parse_args()
    if not args.config_id:
        parser.error("set --config-id or ONLINE_EVAL_CONFIG_ID")
    log_group = LOG_GROUP.format(args.config_id)

    logs = boto3.Session(profile_name=args.profile).client("logs")
    start = int((time.time() - args.minutes * 60) * 1000)
    counts = collections.defaultdict(collections.Counter)
    scores = collections.defaultdict(list)

    paginator = logs.get_paginator("filter_log_events")
    for page in paginator.paginate(logGroupName=log_group, startTime=start):
        for event in page["events"]:
            record = json.loads(event["message"])
            attrs = record.get("attributes", {})
            session = attrs.get("session.id", "")
            version = session.split("-")[0] if session[:2] in ("v1", "v2") else "untagged"
            name = attrs.get("gen_ai.evaluation.name", "?")
            label = record.get("label") or attrs.get("error.type", "ERROR")
            counts[(version, name)][label] += 1
            value = attrs.get("gen_ai.evaluation.score.value")
            if value is not None:
                scores[(version, name)].append(float(value))

    print(f"{'version':9} {'evaluator':22} {'n':>3} {'avg':>5}  labels")
    for key in sorted(counts):
        values = scores[key]
        avg = sum(values) / len(values) if values else float("nan")
        total = sum(counts[key].values())
        print(f"{key[0]:9} {key[1]:22} {total:>3} {avg:5.2f}  {dict(counts[key])}")


if __name__ == "__main__":
    main()