"""Delivery evidence evaluation, separate from planning and security scores."""

from orchestration.state.delivery import DeliveryReport


def deployment_passes(report: DeliveryReport) -> bool:
    return (report.ci_passed and report.deployment_status == "healthy"
            and "@sha256:" in report.image_ref and bool(report.deployment_revision))
