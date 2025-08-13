"""Theme generation functions."""

import logging
import random
from typing import Any

from ..models import (
    ThemeCondensationResponse,
    ThemeGenerationResponse,
    ThemeRefinementResponse,
)
from .deliberation_processor import TextSection
from .gemini_processor import GeminiProcessor, process_items_with_gemini

logger = logging.getLogger(__name__)

# Note:
# - The condensation inevitably puts a lot of topics in AI risks, bias, etc. which is natural given the topic.
#     + CONSIDERATION: Should we discourage this?


async def theme_generation(
    text_sections: list[TextSection],
    processor: GeminiProcessor,
    discussion_topic: str,
    concurrency: int,
) -> list[dict[str, Any]]:
    """Generate themes from text sections using native Gemini API with concurrent processing.

    The decision to mantain deliberation sections separate is to allow for small themes
    to be generated from each section, rather than have larger themes be produced from larger
    bodies of text and a smaller number of API calls. The expectation is that if these themes
    are sufficiently distinct, they may persist after condensing.

    Args:
        text_sections: List of TextSection objects to process
        processor: GeminiProcessor to use
        discussion_topic: Topic of the discussion
        concurrency: Maximum number of concurrent API calls (semaphore limit)

    Returns:
        list[dict[str, Any]]: List of generated themes

    """
    logger.info(f"Generating themes from {len(text_sections)} text sections.")

    # format text sections as items for the prompt template
    items = []
    for section in text_sections:
        items.append({
            "section_id": section.section_id,
            "content": section.content,
        })

    # process text sections through Gemini with concurrent execution
    themes = await process_items_with_gemini(
        items=items,
        prompt_template_name="theme_generation",
        response_model=ThemeGenerationResponse,
        processor=processor,
        concurrency=concurrency,
        discussion_topic=discussion_topic,
    )

    # flatten the themes list and bring section_id into each theme
    flattened_themes = []  # DAVID: reduces chances of token overflow on the call above
    for section_result in themes:
        section_id = section_result.get("section_id")
        for theme in section_result.get("themes", []):
            theme_with_section = dict(theme)
            theme_with_section["section_id"] = section_id
            flattened_themes.append(theme_with_section)

    return flattened_themes


async def theme_condensation(
    themes: list[dict[str, Any]],
    processor: GeminiProcessor,
    discussion_topic: str,
    batch_size: int,
    concurrency: int,
    max_condensation_iterations: int = 4,
) -> list[dict[str, Any]]:
    """Iteratively condense themes to remove redundancy.

    Continues until the model determines themes are semantically fundamentally different
    and no further combinations are possible.

    Args:
        themes: List of themes to condense
        processor: GeminiProcessor to use
        discussion_topic: Topic of the discussion
        batch_size: Batch size for theme condensation
        concurrency: Number of concurrent API calls
        max_condensation_iterations: Maximum number of condensation iterations (default: 10)

    Returns:
        list[dict[str, Any]]: List of condensed themes

    """
    logger.info(f"Starting iterative theme condensation with {len(themes)} themes")

    current_themes = themes
    iteration = 0

    while True:
        iteration += 1
        initial_theme_count = len(current_themes)

        # Check if we've reached the maximum iteration count
        if iteration > max_condensation_iterations:
            logger.warning(f"Reached maximum iteration count ({max_condensation_iterations}) - stopping condensation")
            break

        # shuffle themes for iteration to avoid order bias
        random.shuffle(current_themes)

        # create a batch of themes
        batched_themes = [
            {"themes": current_themes[i : i + batch_size]} for i in range(0, initial_theme_count, batch_size)
        ]

        logger.info(f"Condensation iteration {iteration}: processing {initial_theme_count} themes")

        # process themes through condensation
        condensed_themes = await process_items_with_gemini(
            items=batched_themes,
            prompt_template_name="theme_condensation",
            response_model=ThemeCondensationResponse,
            processor=processor,
            concurrency=concurrency,
            discussion_topic=discussion_topic,
        )

        # update current themes with the condensed themes
        current_themes = [theme for batch in condensed_themes for theme in batch["condensed_themes"]]

        # update the theme count
        final_theme_count = len(current_themes)

        logger.info(f"Iteration {iteration} complete: {initial_theme_count} → {final_theme_count} themes")

        # check if the model determined no more combinations are possible
        if final_theme_count >= initial_theme_count:
            logger.info("Model determined themes are semantically fundamentally different - stopping condensation")
            break

    logger.info(f"Theme condensation complete: {len(themes)} → {len(current_themes)} themes")
    return current_themes


async def theme_refinement(
    condensed_themes: list[dict[str, Any]],
    processor: GeminiProcessor,
    discussion_topic: str,
    batch_size: int,
    concurrency: int,
) -> list[dict[str, Any]]:
    """Refine and standardise condensed themes into final format.

    Args:
        condensed_themes: List of condensed themes
        processor: GeminiProcessor to use
        discussion_topic: Topic of the discussion
        batch_size: Batch size for theme refinement
        concurrency: Number of concurrent API calls

    Returns:
        list[dict[str, Any]]: List of refined themes

    """
    themes_to_refine = [
        {"themes": condensed_themes[i : i + batch_size]} for i in range(0, len(condensed_themes), batch_size)
    ]
    logger.info(f"Refining {len(condensed_themes)} condensed themes")

    # process themes through refinement
    refined_themes = await process_items_with_gemini(
        items=themes_to_refine,
        prompt_template_name="theme_refinement",
        response_model=ThemeRefinementResponse,
        processor=processor,
        concurrency=concurrency,
        discussion_topic=discussion_topic,
        batch_size=batch_size,
    )

    # flatten
    refined_themes = [theme for batch in refined_themes for theme in batch["refined_themes"]]

    # create topic_id for each refined theme (batches each have A-K)
    for i, theme in enumerate(refined_themes):
        theme["topic_id"] = f"t{i}"

    logger.info(f"Refined {len(condensed_themes)} themes into {len(refined_themes)} final themes")
    return refined_themes
