"""Capability, latency, cost and residency constraints for model routing."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelRequirements:
    min_reasoning: int = 1
    max_latency_ms: int = 3000
    max_cost_per_million_tokens: float = 5.0
    residency: str = "local"
    estimated_tokens: int = 1000

    def __post_init__(self):
        if (self.min_reasoning < 1 or self.max_latency_ms < 1 or
                self.max_cost_per_million_tokens < 0 or not self.residency or
                self.estimated_tokens < 1):
            raise ValueError("invalid model routing requirements")


@dataclass(frozen=True)
class ProviderProfile:
    name: str
    reasoning: int
    latency_ms: int
    cost_per_million_tokens: float
    residencies: frozenset[str]

    def __post_init__(self):
        if (not self.name or self.reasoning < 1 or self.latency_ms < 1 or
                self.cost_per_million_tokens < 0 or not self.residencies):
            raise ValueError("invalid model provider profile")


def provider_allowed(profile: ProviderProfile, requirements: ModelRequirements) -> bool:
    return (profile.reasoning >= requirements.min_reasoning
            and profile.latency_ms <= requirements.max_latency_ms
            and profile.cost_per_million_tokens <= requirements.max_cost_per_million_tokens
            and requirements.residency in profile.residencies)
