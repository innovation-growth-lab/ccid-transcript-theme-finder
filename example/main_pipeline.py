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
from typing import Any

from ccid_transcript_theme_finder.pipeline import analyse_deliberation_session


async def main(session_folder: str, target_section: str | None) -> dict[str, Any]:
    """Main function to execute the pipeline."""
    results = await analyse_deliberation_session(session_folder, target_section=target_section)

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
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.data_path, args.target_section))
