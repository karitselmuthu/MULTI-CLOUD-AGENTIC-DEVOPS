import pytest

from gateways.llm.model import MockModelGateway, ModelRequirements, ProviderProfile, RoutedModelGateway
from gateways.llm.quotas import QuotaExceeded, QuotaPolicy, TenantQuotaLedger
from tests.unit.test_model_routing import REQUEST


def test_fallback_stays_within_residency_and_releases_failed_reservation():
    class Unavailable:
        def propose(self, request, *, context=()):
            raise TimeoutError("provider unavailable")
    ledger = TenantQuotaLedger({"team-a": QuotaPolicy(1, 0.01)})
    router = RoutedModelGateway([
        (ProviderProfile("wrong-region", 3, 100, 0.1, frozenset({"us"})), MockModelGateway()),
        (ProviderProfile("unavailable", 3, 100, 1.0, frozenset({"eu"})), Unavailable()),
        (ProviderProfile("fallback", 3, 200, 2.0, frozenset({"eu"})), MockModelGateway()),
    ], ModelRequirements(min_reasoning=3, residency="eu"), tenant="team-a", quotas=ledger)
    assert router.propose(REQUEST)["cloud"] == "aws"
    assert router.last_provider == "fallback"
    assert ledger.usage("team-a") == (1, 0.002)
    with pytest.raises(QuotaExceeded):
        router.propose(REQUEST)


def test_policy_or_invalid_output_never_falls_back():
    class Invalid:
        def propose(self, request, *, context=()):
            raise ValueError("invalid model output")
    router = RoutedModelGateway([
        (ProviderProfile("first", 3, 100, 1.0, frozenset({"eu"})), Invalid()),
        (ProviderProfile("second", 3, 200, 2.0, frozenset({"eu"})), MockModelGateway()),
    ], ModelRequirements(min_reasoning=3, residency="eu"))
    with pytest.raises(ValueError, match="invalid model output"):
        router.propose(REQUEST)
    assert router.last_provider is None
