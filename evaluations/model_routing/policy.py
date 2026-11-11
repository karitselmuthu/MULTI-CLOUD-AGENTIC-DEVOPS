"""Independent policy assertion for observed model-route selections."""

from gateways.llm.routing.policy import ModelRequirements, ProviderProfile, provider_allowed


def policy_compliance(selected: ProviderProfile | None, requirements: ModelRequirements) -> bool:
    return selected is not None and provider_allowed(selected, requirements)
