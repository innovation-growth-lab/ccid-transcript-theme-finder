"""Sentence mapping functionality for theme analysis pipeline."""

import logging
import re
from typing import Any, Set

from .session_processor import TextSection

logger = logging.getLogger(__name__)


class SentenceMapper:
    """Handles sentence-level mapping to themes across pipeline stages."""

    def __init__(self) -> None:
        """Init the sentence mapper."""
        self.all_original_sentences: Set[str] = set()
        self.assigned_sentences: Set[str] = set()

    def extract_sentences_from_text_sections(self, text_sections: list[TextSection]) -> Set[str]:
        """Extract all unique sentences from text sections.

        Args:
            text_sections: List of TextSection objects containing original text

        Returns:
            Set of unique sentences

        """
        sentences = set()

        # pattern to match sentences, keeping the punctuation at the end
        sentence_pattern = re.compile(r"[^.!?]*[.!?]")

        for section in text_sections:
            # find all sentences ending with ., !, or ?
            section_sentences = sentence_pattern.findall(section.content)
            for sentence in section_sentences:
                sentence = sentence.strip()
                if sentence:  # only add non-empty sentences (i.e. not empty lines)
                    sentences.add(sentence)

        logger.info(f"Extracted {len(sentences)} unique sentences from text sections")
        return sentences

    def collect_assigned_sentences(
        self,
        initial_themes: list[dict[str, Any]],
        condensed_themes: list[dict[str, Any]],
        refined_themes: list[dict[str, Any]],
    ) -> Set[str]:
        """Collect all sentences that were assigned to themes across all stages.

        Args:
            initial_themes: List of initial themes from theme generation
            condensed_themes: List of condensed themes from theme condensation
            refined_themes: List of refined themes from theme refinement

        Returns:
            Set of sentences that were assigned to themes

        """
        assigned_sentences = set()

        # extract sentences from initial themes
        for theme in initial_themes:
            if "source_sentences" in theme:
                assigned_sentences.update(theme["source_sentences"])

        return assigned_sentences

    def find_themes_for_sentence(
        self, sentence: str, themes: list[dict[str, Any]], theme_type: str
    ) -> list[dict[str, Any]] | None:
        """Find themes containing a specific sentence.

        Args:
            sentence: The sentence to search for
            themes: List of themes to search in
            theme_type: Type of themes ('initial', 'condensed', or 'refined')

        Returns:
            List of themes containing the sentence

        """
        matching_themes: list[dict[str, Any]] = []

        for theme in themes:
            # handle initial themes which have nested structure
            if theme_type == "initial" and "themes" in theme:
                for sub_theme in theme["themes"]:
                    if "source_sentences" in sub_theme and sentence in sub_theme["source_sentences"]:
                        clean_theme = {
                            "topic_label": sub_theme.get("topic_label", ""),
                            "topic_description": sub_theme.get("topic_description", ""),
                        }
                        matching_themes.append(clean_theme)
            # handle condensed and refined themes which have direct structure
            elif "source_sentences" in theme and sentence in theme["source_sentences"]:
                clean_theme = {
                    "topic_label": theme.get("topic_label", ""),
                    "topic_description": theme.get("topic_description", ""),
                }

                # add theme-specific fields
                if theme_type == "condensed":
                    clean_theme["source_session_count"] = theme.get("source_session_count", 0)
                elif theme_type == "refined":
                    clean_theme["topic_id"] = theme.get("topic_id", "")
                    clean_theme["source_session_count"] = theme.get("source_session_count", 0)

                matching_themes.append(clean_theme)

        return matching_themes

    def create_sentence_mapping(
        self,
        sentence: str,
        initial_themes: list[dict[str, Any]],
        condensed_themes: list[dict[str, Any]],
        refined_themes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create mapping for a single sentence.

        Args:
            sentence: The sentence to map
            initial_themes: List of initial themes
            condensed_themes: List of condensed themes
            refined_themes: List of refined themes

        Returns:
            Dictionary containing sentence mapping

        """
        if sentence in self.assigned_sentences:
            sentence_mapping = {"sentence": sentence, "topics": {"initial": [], "condensed": [], "refined": []}}

            # find themes for each stage
            sentence_mapping["topics"]["initial"] = self.find_themes_for_sentence(sentence, initial_themes, "initial")
            sentence_mapping["topics"]["condensed"] = self.find_themes_for_sentence(
                sentence, condensed_themes, "condensed"
            )
            sentence_mapping["topics"]["refined"] = self.find_themes_for_sentence(sentence, refined_themes, "refined")
        else:
            # sentence was never assigned to any theme
            sentence_mapping = {"sentence": sentence, "topics": None}

        return sentence_mapping

    def create_sentence_theme_mapping(
        self,
        text_sections: list[TextSection],
        initial_themes: list[dict[str, Any]],
        condensed_themes: list[dict[str, Any]],
        refined_themes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Create sentence-level mapping to themes across all pipeline stages.

        This function leverages the source_sentences tracked throughout the pipeline
        to create a mapping of each sentence to its corresponding themes at each stage.
        Sentences that were never assigned to any theme will have topics: None.

        Args:
            text_sections: List of TextSection objects containing all original sentences
            initial_themes: List of initial themes from theme generation
            condensed_themes: List of condensed themes from theme condensation
            refined_themes: List of refined themes from theme refinement

        Returns:
            list[dict[str, Any]]: List of sentence mappings with structure:
                {
                    "sentence": str,
                    "topics": {
                        "initial": list[dict],  # List of initial themes containing this sentence
                        "condensed": list[dict], # List of condensed themes containing this sentence
                        "refined": list[dict]    # List of refined themes containing this sentence
                    }
                }
                OR
                {
                    "sentence": str,
                    "topics": None  # If sentence was never assigned to any theme
                }

        """
        logger.info("Creating sentence-level theme mapping from tracked source_sentences")

        # extract all sentences from text sections
        self.all_original_sentences = self.extract_sentences_from_text_sections(text_sections)

        # collect assigned sentences from all theme stages
        self.assigned_sentences = self.collect_assigned_sentences(initial_themes, condensed_themes, refined_themes)

        # create mapping for each sentence
        sentence_mappings = []
        for sentence in sorted(self.all_original_sentences):
            mapping = self.create_sentence_mapping(sentence, initial_themes, condensed_themes, refined_themes)
            sentence_mappings.append(mapping)

        logger.info(f"Created sentence mappings for {len(sentence_mappings)} sentences")
        return sentence_mappings
