import asyncio

from exodus.logs import logger
from exodus.settings import settings


async def main():
    """
    Main entry point for testing Exodus functionality with AgentEngine.
    """
    logger.info(f"Exodus playground...")
    logger.info("--------------------------------")
    logger.info(f"Settings: {settings.get('agent.memory.local.workspace')}")
    logger.info("--------------------------------")

def run():
    """Synchronous wrapper for entry points."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exodia stopped by user.")
    except Exception as e:
        logger.exception(f"An error occurred: {e}")

if __name__ == "__main__":
    run()
