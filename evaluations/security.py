"""Security evidence evaluation; OPA policy tests remain an independent gate."""

from orchestration.state.delivery import DeliveryReport


def security_passes(report: DeliveryReport) -> bool:
    return report.security_passed and report.supply_chain_passed
