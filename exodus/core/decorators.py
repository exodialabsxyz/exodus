import asyncio
import functools
import inspect
from typing import Any, get_type_hints

from pydantic import Field, create_model


def tool(name=None, type="cli", description=None):
    def decorator(func):
        func.tool_name = name or func.__name__
        func.tool_type = type
        func.tool_description = description or func.__doc__ or "No description provided"

        ####### Scheme building for the openai schema #######

        ### Scheme creation for the tool
        type_hints = get_type_hints(func, include_extras=True)
        signature = inspect.signature(func)

        fields = {}

        for param_name, param in signature.parameters.items():
            if param_name in ("self", "cls"):
                continue

            annotation = type_hints.get(param_name, Any)
            default_value = param.default

            if default_value == inspect.Parameter.empty:
                pydantic_field = Field(...)
            else:
                pydantic_field = Field(default=default_value)

            fields[param_name] = (annotation, pydantic_field)

        dynamic_model = create_model(f"{func.tool_name}Args", **fields)

        schema = dynamic_model.model_json_schema()
        openai_parameters = {
            "type": "object",
            "properties": schema.get("properties", {}),
            "required": schema.get("required", []),
        }

        openai_tool_def = {
            "type": "function",
            "function": {
                "name": func.tool_name,
                "description": func.tool_description.strip(),
                "parameters": openai_parameters,
            },
        }

        ####### End of scheme building for the openai schema #######

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
        else:

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

        wrapper.tool_name = func.tool_name
        wrapper.tool_type = func.tool_type
        wrapper.tool_description = func.tool_description
        wrapper.openai_tool_def = openai_tool_def
        wrapper.pydantic_model = dynamic_model

        return wrapper

    return decorator
