import logging

from exodus.settings import settings


### TMP: Filter to suppress aiohttp unclosed session warnings from LiteLLM's internal sessions
### See: https://github.com/BerriAI/litellm/issues/12443
class AiohttpWarningFilter(logging.Filter):
    """Filter out known aiohttp unclosed session warnings from LiteLLM."""

    def filter(self, record):
        msg = record.getMessage()
        # Suppress these specific error messages from asyncio logger
        if record.name == "asyncio" and record.levelno == logging.ERROR:
            if "Unclosed client session" in msg or "Unclosed connector" in msg:
                return False
        return True


logging.basicConfig(
    level=settings.get("logging.level", logging.INFO),
    format=settings.get(
        "logging.format", "[exodus] %(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ),
)

# Apply the filter to all root logger handlers
for handler in logging.root.handlers:
    handler.addFilter(AiohttpWarningFilter())

logger = logging.getLogger(__name__)
