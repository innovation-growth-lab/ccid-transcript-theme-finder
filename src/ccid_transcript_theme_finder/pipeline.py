"""Core pipeline for focus group session analysis using native Gemini APIs.

This module provides the main analysis pipeline that orchestrates the entire
theme finding process.
"""

import logging
from typing import Any

from .nodes.deliberation_processor import DeliberationProcessor
from .nodes.gemini_processor import GeminiProcessor
from .nodes.sentence_mapper import SentenceMapper
from .nodes.sentiment import theme_sentiment_analysis
from .nodes.themes import theme_condensation, theme_generation, theme_refinement

logger = logging.getLogger(__name__)


async def analyse_deliberation_session(
    data_path: str,
    model_name: str = "gemini-2.5-flash",  # "gemini-2.5-flash-lite",
    batch_size: int = 10,
    concurrency: int = 4,
    max_condensation_iterations: int = 2,
    remove_facilitator_content: bool = False,
    target_section: str | None = None,
    remove_short_sentences: bool = False,
) -> dict[str, Any]:
    """Analyse a transcript session from a folder of JSON files to identify and map themes using Gemini API calls.

    This is the main pipeline function that processes a folder of transcript sessions through
    multiple stages: session processing, theme generation, iterative condensation,
    refinement, and text section mapping.

    Two processing modes are supported:
    1. Session mode: Process all sections within a single deliberation session
    2. Cross-session mode: Process a specific section across all deliberation sessions on a given date

    Args:
        data_path: Path to folder containing JSON files with transcript data for deliberation sections
                   OR path to root folder containing date folders when using cross-session mode
        model_name: Gemini model to use (default: "gemini-2.5-flash-lite")
        batch_size: Batch size for theme condensation, refinement and mapping (default: 10)
        concurrency: Number of concurrent API calls (default: 4)
        max_condensation_iterations: Maximum number of condensation iterations (default: 4)
        remove_facilitator_content: Whether to remove facilitator content (default: False)
        target_section: Specific section to analyze across sessions (e.g., "groundwork-intro").
                       If provided, enables cross-session mode. If None, uses session mode.
        remove_short_sentences: Whether to remove short sentences from the transcript (default: False)

    Returns:
        dict: Results from each pipeline stage, structured as:
            {
                "session": TranscriptSession,
                "text_sections": list[TextSection],
                "initial_themes": list[dict],
                "condensed_themes": list[dict],
                "refined_themes": list[dict],
                "sentence_theme_mapping": list[dict],
                "sentiment_analyses": list[dict],
            }

    """
    logger.info("Starting focus group session analysis with native Gemini")

    # init the gemini and session processor
    processor = GeminiProcessor(model_name=model_name)
    deliberation_processor = DeliberationProcessor(processor=processor if remove_facilitator_content else None)

    # stage 1: process the session folder or specific section across sessions
    if target_section:
        logger.info(f"Stage 1: Processing {target_section} across sessions in root folder")
        corpus, text_sections = await deliberation_processor.process_specific_section_across_sessions(
            data_path, target_section, remove_short_sentences=remove_short_sentences
        )
    else:
        logger.info("Stage 1: Processing session folder from JSON files")
        corpus, text_sections = await deliberation_processor.process_session_folder(
            data_path, remove_short_sentences=remove_short_sentences
        )

    logger.info(f"Created {len(text_sections)} text sections from session folder {corpus.session_id}")

    # stage 2: generate initial themes from text sections
    logger.info("Stage 2: Generating themes from text sections")
    initial_themes = await theme_generation(
        text_sections=text_sections,
        processor=processor,
        discussion_topic=corpus.system_info,
        concurrency=concurrency,
    )

    logger.info(f"Generated {len(initial_themes)} initial themes")

    # stage 3: iteratively condense themes
    logger.info("Stage 3: Condensing themes iteratively")
    condensed_themes = await theme_condensation(
        themes=initial_themes,
        processor=processor,
        discussion_topic=corpus.system_info,
        batch_size=batch_size,
        concurrency=concurrency,
        max_condensation_iterations=max_condensation_iterations,
    )

    logger.info(f"Condensed to {len(condensed_themes)} themes")

    # stage 4: refine themes
    logger.info("Stage 4: Refining themes")
    refined_themes = await theme_refinement(
        condensed_themes=condensed_themes,
        processor=processor,
        discussion_topic=corpus.system_info,
        batch_size=batch_size,
        concurrency=concurrency,
    )

    logger.info(f"Refined to {len(refined_themes)} final themes")

    # stage 5: create sentence-level theme mapping
    logger.info("Stage 5: Creating sentence-level theme mapping")
    sentence_mapper = SentenceMapper()
    sentence_mapping = sentence_mapper.create_sentence_theme_mapping(
        text_sections=text_sections,
        initial_themes=initial_themes,
        condensed_themes=condensed_themes,
        refined_themes=refined_themes,
    )

    # stage 6: analyse position and stance of sentences within each theme
    logger.info("Stage 6: Analysing position and stance of sentences within themes")
    sentiment_analyses = await theme_sentiment_analysis(
        refined_themes=refined_themes,
        processor=processor,
        discussion_topic=corpus.system_info,
        batch_size=batch_size,
        concurrency=concurrency,
    )

    logger.info("Deliberation analysis complete")

    return {
        "combined_transcript": corpus,
        "text_sections": text_sections,
        "initial_themes": initial_themes,
        "condensed_themes": condensed_themes,
        "refined_themes": refined_themes,
        "sentence_theme_mapping": sentence_mapping,
        "sentiment_analyses": sentiment_analyses,
    }
