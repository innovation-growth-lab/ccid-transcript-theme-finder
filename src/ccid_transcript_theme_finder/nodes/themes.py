"""Theme generation functions."""

import logging
from typing import Any

from ..models import (
    ThemeGenerationResponse,
    ThemeRefinementResponse,
)
from .bootstrap_condensation import BootstrapCondenser
from .context_loader import get_section_context, load_section_context
from .deliberation_processor import TextSection
from .gemini_processor import GeminiProcessor, process_items_with_gemini
from .tracer import ThemeTracer

logger = logging.getLogger(__name__)


async def theme_generation(
    text_sections: list[TextSection],
    processor: GeminiProcessor,
    discussion_topic: str,
    concurrency: int,
    context_file_path: str | None = None,
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
        context_file_path: Optional path to Excel file with section context

    Returns:
        list[dict[str, Any]]: List of generated themes

    """
    logger.info(f"Generating themes from {len(text_sections)} text sections.")

    # load section context if provided
    context_dict = {}
    if context_file_path:
        context_dict = load_section_context(context_file_path)

    # format text sections as items for the prompt template
    items = []
    for section in text_sections:
        # get context for this section
        section_context = get_section_context(section.section_id, context_dict)

        items.append({
            "section_id": section.section_id,
            "content": section.content,
            "stimulus": section_context.get("stimulus", ""),
            "core_question": section_context.get("core_question", ""),
            "facilitator_prompts": section_context.get("facilitator_prompts", ""),
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
    topic_id_counter = 0

    for i, section_result in enumerate(themes):
        section_id = section_result.get("section_id")
        session_id = text_sections[i].session_id
        for theme in section_result.get("themes", []):
            theme_with_section = dict(theme)
            theme_with_section["section_id"] = section_id
            theme_with_section["session_id"] = session_id
            theme_with_section["source_topic_list"] = [f"t{topic_id_counter}"]
            topic_id_counter += 1
            flattened_themes.append(theme_with_section)

    return flattened_themes


async def theme_condensation(
    themes: list[dict[str, Any]],
    processor: GeminiProcessor,
    discussion_topic: str,
    batch_size: int,
    concurrency: int,
    max_condensation_iterations: int = 4,
    context_file_path: str | None = None,
    tracer: ThemeTracer | None = None,
    n_bootstrap_samples: int = 10,
) -> list[dict[str, Any]]:
    """Condense themes using bootstrap sampling and network clustering.

    Uses multiple bootstrap samples with different shuffles to build a co-occurrence
    network, then applies Louvain clustering for robust theme condensation.

    Args:
        themes: List of themes to condense
        processor: GeminiProcessor to use
        discussion_topic: Topic of the discussion
        batch_size: Batch size for theme condensation
        concurrency: Number of concurrent API calls
        max_condensation_iterations: Maximum number of condensation iterations (unused in bootstrap mode)
        context_file_path: Optional path to Excel file with section context
        tracer: Optional ThemeTracer to record theme evolution
        n_bootstrap_samples: Number of bootstrap samples to generate

    Returns:
        list[dict[str, Any]]: List of condensed themes

    """
    logger.info(f"Starting bootstrap theme condensation with {len(themes)} themes")

    # record initial themes in tracer if provided
    if tracer:
        tracer.record_initial_themes(themes)

    # Create bootstrap condenser
    condenser = BootstrapCondenser(
        processor=processor,
        discussion_topic=discussion_topic,
        batch_size=batch_size,
        concurrency=concurrency,
        n_bootstrap_samples=n_bootstrap_samples,
        context_file_path=context_file_path,
    )

    # Perform bootstrap condensation
    condensed_themes = await condenser.condense_themes(themes)

    # record condensed themes in tracer if provided
    if tracer:
        tracer.record_condensation_iteration(1, condensed_themes)

    logger.info(f"Bootstrap theme condensation complete: {len(themes)} → {len(condensed_themes)} themes")
    return condensed_themes


async def theme_refinement(
    condensed_themes: list[dict[str, Any]],
    processor: GeminiProcessor,
    discussion_topic: str,
    batch_size: int,
    concurrency: int,
    context_file_path: str | None = None,
    tracer: ThemeTracer | None = None,
) -> list[dict[str, Any]]:
    """Refine and standardise condensed themes into final format.

    Args:
        condensed_themes: List of condensed themes
        processor: GeminiProcessor to use
        discussion_topic: Topic of the discussion
        batch_size: Batch size for theme refinement
        concurrency: Number of concurrent API calls
        context_file_path: Optional path to Excel file with section context
        tracer: Optional ThemeTracer to record theme evolution

    Returns:
        list[dict[str, Any]]: List of refined themes

    """
    # load section context if provided
    context_dict = {}
    if context_file_path:
        context_dict = load_section_context(context_file_path)

    # create batches of themes with context
    themes_to_refine = []
    for i in range(0, len(condensed_themes), batch_size):
        theme_batch = condensed_themes[i : i + batch_size]
        # get context for this batch (use first theme's section_id as representative)
        batch_context = {"stimulus": "", "core_question": "", "facilitator_prompts": ""}
        if context_dict and theme_batch:
            section_context = get_section_context(theme_batch[0].get("section_id", ""), context_dict)
            batch_context = {
                "stimulus": section_context.get("stimulus", ""),
                "core_question": section_context.get("core_question", ""),
                "facilitator_prompts": section_context.get("facilitator_prompts", ""),
            }
        themes_to_refine.append({"themes": theme_batch, **batch_context})
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

    # flatten the refined themes list
    refined_themes = [theme for batch in refined_themes for theme in batch["refined_themes"]]

    # assign topic_id manually to each refined theme
    for i, theme in enumerate(refined_themes):
        # Convert to uppercase letter format (A, B, C, ..., Z, AA, AB, etc.)
        if i < 26:
            topic_id = chr(ord("A") + i)
        else:
            # For themes beyond Z, use AA, AB, AC, etc.
            first_letter = chr(ord("A") + (i - 26) // 26)
            second_letter = chr(ord("A") + (i - 26) % 26)
            topic_id = first_letter + second_letter

        theme["topic_id"] = topic_id
        # ensure source_topic_list exists for tracking
        if "source_topic_list" not in theme:
            theme["source_topic_list"] = []

    # record refined themes in tracer if provided
    if tracer:
        tracer.record_refined_themes(refined_themes)

    logger.info(f"Refined {len(condensed_themes)} themes into {len(refined_themes)} final themes")
    return refined_themes
