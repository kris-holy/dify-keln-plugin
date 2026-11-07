import re
from collections.abc import Generator
from typing import Optional, Union

import requests
from dify_plugin import OAICompatLargeLanguageModel
from dify_plugin.entities import I18nObject
from dify_plugin.entities.model import AIModelEntity, DefaultParameterName, ModelFeature, ParameterRule, ParameterType
from dify_plugin.entities.model.llm import LLMMode, LLMResult
from dify_plugin.entities.model.message import PromptMessage, PromptMessageTool

KELN_API_BASE = "https://api.keln.ai/v1"
DEFAULT_MAX_TOKENS = 8192
REASONING_EFFORTS = ["none", "low", "medium", "high", "max"]
TOOL_FEATURES = {ModelFeature.TOOL_CALL, ModelFeature.MULTI_TOOL_CALL, ModelFeature.STREAM_TOOL_CALL}

# The SDK wraps a streamed reasoning trace as "<think>\n...\n</think>" at the start of the content.
THINK_BLOCK = re.compile(r"^<think>\n(.*?)\n</think>", re.DOTALL)


class KelnLargeLanguageModel(OAICompatLargeLanguageModel):
    """Keln chat models over the OpenAI-compatible Chat Completions API."""

    def _invoke(
        self,
        model: str,
        credentials: dict,
        prompt_messages: list[PromptMessage],
        model_parameters: dict,
        tools: Optional[list[PromptMessageTool]] = None,
        stop: Optional[list[str]] = None,
        stream: bool = True,
        user: Optional[str] = None,
    ) -> Union[LLMResult, Generator]:
        parameters = dict(model_parameters)
        if stream:
            parameters["stream_options"] = {"include_usage": True}
        # The Dify end-user ID is not forwarded (user=None).
        return super()._invoke(
            model, self._prepare_credentials(model, credentials), prompt_messages, parameters, tools, stop, stream, None
        )

    def validate_credentials(self, model: str, credentials: dict) -> None:
        super().validate_credentials(model, self._prepare_credentials(model, credentials))

    def get_num_tokens(
        self,
        model: str,
        credentials: dict,
        prompt_messages: list[PromptMessage],
        tools: Optional[list[PromptMessageTool]] = None,
    ) -> int:
        return super().get_num_tokens(model, self._prepare_credentials(model, credentials), prompt_messages, tools)

    def get_customizable_model_schema(self, model: str, credentials: dict) -> AIModelEntity:
        credentials = dict(credentials)
        credentials["mode"] = LLMMode.CHAT.value
        credentials.setdefault("function_calling_type", "tool_call")
        entity = super().get_customizable_model_schema(model, credentials)
        if credentials["function_calling_type"] == "tool_call":
            for feature in (ModelFeature.TOOL_CALL, ModelFeature.AGENT_THOUGHT):
                if feature not in entity.features:
                    entity.features.append(feature)
        else:
            entity.features = [feature for feature in entity.features if feature not in TOOL_FEATURES]
        for rule in entity.parameter_rules:
            # max_tokens covers reasoning and answer, so the SDK default of 512 can leave no room for the answer.
            if rule.name == DefaultParameterName.MAX_TOKENS.value:
                rule.default = min(DEFAULT_MAX_TOKENS, rule.max) if rule.max else DEFAULT_MAX_TOKENS
        entity.parameter_rules.append(
            ParameterRule(
                name="reasoning_effort",
                label=I18nObject(en_US="Reasoning effort"),
                help=I18nObject(
                    en_US="How much the model reasons before answering. Keln runs the deepest level of the model "
                    "when this is unset. none turns reasoning off where the model allows it."
                ),
                type=ParameterType.STRING,
                required=False,
                options=REASONING_EFFORTS,
            )
        )
        return entity

    def _convert_prompt_message_to_dict(self, message: PromptMessage, credentials: Optional[dict] = None) -> dict:
        message_dict = super()._convert_prompt_message_to_dict(message, credentials)
        # Keln asks for the trace back in reasoning_content when history includes tool calls.
        if message_dict.get("role") == "assistant" and isinstance(message_dict.get("content"), str):
            match = THINK_BLOCK.match(message_dict["content"])
            if match:
                message_dict["reasoning_content"] = match.group(1)
                message_dict["content"] = message_dict["content"][match.end() :]
        return message_dict

    def _handle_generate_response(
        self,
        model: str,
        credentials: dict,
        response: requests.Response,
        prompt_messages: list[PromptMessage],
    ) -> LLMResult:
        # A blocking tool-call reply has content: null, and the Dify plugin daemon rejects a message without content.
        body = response.json()
        for choice in body.get("choices", []):
            message = choice.get("message")
            if message is not None and message.get("content") is None:
                message["content"] = ""
        response.json = lambda **_: body
        return super()._handle_generate_response(model, credentials, response, prompt_messages)

    def _prepare_credentials(self, model: str, credentials: dict) -> dict:
        prepared = dict(credentials)
        prepared["endpoint_url"] = KELN_API_BASE
        prepared["mode"] = LLMMode.CHAT.value
        if "function_calling_type" not in prepared:
            schema = next((item for item in self.predefined_models() if item.model == model), None)
            if schema is None or TOOL_FEATURES.intersection(schema.features or []):
                prepared["function_calling_type"] = "tool_call"
        return prepared
