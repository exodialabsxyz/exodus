from typing import Any, AsyncIterator, Dict, List, Optional, Union

import litellm
from litellm.types.utils import ModelResponse

from exodus.core.models.llm import LLMConfig, LLMProvider, LLMProviderResponse
from exodus.core.models.memory import Message


class LitellmProviderResponse(LLMProviderResponse):
    def __init__(self, response: ModelResponse):
        super().__init__(response)

    def get_content(self) -> Optional[str]:
        if self.response.choices[0].message.content is not None:
            return self.response.choices[0].message.content
        else:
            return None

    def is_tool_call(self) -> bool:
        return self.response.choices[0].message.tool_calls is not None

    def get_tool_calls(self) -> Dict[str, Any]:
        return self.response.choices[0].message.tool_calls


class LitellmProvider(LLMProvider[ModelResponse]):
    def __init__(self, config: LLMConfig):
        super().__init__(config)

    def _build_completion_args(
        self,
        messages: List[Union[Message, Dict[str, Any]]],
        tools_schema: Optional[List[Dict[str, Any]]] = [],
        **kwargs,
    ) -> Dict[str, Any]:
        """Build completion arguments for litellm."""
        # Convert messages to OpenAI format if they aren't already dicts
        messages_dict = [
            message.to_openai_format() if isinstance(message, Message) else message
            for message in messages
        ]

        completion_args = {
            "model": self.config.model,
            "messages": messages_dict,
            "api_key": self.config.api_key,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        # Only add tools if they are provided and not empty
        if tools_schema and len(tools_schema) > 0:
            completion_args["tools"] = tools_schema

        if self.config.custom_api_base is not None:
            completion_args["api_base"] = self.config.custom_api_base

        completion_args.update(kwargs)
        # Remove None values
        return {k: v for k, v in completion_args.items() if v is not None}

    async def generate(
        self,
        messages: List[Union[Message, Dict[str, Any]]],
        tools_schema: Optional[List[Dict[str, Any]]] = [],
        **kwargs,
    ) -> LitellmProviderResponse:
        completion_args = self._build_completion_args(messages, tools_schema, **kwargs)
        response = await litellm.acompletion(**completion_args)
        return LitellmProviderResponse(response)

    async def generate_stream(
        self,
        messages: List[Union[Message, Dict[str, Any]]],
        tools_schema: Optional[List[Dict[str, Any]]] = [],
        **kwargs,
    ) -> AsyncIterator[Any]:
        completion_args = self._build_completion_args(messages, tools_schema, **kwargs)
        completion_args["stream"] = True

        ### In LiteLLM, awaiting acompletion with stream=True returns the generator
        response = await litellm.acompletion(**completion_args)
        async for chunk in response:
            yield chunk

    def rebuild_response(self, chunks: List[Any]) -> LitellmProviderResponse:
        """Rebuild a complete response from chunks using litellm helper."""
        full_response = litellm.stream_chunk_builder(chunks, messages=None)
        return LitellmProviderResponse(full_response)
