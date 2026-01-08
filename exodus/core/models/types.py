from typing import TypeVar

from pydantic import BaseModel

### Generic type variable for LLM provider responses
T = TypeVar("T")

### Type variable for Pydantic-based output schemas
OutputSchemaType = TypeVar("OutputSchemaType", bound=BaseModel)
