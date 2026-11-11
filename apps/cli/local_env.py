"""Create one private environment file shared by local API, worker and issuer.

Source: https://docs.python.org/3/library/secrets.html
"""

import argparse
import os
import re
import secrets
from pathlib import Path


def create_local_env(path: Path, requester: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", requester):
        raise ValueError("requester must be a shell-safe email address")
    content = (
        f"LOCAL_DASHBOARD_REQUESTER={requester}\n"
        f"LOCAL_DASHBOARD_TOKEN={secrets.token_hex(24)}\n"
        f"AGENT_SIGNING_KEY={secrets.token_hex(32)}\n"
        "TEMPORAL_ADDRESS=localhost:7233\n"
        "LOCAL_MOCK_APPROVAL_ENABLED=1\n"
    )
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create private local mock credentials")
    parser.add_argument("--path", type=Path, default=Path(".env"))
    parser.add_argument("--requester", default="engineer@example.com")
    args = parser.parse_args()
    create_local_env(args.path, args.requester)
    print(f"Created {args.path}. Source it in the API, worker and approval terminals.")


if __name__ == "__main__":
    main()
