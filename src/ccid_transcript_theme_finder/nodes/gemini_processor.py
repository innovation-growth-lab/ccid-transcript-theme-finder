"""Gemini API processor for the theme-finder package.

This module provides functionality to process transcript chunks through
Gemini models with structured outputs.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from google import genai
from google.genai.client import Client
from pydantic import BaseModel

from .decorators import async_retry

logger = logging.getLogger(__name__)


class GeminiProcessor:
    """Direct Gemini API processor with retry logic and structured outputs."""

    def __init__(self, model_name: str = "gemini-2.5-flash-lite") -> None:
        """Init the Gemini processor.

        Args:
            model_name: Gemini model to use

        """
        self.client: Client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_name = model_name

    @async_retry()
    async def generate(self, prompt: str, response_model: type[BaseModel]) -> BaseModel:
        """Generate content with structured output validation.

        Args:
            prompt: The prompt to send to Gemini
            response_model: Pydantic model for response validation

        Returns:
            BaseModel: Response as Pydantic model instance

        """
        # get the model schema for structured output guidance
        model_schema = response_model.model_json_schema()

        # create generation config for structured JSON output
        generation_config = {
            "response_mime_type": "application/json",
            "temperature": 0.3,
            "response_schema": model_schema,
        }

        response = await self.client.aio.models.generate_content(
            model=self.model_name, contents=prompt, config=generation_config
        )

        if not response.text:
            raise ValueError("Empty response from Gemini")

        # Parse and validate JSON
        try:
            response_data = json.loads(response.text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in response: {e}\nResponse: {response.text[:500]}") from e

        # Validate with Pydantic model
        return response_model(**response_data)


def load_prompt_template(template_name: str) -> str:
    """Load a prompt template from the prompts directory."""
    prompts_dir = Path(__file__).parent.parent / "prompts"
    template_path = prompts_dir / f"{template_name}.txt"

    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")

    return template_path.read_text()


async def process_items_with_gemini(
    items: list[dict[str, Any]],
    prompt_template_name: str,
    response_model: type[BaseModel],
    processor: GeminiProcessor,
    concurrency: int = 8,
    **template_kwargs: Any,
) -> list[dict[str, Any]]:
    """Process chunks through Gemini with concurrent execution.

    Args:
        items: List of items to process
        prompt_template_name: Name of the prompt template file (without .txt)
        response_model: Pydantic model for response validation
        processor: GeminiProcessor instance
        concurrency: Maximum concurrent requests
        **template_kwargs: Additional arguments for prompt template

    Returns:
        pd.DataFrame: DataFrame with processed results

    """
    logger.info(f"Starting processing of {len(items)} items with Gemini")

    # load prompt template
    prompt_template = load_prompt_template(prompt_template_name)
    semaphore = asyncio.Semaphore(concurrency)

    async def process_item(item: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            # format prompt with item data and template kwargs
            prompt = prompt_template.format(**item, **template_kwargs)
            result = await processor.generate(prompt, response_model)
            return result.model_dump()

    # Process all chunks concurrently
    tasks = [process_item(item) for item in items]
    return await asyncio.gather(*tasks)
