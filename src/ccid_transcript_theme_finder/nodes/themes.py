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


class ThemeTracer:
    """Simple theme tracing to track evolution through pipeline stages."""

    def __init__(self):
        self.trace_data = []
        self.theme_counter = 0

    def add_initial_themes(self, themes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Add initial themes to trace and return them with trace IDs."""
        traced_themes = []
        for theme in themes:
            trace_id = f"init_{self.theme_counter}"
            theme["trace_id"] = trace_id
            traced_themes.append(theme)
            self.theme_counter += 1
        return traced_themes

    def add_condensed_themes(self, themes: list[dict[str, Any]], iteration: int) -> list[dict[str, Any]]:
        """Add condensed themes to trace and return them with trace IDs."""
        traced_themes = []
        for theme in themes:
            trace_id = f"cond_{iteration}_{self.theme_counter}"
            theme["trace_id"] = trace_id
            traced_themes.append(theme)
            self.theme_counter += 1
        return traced_themes

    def add_refined_themes(self, themes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Add refined themes to trace and return them with trace IDs."""
        traced_themes = []
        for theme in themes:
            trace_id = f"ref_{self.theme_counter}"
            theme["trace_id"] = trace_id
            traced_themes.append(theme)
            self.theme_counter += 1
        return traced_themes

    def create_trace_csv_data(
        self, initial_themes: list[dict], condensed_themes: list[dict], refined_themes: list[dict]
    ) -> list[dict]:
        """Create CSV data showing theme evolution."""
        # Simple approach: create one row per initial theme showing its evolution
        trace_rows = []
        for i, initial_theme in enumerate(initial_themes):
            row = {
                "initial_theme": initial_theme.get("topic_label", ""),
                "initial_description": initial_theme.get("topic_description", ""),
                "initial_trace_id": initial_theme.get("trace_id", ""),
                "refined_theme": "",
                "refined_description": "",
                "refined_topic_id": "",
            }

            # Find corresponding refined theme (simplified matching)
            if i < len(refined_themes):
                refined_theme = refined_themes[i]
                row["refined_theme"] = refined_theme.get("topic_label", "")
                row["refined_description"] = refined_theme.get("topic_description", "")
                row["refined_topic_id"] = refined_theme.get("topic_id", "")

            trace_rows.append(row)

        return trace_rows


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
    topic_id_counter = 0
    for section_result in themes:
        section_id = section_result.get("section_id")
        for theme in section_result.get("themes", []):
            theme_with_section = dict(theme)
            theme_with_section["section_id"] = section_id
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
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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

    trace_data = [{"iteration": 0, "themes": themes}]
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
        trace_data.append({"iteration": iteration, "themes": current_themes})
        # update the theme count
        final_theme_count = len(current_themes)

        logger.info(f"Iteration {iteration} complete: {initial_theme_count} → {final_theme_count} themes")

        # check if the model determined no more combinations are possible
        if final_theme_count >= initial_theme_count:
            logger.info("Model determined themes are semantically fundamentally different - stopping condensation")
            break

    logger.info(f"Theme condensation complete: {len(themes)} → {len(current_themes)} themes")
    return current_themes, trace_data


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

    logger.info(f"Refined {len(condensed_themes)} themes into {len(refined_themes)} final themes")
    return refined_themes


async def create_theme_trace_data(
    initial_themes: list[dict[str, Any]],
    condensed_trace_data: list[dict[str, Any]],
    refined_themes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Create theme trace data showing evolution from initial to refined themes.

    Args:
        initial_themes: List of initial themes
        condensed_trace_data: List of trace data from condensation iterations
        refined_themes: List of refined themes

    Returns:
        List of dictionaries with theme evolution data
    """
    trace_rows = []

    # Create one row per granular topic ID, showing its evolution through all iterations
    for initial_theme in initial_themes:
        # Get the granular topic ID from source_topic_list
        source_topic_list = initial_theme.get("source_topic_list", [])
        if not source_topic_list:
            continue

        granular_topic_id = source_topic_list[0]  # Should be the only one for initial themes

        row = {
            "granular_topic_id": granular_topic_id,
            "initial_theme": initial_theme.get("topic_label", ""),
            "initial_description": initial_theme.get("topic_description", ""),
            "source_sentences": initial_theme.get("source_sentences", []),
        }

        # Add columns for each condensation iteration
        for trace_entry in condensed_trace_data:
            iteration = trace_entry.get("iteration", 0)
            themes = trace_entry.get("themes", [])

            # Find which theme in this iteration contains this granular topic ID
            iteration_theme = ""
            iteration_description = ""
            for theme in themes:
                theme_source_list = theme.get("source_topic_list", [])
                if granular_topic_id in theme_source_list:
                    iteration_theme = theme.get("topic_label", "")
                    iteration_description = theme.get("topic_description", "")
                    break

            row[f"iteration_{iteration}_theme"] = iteration_theme
            row[f"iteration_{iteration}_description"] = iteration_description

        # Find which refined theme contains this granular topic ID
        refined_theme = ""
        refined_description = ""
        refined_topic_id = ""
        for theme in refined_themes:
            theme_source_list = theme.get("source_topic_list", [])
            if granular_topic_id in theme_source_list:
                refined_theme = theme.get("topic_label", "")
                refined_description = theme.get("topic_description", "")
                refined_topic_id = theme.get("topic_id", "")
                refined_sentences = theme.get("source_sentences", [])
                break

        row["refined_theme"] = refined_theme
        row["refined_description"] = refined_description
        row["refined_topic_id"] = refined_topic_id
        row["refined_sentences"] = refined_sentences

        trace_rows.append(row)

    return trace_rows
