"""Amplifier Tool: ChatGPT Images — image generation, analysis, and comparison via OpenAI."""

__amplifier_module_type__ = "tool"

import logging
from typing import Any

from .tool import GPTImageTool

__all__ = ["mount"]
__version__ = "0.1.0"

logger = logging.getLogger(__name__)


async def mount(coordinator: Any, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Mount ChatGPT Images tool."""
    config = config or {}

    # Pull session.working_dir capability from coordinator if caller didn't set it
    if "working_dir" not in config:
        working_dir = coordinator.get_capability("session.working_dir")
        if working_dir:
            config["working_dir"] = working_dir
            logger.debug("Using session.working_dir: %s", working_dir)

    # Create and register tool
    tool = GPTImageTool(config, coordinator)
    await coordinator.mount("tools", tool, name=tool.name)

    logger.info("Mounted ChatGPT Images tool (ChatGPT Images 2.0)")
    return {"name": "tool-chatgpt-images", "version": __version__, "provides": ["chatgpt_images"]}