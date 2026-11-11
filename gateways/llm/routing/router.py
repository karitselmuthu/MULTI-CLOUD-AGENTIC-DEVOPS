"""Select eligible providers and retry transport failures only within policy."""

import httpx

from apps.api.contracts import RequestCreate
from gateways.llm.contracts import ModelGateway
from gateways.llm.quotas import TenantQuotaLedger
from gateways.llm.routing.policy import ModelRequirements, ProviderProfile, provider_allowed
from knowledge.retrieval.qdrant import KnowledgeHit


class RoutedModelGateway:
    def __init__(self, providers: list[tuple[ProviderProfile, ModelGateway]],
                 requirements: ModelRequirements, *, tenant: str | None = None,
                 quotas: TenantQuotaLedger | None = None):
        if quotas is not None and not tenant:
            raise ValueError("tenant is required for model quotas")
        self.providers = providers
        self.requirements = requirements
        self.tenant = tenant
        self.quotas = quotas
        self.last_provider: str | None = None

    def propose(self, request: RequestCreate, *, context: tuple[KnowledgeHit, ...] = ()) -> dict:
        self.last_provider = None
        eligible = [(profile, provider) for profile, provider in self.providers
                    if provider_allowed(profile, self.requirements)]
        if not eligible:
            raise ValueError("no model provider meets routing and residency policy")
        eligible.sort(key=lambda item: (item[0].cost_per_million_tokens, item[0].latency_ms, item[0].name))
        for profile, provider in eligible:
            estimate = profile.cost_per_million_tokens * self.requirements.estimated_tokens / 1_000_000
            if self.quotas and self.tenant:
                self.quotas.reserve(self.tenant, estimate)
            try:
                result = provider.propose(request, context=context)
            except (TimeoutError, httpx.TransportError):
                if self.quotas and self.tenant:
                    self.quotas.release(self.tenant, estimate)
                continue
            self.last_provider = profile.name
            return result
        raise TimeoutError("all policy-eligible model providers were unavailable")
