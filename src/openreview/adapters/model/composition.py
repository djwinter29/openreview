from __future__ import annotations

from collections.abc import Callable

from openreview.adapters.model.runtime import ConfiguredReviewModelGateway, RuntimeModelGateway, openai_transport, anthropic_transport, deepseek_transport
from openreview.ports.model import AnthropicModelConfig, DeepSeekModelConfig, ModelProviderConfig, OpenAIModelConfig, ReviewModelGateway


ModelComposer = Callable[[ModelProviderConfig], ReviewModelGateway]


def _compose_openai(config: ModelProviderConfig) -> ReviewModelGateway:
    if not isinstance(config, OpenAIModelConfig):
        raise TypeError(f"expected OpenAIModelConfig, got {type(config)!r}")
    return ConfiguredReviewModelGateway(
        transport=RuntimeModelGateway(provider_name="openai", handler=openai_transport),
        model=config.model,
        api_key=config.api_key,
        base_url=config.base_url,
    )


def _compose_anthropic(config: ModelProviderConfig) -> ReviewModelGateway:
    if not isinstance(config, AnthropicModelConfig):
        raise TypeError(f"expected AnthropicModelConfig, got {type(config)!r}")
    return ConfiguredReviewModelGateway(
        transport=RuntimeModelGateway(provider_name="anthropic", handler=anthropic_transport),
        model=config.model,
        api_key=config.api_key,
        base_url=config.base_url,
    )


def _compose_deepseek(config: ModelProviderConfig) -> ReviewModelGateway:
    if not isinstance(config, DeepSeekModelConfig):
        raise TypeError(f"expected DeepSeekModelConfig, got {type(config)!r}")
    return ConfiguredReviewModelGateway(
        transport=RuntimeModelGateway(provider_name="deepseek", handler=deepseek_transport),
        model=config.model,
        api_key=config.api_key,
        base_url=config.base_url,
    )


MODEL_PROVIDER_COMPOSERS: dict[type[object], ModelComposer] = {
    OpenAIModelConfig: _compose_openai,
    AnthropicModelConfig: _compose_anthropic,
    DeepSeekModelConfig: _compose_deepseek,
}


def compose_review_model(config: ModelProviderConfig) -> ReviewModelGateway:
    composer = MODEL_PROVIDER_COMPOSERS.get(type(config))
    if composer is None:
        raise TypeError(f"unsupported model config: {type(config)!r}")
    return composer(config)