# CCID Transcript Theme Finder

A tool for analysing focus group transcripts to identify and map key themes from participant discussions.

## Overview

This tool processes transcript data from focus group sessions to extract meaningful themes and insights. It uses AI-powered analysis to identify distinct topics, viewpoints, and discussion points from participant conversations, providing a structured approach to understanding the range of perspectives shared during deliberation sessions.

## Functionality

The tool performs a multi-stage analysis process:

1. **Session processing**: Loads transcript data from JSON files and optionally removes facilitator content
2. **Theme generation**: Extracts initial themes from transcript segments, identifying distinct topics and viewpoints
3. **Theme condensation**: Combines similar or redundant themes while preserving nuanced differences
4. **Theme refinement**: Polishes themes with clear labels, descriptions, and unique identifiers
5. **Contribution mapping**: Links individual participant contributions to the identified themes

## Current relevant features

- **Concurrent processing**: Handles multiple API calls simultaneously for each stage
- **Configurable parameters**: Batch sizes are adjustable, and so is concurrency limits, and iteration counts for theme condensation
- **Facilitator removal**: Optional filtering of moderator content to focus on participant insights
- **Structured output**: Generates themes with topic IDs, labels, descriptions, and source sentence mappings

## Requirements

- Python 3.8 or higher
- Access to Google's Gemini API (Key stored as environment variable)
- Transcript data folder with JSON formats

## Installation

```bash
pip install ccid-transcript-theme-finder
```

## Usage

```python
from ccid_transcript_theme_finder.pipeline import analyse_deliberation_session

# Analyse a transcript session
results = await analyse_deliberation_session(
    session_path="path/to/transcript/folder",
    model_name="gemini-2.5-flash",
    remove_facilitator_content=True
)
```

## Output format

The tool produces structured data including:
- Initial themes extracted from transcript segments
- Condensed themes after similarity analysis
- Refined themes with clear labels and descriptions
- Sentence-level mapping of participant contributions to themes
