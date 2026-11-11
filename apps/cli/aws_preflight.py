"""Read-only account and network checks before an AWS sandbox plan.

Sources: https://docs.aws.amazon.com/cli/latest/reference/sts/get-caller-identity.html
         https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-availability-zones.html
"""

import argparse
import ipaddress
import json
import re
import subprocess


def validate_network(region: str, zone: str, vpc_cidr: str, subnet_cidr: str) -> None:
    if not re.fullmatch(r"[a-z]{2}-[a-z-]+-[0-9]", region):
        raise ValueError("invalid AWS Region")
    if not re.fullmatch(re.escape(region) + r"[a-z]", zone):
        raise ValueError("availability zone must belong to the chosen Region")
    vpc = ipaddress.ip_network(vpc_cidr, strict=True)
    subnet = ipaddress.ip_network(subnet_cidr, strict=True)
    if vpc.version != 4 or subnet.version != 4 or not subnet.subnet_of(vpc):
        raise ValueError("private subnet must be IPv4 and contained in the VPC")


def aws_json(profile: str, region: str, operation: list[str]) -> dict:
    result = subprocess.run(
        ["aws", *operation, "--profile", profile, "--region", region,
         "--output", "json", "--no-cli-pager", "--cli-connect-timeout", "5",
         "--cli-read-timeout", "10"],
        check=False, capture_output=True, text=True, timeout=20,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "AWS read-only call failed")
    return json.loads(result.stdout)


def check_identity(profile: str, account_id: str, region: str) -> dict:
    if not profile or not re.fullmatch(r"[0-9]{12}", account_id):
        raise ValueError("profile and a 12-digit approved account ID are required")
    identity = aws_json(profile, region, ["sts", "get-caller-identity"])
    if identity.get("Account") != account_id:
        raise PermissionError("AWS profile resolves to a different account")
    if identity.get("Arn", "").endswith(":root"):
        raise PermissionError("do not use root credentials for Terraform")
    return identity


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only AWS sandbox account and network preflight")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--availability-zone", required=True)
    parser.add_argument("--vpc-cidr", required=True)
    parser.add_argument("--subnet-cidr", required=True)
    args = parser.parse_args()
    try:
        validate_network(args.region, args.availability_zone, args.vpc_cidr, args.subnet_cidr)
        identity = check_identity(args.profile, args.account_id, args.region)
        zones = aws_json(args.profile, args.region, [
            "ec2", "describe-availability-zones", "--zone-names", args.availability_zone,
        ])
        if not any(zone.get("ZoneName") == args.availability_zone and zone.get("State") == "available"
                   for zone in zones.get("AvailabilityZones", [])):
            raise ValueError("availability zone is not available to this account")
    except (ValueError, PermissionError, RuntimeError, subprocess.TimeoutExpired) as exc:
        parser.error(str(exc))
    print(f"Verified AWS account {identity['Account']} ({identity['Arn']}) in {args.region}.")


if __name__ == "__main__":
    main()
