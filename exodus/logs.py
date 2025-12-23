import logging

from exodus.settings import settings

logging.basicConfig(
    level=settings.get("logging.level", logging.INFO),
    format=settings.get(
        "logging.format", "[exodus] %(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ),
)

logger = logging.getLogger(__name__)
