from dataclasses import replace

import pytest

from deployments.rollouts.mock import MockCanaryRollout
from observability.otel.mock import MockTelemetry
from security.audit.evidence import EvidenceBundle
from orchestration.state.recovery import MockRecoveryStore, RecoverySnapshot


def test_canary_failure_rolls_back_and_correlates_incident():
    rollout = MockCanaryRollout().release(
        previous_revision="sha-old", candidate_revision="sha-new",
        canary_healthy=False, full_healthy=True,
    )
    assert rollout.status == "rolled_back"
    assert rollout.active_revision == "sha-old"
    telemetry = MockTelemetry()
    start = telemetry.record(tenant="team-a", workflow_id="w1", phase="planning", status="ok", trace_id="trace-1")
    assert start.attributes["gen_ai.operation.name"] == "invoke_agent"
    telemetry.record(tenant="team-a", workflow_id="w1", phase="canary", status="failed")
    incident = telemetry.incident("team-a", "w1")
    assert incident.trace_id == "trace-1"
    assert incident.failed_phases == ("canary",)
    assert telemetry.failure_count("team-b") == 0


def test_evidence_snapshot_detects_tampering():
    bundle = EvidenceBundle.create("w1", "team-a", ("plan.approved", "canary.failed", "rollback.completed"))
    assert bundle.verify()
    assert len(bundle.event_hashes) == 3
    assert bundle.digest == bundle.event_hashes[-1]
    assert not replace(bundle, events=("plan.approved", "rollback.completed")).verify()
    assert not replace(bundle, event_hashes=tuple(reversed(bundle.event_hashes))).verify()


def test_dr_snapshot_survives_store_restart_and_is_tenant_scoped(tmp_path):
    path = tmp_path / "workflow-recovery.json"
    snapshot = RecoverySnapshot("team-a", "w1", "a" * 64, "sha-old", "rolled_back")
    MockRecoveryStore(path).backup(snapshot)
    recovered = MockRecoveryStore(path)
    assert recovered.restore(tenant="team-a") == snapshot
    with pytest.raises(PermissionError):
        recovered.restore(tenant="team-b")

    path.write_text(path.read_text().replace("sha-old", "sha-new"))
    with pytest.raises(ValueError, match="checksum"):
        recovered.restore(tenant="team-a")
