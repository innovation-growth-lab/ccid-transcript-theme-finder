"""Sentiment analysis functions for theme sentences."""

import logging
from typing import Any

from ..models import ThemeSentiment
from .gemini_processor import GeminiProcessor, process_items_with_gemini

logger = logging.getLogger(__name__)


async def theme_sentiment_analysis(
    refined_themes: list[dict[str, Any]],
    processor: GeminiProcessor,
    discussion_topic: str,
    batch_size: int,
    concurrency: int,
) -> list[dict[str, Any]]:
    """Check for position and stance of sentences within each refined theme.

    This function checks each sentence in each refined theme to determine:
    1. Position: agreement, disagreement, or unclear (default)
    2. Stance: positive, negative, or unclear (default)
    3. Reasoning for the classifications

    Args:
        refined_themes: List of refined themes with source sentences
        processor: GeminiProcessor to use
        discussion_topic: Topic of the discussion
        batch_size: Batch size for sentiment analysis
        concurrency: Number of concurrent API calls

    Returns:
        list[dict[str, Any]]: List of theme sentiment analyses

    """
    logger.info(f"Starting position & stance analysis for {len(refined_themes)} refined themes")

    # preprocess the refined themes
    refined_themes = [{"theme": theme} for theme in refined_themes]

    # process themes through sentiment analysis
    sentiment_analyses = await process_items_with_gemini(
        items=refined_themes,
        prompt_template_name="theme_sentiment",
        response_model=ThemeSentiment,
        processor=processor,
        concurrency=concurrency,
        discussion_topic=discussion_topic,
        batch_size=batch_size,
    )

    logger.info(f"Completed sentiment analysis for {len(sentiment_analyses)} themes")
    return sentiment_analyses
