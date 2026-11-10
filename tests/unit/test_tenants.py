import pytest

from security.identity.tenants import TenantPolicy, TenantRegistry


def test_namespace_and_budget_isolation():
    registry = TenantRegistry()
    registry.register(TenantPolicy("team-a", "team-a-sandbox", frozenset({"aws"}), 20))
    with pytest.raises(ValueError, match="namespace"):
        registry.register(TenantPolicy("team-b", "team-a-sandbox", frozenset({"azure"}), 20))
    assert registry.authorize(tenant="team-a", cloud="aws", environment="sandbox", estimated_cost=10).namespace == "team-a-sandbox"
    with pytest.raises(PermissionError, match="target"):
        registry.authorize(tenant="team-a", cloud="azure", environment="sandbox", estimated_cost=10)
    with pytest.raises(PermissionError, match="target"):
        registry.authorize(tenant="team-a", cloud="aws", environment="prod", estimated_cost=10)
    with pytest.raises(PermissionError, match="budget"):
        registry.authorize(tenant="team-a", cloud="aws", environment="sandbox", estimated_cost=21)
