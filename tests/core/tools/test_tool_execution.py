import pytest
import asyncio
from exodus.core.decorators import tool
from exodus.core.tools.tool_executor import ToolExecutor
from exodus.core.registries import tool_registry

# --- Fixtures ---
@pytest.fixture
def tool_executor():
    return ToolExecutor()

@pytest.fixture(autouse=True)
def clear_registry():
    # Setup: Clear registry before test to avoid conflicts
    tool_registry._tools.clear()
    yield
    # Teardown: Clear again
    tool_registry._tools.clear()

# --- Mock Tools ---

@tool(name="calculator", type="python", description="Adds two numbers")
def add(a: int, b: int) -> int:
    """Calculates sum of a and b"""
    return a + b

@tool(name="echo_cli", type="cli", description="Echoes text via CLI")
def echo_cli(text: str) -> str:
    return f"echo '{text}'"

@tool(name="async_tool", type="python", description="Async python tool")
async def async_reverse(text: str) -> str:
    await asyncio.sleep(0.01)
    return text[::-1]

class TestToolExecution:
    """TEST TOOL EXECUTION"""

    @pytest.mark.asyncio
    async def test_python_tool_execution(self, tool_executor):
        if tool_executor.execution_mode != "local":
            pytest.skip("Skipping python tool test for non-local execution mode")

        # 1. Register tool
        tool_registry.register_tool("calculator", add)
        
        # 2. Execute
        result = await tool_executor.execute("calculator", {"a": 5, "b": 3})
        
        # 3. Verify
        assert result == 8

    @pytest.mark.asyncio
    async def test_cli_tool_execution(self, tool_executor):
        # 1. Register tool
        tool_registry.register_tool("echo_cli", echo_cli)
        
        # 2. Execute
        result = await tool_executor.execute("echo_cli", {"text": "Hello World"})
        
        # 3. Verify
        assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_async_python_tool(self, tool_executor):
        if tool_executor.execution_mode != "local":
            pytest.skip("Skipping python tool test for non-local execution mode")

        tool_registry.register_tool("async_reverse", async_reverse)
        
        result = await tool_executor.execute("async_reverse", {"text": "exodia"})
        assert result == "aidoxe"

    @pytest.mark.asyncio
    async def test_missing_tool_error(self, tool_executor):
        with pytest.raises(ValueError) as excinfo:
            await tool_executor.execute("non_existent_tool", {})
        assert "not found" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_cli_error_handling(self, tool_executor):
        # Define a tool that fails
        @tool(name="fail_cli", type="cli")
        def fail_cli() -> str:
            return "ls /non_existent_directory_xyz"
            
        tool_registry.register_tool("fail_cli", fail_cli)
        
        result = await tool_executor.execute("fail_cli", {})
        # assert "Error:" in result
        # Check for common error patterns across languages (English/Spanish)
        assert any(msg in result for msg in ["No such file", "No existe", "cannot access", "no se puede acceder"])

    def test_openai_tool_schema_generation(self):
        """Test if tools correctly generate OpenAI-compatible JSON schemas"""
        
        # Register the calculator tool
        tool_registry.register_tool("calculator", add)
        
        # Verify schema attributes
        assert hasattr(add, "openai_tool_def")
        schema = add.openai_tool_def
        
        # Check top-level structure
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "calculator"
        assert schema["function"]["description"] == "Adds two numbers"
        
        # Check parameters
        parameters = schema["function"]["parameters"]
        assert parameters["type"] == "object"
        assert "a" in parameters["properties"]
        assert "b" in parameters["properties"]
        
        # Check types (mapped from python types via Pydantic)
        assert parameters["properties"]["a"]["type"] == "integer"
        assert parameters["properties"]["b"]["type"] == "integer"
        
        # Check required fields
        assert "a" in parameters["required"]
        assert "b" in parameters["required"]

    @pytest.mark.asyncio
    async def test_llm_tool_call_simulation(self, tool_executor):
        """
        Simulates an LLM response containing a tool call, 
        parses it using the dynamic Pydantic model, 
        and executes the tool.
        """
        if tool_executor.execution_mode != "local":
            pytest.skip("Skipping python tool test for non-local execution mode")

        # 1. Define and register a tool
        @tool(name="weather_tool", type="python", description="Get weather")
        def get_weather(location: str, unit: str = "celsius") -> str:
            return f"Weather in {location} is 25 {unit}"

        tool_registry.register_tool("weather_tool", get_weather)

        # 2. Simulate LLM Response (JSON string for arguments)
        llm_tool_call_args = '{"location": "Madrid", "unit": "celsius"}'
        tool_name = "weather_tool"

        # 3. Retrieve tool and its Pydantic model
        tool_func = tool_registry.get_tool(tool_name)
        assert hasattr(tool_func, "pydantic_model")
        DynamicModel = tool_func.pydantic_model

        # 4. Validate/Parse arguments using the model
        try:
            parsed_args = DynamicModel.model_validate_json(llm_tool_call_args)
            args_dict = parsed_args.model_dump()
        except Exception as e:
            pytest.fail(f"Failed to parse LLM args: {e}")

        # 5. Execute using the parsed dictionary
        result = await tool_executor.execute(tool_name, args_dict)

        # 6. Verify result
        assert result == "Weather in Madrid is 25 celsius"
