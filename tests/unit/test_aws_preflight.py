import pytest

from apps.cli.aws_preflight import check_identity, validate_network


def test_network_requires_subnet_inside_selected_region():
    validate_network("us-east-1", "us-east-1a", "10.70.0.0/16", "10.70.1.0/24")
    with pytest.raises(ValueError, match="contained"):
        validate_network("us-east-1", "us-east-1a", "10.70.0.0/16", "10.71.1.0/24")
    with pytest.raises(ValueError, match="Region"):
        validate_network("us-east-1", "us-west-2a", "10.70.0.0/16", "10.70.1.0/24")


def test_identity_rejects_wrong_account_and_root(monkeypatch):
    monkeypatch.setattr("apps.cli.aws_preflight.aws_json", lambda *_: {
        "Account": "111111111111", "Arn": "arn:aws:iam::111111111111:user/test"
    })
    with pytest.raises(PermissionError, match="different account"):
        check_identity("sandbox", "222222222222", "us-east-1")
    monkeypatch.setattr("apps.cli.aws_preflight.aws_json", lambda *_: {
        "Account": "111111111111", "Arn": "arn:aws:iam::111111111111:root"
    })
    with pytest.raises(PermissionError, match="root"):
        check_identity("sandbox", "111111111111", "us-east-1")
