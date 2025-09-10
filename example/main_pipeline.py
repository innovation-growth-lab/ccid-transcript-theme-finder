#!/usr/bin/env python3
"""Minimal script to execute the pipeline for debugging.

This script demonstrates how to use the updated pipeline that processes
a folder of JSON files, where each JSON file represents a different
section/chunk of the deliberation.

Argparse is used to parse command line arguments. Example usage:

```bash
python example/main_pipeline.py \
    --data_path "data/2025 Live FLI workshops - Consult tool" \
    --target_section "groundwork-intro"
```
"""

import argparse
import asyncio
from pathlib import Path
from typing import Any

import pandas as pd

from ccid_transcript_theme_finder.pipeline import analyse_deliberation_session


def extract_topic_labels(mapping: dict[str, Any]) -> dict[str, Any]:
    """Extract topic labels from the nested topics structure."""
    topics = mapping.get("topics", {})

    # if topics is None, return empty themes
    if topics is None:
        return {
            "sentence_id": mapping.get("sentence_id", ""),
            "sentence": mapping.get("sentence", ""),
            "initial_theme": None,
            "condensed_theme": None,
            "refined_theme": None,
        }

    # Extract single theme label for each level (take the first one if multiple exist)
    initial_themes = topics.get("initial", [])
    initial_label = initial_themes[0].get("topic_label", "") if initial_themes else ""

    condensed_themes = topics.get("condensed", [])
    condensed_label = condensed_themes[0].get("topic_label", "") if condensed_themes else ""

    refined_themes = topics.get("refined", [])
    refined_label = refined_themes[0].get("topic_label", "") if refined_themes else ""

    return {
        "sentence_id": mapping.get("sentence_id", ""),
        "sentence": mapping.get("sentence", ""),
        "initial_theme": initial_label,
        "condensed_theme": condensed_label,
        "refined_theme": refined_label,
    }


async def main(session_folder: str, target_section: str | None) -> dict[str, Any]:
    """Main function to execute the pipeline.

    Args:
        session_folder: Path to the session folder
        target_section: Optional target section to process
        remove_short_sentences: Whether to remove short sentences from the transcript

    Returns:
        results: dict[str, Any]

    """
    # run the async pipeline
    results = await analyse_deliberation_session(
        session_folder, target_section=target_section, remove_short_sentences=True
    )

    print("Pipeline completed!")
    print(f"Processed {len(results['text_sections'])} text sections")
    print(f"Generated {len(results['initial_themes'])} initial themes")
    print(f"Condensed to {len(results['condensed_themes'])} themes")
    print(f"Refined to {len(results['refined_themes'])} final themes")
    print(f"Created sentence mappings for {len(results['sentence_theme_mapping'])} sentences")

    # count sentences with and without themes
    sentences_with_themes = sum(1 for mapping in results["sentence_theme_mapping"] if mapping["topics"] is not None)
    sentences_without_themes = sum(1 for mapping in results["sentence_theme_mapping"] if mapping["topics"] is None)
    print("\nSentence coverage:")
    print(f"Sentences with themes: {sentences_with_themes}")
    print(f"Sentences without themes: {sentences_without_themes}")
    print(f"Total sentences: {len(results['sentence_theme_mapping'])}")

    # save outputs to CSV files
    outputs_dir = Path("example/outputs" + (f"/{target_section}" if target_section else ""))
    outputs_dir.mkdir(exist_ok=True)

    pd.DataFrame(results["initial_themes"]).to_csv(outputs_dir / "initial_themes.csv", index=False)
    pd.DataFrame(results["condensed_themes"]).to_csv(outputs_dir / "condensed_themes.csv", index=False)
    pd.DataFrame(results["refined_themes"]).to_csv(outputs_dir / "refined_themes.csv", index=False)
    pd.DataFrame(results["theme_trace_data"]).to_csv(outputs_dir / "theme_trace_data.csv", index=False)

    # process sentence mapping to extract topic labels
    sentence_mappings = [extract_topic_labels(mapping) for mapping in results["sentence_theme_mapping"]]
    pd.DataFrame(sentence_mappings).to_csv(outputs_dir / "sentence_mapping.csv", index=False)

    pd.DataFrame(results["sentiment_analyses"]).to_csv(outputs_dir / "sentiment_analyses.csv", index=False)

    print(f"\nOutputs saved to {outputs_dir}/")

    return results


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run the CCID transcript theme finder pipeline on a session folder.")
    parser.add_argument(
        "--data_path", type=str, help="Path to the deliberation session folder (containing JSON files)."
    )
    parser.add_argument(
        "--target_section",
        type=str,
        default=None,
        help="(Optional) Specific section to analyze across sessions (e.g., 'groundwork-intro').",
    )
    parser.add_argument(
        "--remove_short_sentences",
        action="store_true",
        default=True,
        help="Whether to remove short sentences from the transcript (default: True)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.data_path, args.target_section))
