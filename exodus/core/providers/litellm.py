import litellm
from litellm.types.utils import ModelResponse
from typing import List, AsyncIterator, Dict, Any, Optional, Union

from exodus.core.models.llm import LLMProvider, LLMProviderResponse, LLMConfig
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

    async def generate(self, messages: List[Union[Message, Dict[str, Any]]], tools_schema: Optional[List[Dict[str, Any]]] = [], **kwargs) -> LitellmProviderResponse:
        
        # Convert messages to OpenAI format if they aren't already dicts
        messages_dict = [message.to_openai_format() if isinstance(message, Message) else message for message in messages]
            
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
        completion_args = {k: v for k, v in completion_args.items() if v is not None}
        response = await litellm.acompletion(**completion_args)
        return LitellmProviderResponse(response)   
    async def generate_stream(self, messages: List[Message], **kwargs):
        pass
