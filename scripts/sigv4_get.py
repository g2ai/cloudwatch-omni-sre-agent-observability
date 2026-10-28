"""GET an IAM-auth Lambda function URL, signed with SigV4."""
import sys
import urllib.error
import urllib.request

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: sigv4_get.py <url> [profile]")
    url = sys.argv[1]
    profile = sys.argv[2] if len(sys.argv) > 2 else "build04"

    session = boto3.Session(profile_name=profile)
    creds = session.get_credentials().get_frozen_credentials()
    signed = AWSRequest(method="GET", url=url)
    SigV4Auth(creds, "lambda", session.region_name).add_auth(signed)

    request = urllib.request.Request(url, headers=dict(signed.headers), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            print(resp.status)
            print(resp.read().decode())
    except urllib.error.HTTPError as err:
        print(err.code)
        print(err.read().decode())


if __name__ == "__main__":
    main()