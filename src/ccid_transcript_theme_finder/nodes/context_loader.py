"""Context loader for section-specific analysis context."""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def load_section_context(context_file_path: str) -> dict[str, dict[str, str]]:
    """Load section context from Excel or CSV file.

    Args:
        context_file_path: Path to the Excel or CSV file containing section context

    Returns:
        Dictionary mapping section names to their context information

    """
    try:
        df = pd.read_excel(context_file_path)
        df["section_key"] = df["reference"].str.replace("_", "-")

        context_dict = {}
        for _, row in df.iterrows():
            section_key = row["section_key"]
            context_dict[section_key] = {
                "stimulus": str(row.get("stimulus", "")),
                "core_question": str(row.get("core_question", "")),
                "facilitator_prompts": str(row.get("facilitator_prompt", "")),
            }

        return context_dict

    except Exception as e:
        logger.warning(f"Warning: Could not load context file {context_file_path}: {e}")
        # default to empty dictionary if there is an error
        return {}


def get_section_context(section_id: str, context_dict: dict[str, dict[str, str]]) -> dict[str, str]:
    """Get context for a specific section.

    Args:
        section_id: The section ID to look up
        context_dict: Dictionary of section contexts

    Returns:
        Context information for the section, or empty strings if not found

    """
    if section_id in context_dict:
        return context_dict[section_id]

    # try fuzzy matches
    section_parts = set()
    for separator in ["_", "-"]:
        section_parts.update(section_id.split(separator))

    # Remove empty parts and convert to lowercase for comparison
    section_parts = {part.lower() for part in section_parts if part}

    best_match = None
    best_score = 0

    for context_key in context_dict.keys():
        context_parts = set()
        for separator in ["_", "-"]:
            context_parts.update(context_key.split(separator))

        # remove empty parts and convert to lowercase
        context_parts = {part.lower() for part in context_parts if part}

        # calculate overlap score
        overlap = len(section_parts.intersection(context_parts))
        if overlap > best_score and overlap > 0:
            best_score = overlap
            best_match = context_key

    if best_match:
        return context_dict[best_match]
    # return empty context if not found
    return {"stimulus": "", "core_question": "", "facilitator_prompts": ""}
