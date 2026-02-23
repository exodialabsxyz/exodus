from typing import Any, AsyncIterator, Dict, List, Optional, Union

import aiohttp
import litellm
from litellm.llms.custom_httpx.aiohttp_handler import BaseLLMAIOHTTPHandler
from litellm.types.utils import ModelResponse

from exodus.core.models.llm import LLMConfig, LLMProvider, LLMProviderResponse
from exodus.core.models.memory import Message
from exodus.core.models.types import OutputSchemaType


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

        self._custom_session_handler = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=300),
            connector=aiohttp.TCPConnector(limit=1000, limit_per_host=200, keepalive_timeout=60),
        )

        litellm.base_llm_aiohttp_handler = BaseLLMAIOHTTPHandler(
            client_session=self._custom_session_handler
        )

    def _build_completion_args(
        self,
        messages: List[Union[Message, Dict[str, Any]]],
        tools_schema: Optional[List[Dict[str, Any]]] = [],
        output_schema: Optional[OutputSchemaType] = None,
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

        # Add response format if output_schema is provided
        if output_schema is not None:
            completion_args["response_format"] = output_schema

        if self.config.custom_api_base is not None:
            completion_args["api_base"] = self.config.custom_api_base

        completion_args.update(kwargs)
        # Remove None values
        return {k: v for k, v in completion_args.items() if v is not None}

    async def generate(
        self,
        messages: List[Union[Message, Dict[str, Any]]],
        tools_schema: Optional[List[Dict[str, Any]]] = [],
        output_schema: Optional[OutputSchemaType] = None,
        **kwargs,
    ) -> LitellmProviderResponse:
        completion_args = self._build_completion_args(
            messages, tools_schema, output_schema, **kwargs
        )
        response = await litellm.acompletion(**completion_args)
        return LitellmProviderResponse(response)

    async def generate_stream(
        self,
        messages: List[Union[Message, Dict[str, Any]]],
        tools_schema: Optional[List[Dict[str, Any]]] = [],
        output_schema: Optional[OutputSchemaType] = None,
        **kwargs,
    ) -> AsyncIterator[Any]:
        completion_args = self._build_completion_args(
            messages, tools_schema, output_schema, **kwargs
        )
        completion_args["stream"] = True

        ### In LiteLLM, awaiting acompletion with stream=True returns the generator
        response = await litellm.acompletion(**completion_args)
        async for chunk in response:
            yield chunk

    def rebuild_response(self, chunks: List[Any]) -> LitellmProviderResponse:
        """Rebuild a complete response from chunks using litellm helper."""
        full_response = litellm.stream_chunk_builder(chunks, messages=None)
        return LitellmProviderResponse(full_response)

    def count_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Counts the number of tokens in the given messages using litellm."""
        return litellm.token_counter(model=self.config.model, messages=messages)

    async def close(self):
        """Closes the LLM provider."""
        if hasattr(self, "_custom_session_handler"):
            await self._custom_session_handler.close()
