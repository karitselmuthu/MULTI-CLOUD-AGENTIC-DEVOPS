"""Local security finding contract and mock blocking gate.

SARIF mapping follows: https://docs.github.com/en/code-security/reference/code-scanning/sarif-files/sarif-support
"""

from dataclasses import dataclass


MOCK_TOOLS = ("semgrep-mock", "trivy-mock", "checkov-mock", "gitleaks-mock")


@dataclass(frozen=True)
class Finding:
    tool: str
    rule_id: str
    level: str
    message: str


def mock_scan(content: str) -> list[Finding]:
    findings: list[Finding] = []
    if "DEMO_SECRET=" in content:
        findings.append(Finding("gitleaks-mock", "hardcoded-secret", "error", "Demo secret marker detected"))
    if "subprocess.run(" in content and "shell=True" in content:
        findings.append(Finding("semgrep-mock", "shell-injection", "error", "Shell execution with shell=True"))
    if "VULNERABLE_IMAGE=" in content:
        findings.append(Finding("trivy-mock", "vulnerable-image", "error", "Vulnerable image marker detected"))
    if "PUBLIC_CIDR=" in content:
        findings.append(Finding("checkov-mock", "public-cidr", "error", "Public CIDR marker detected"))
    return findings


def blocking(findings: list[Finding]) -> bool:
    return any(finding.level == "error" for finding in findings)


def to_sarif(findings: list[Finding]) -> dict:
    runs = []
    for tool in MOCK_TOOLS:
        relevant = [finding for finding in findings if finding.tool == tool]
        runs.append({
            "tool": {"driver": {"name": tool, "rules": [
                {"id": rule_id} for rule_id in sorted({finding.rule_id for finding in relevant})
            ]}},
            "results": [{"ruleId": finding.rule_id, "level": finding.level,
                         "message": {"text": finding.message}} for finding in relevant],
        })
    return {"version": "2.1.0", "$schema": "https://json.schemastore.org/sarif-2.1.0.json", "runs": runs}

