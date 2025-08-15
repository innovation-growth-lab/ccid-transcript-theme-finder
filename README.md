# CCID Transcript Theme Finder

A tool for analysing focus group transcripts to identify and map key themes from participant discussions.

## Overview

This tool processes transcript data from focus group sessions to extract meaningful themes and insights. It uses AI-powered analysis to identify distinct topics, viewpoints, and discussion points from participant conversations, providing a structured approach to understanding the range of perspectives shared during deliberation sessions.

## Functionality

The tool performs a multi-stage analysis process:

1. **Session processing**: Loads transcript data from CSV files and optionally removes facilitator content
2. **Theme generation**: Extracts initial themes from transcript segments, identifying distinct topics and viewpoints
3. **Theme condensation**: Combines similar or redundant themes while preserving nuanced differences
4. **Theme refinement**: Polishes themes with clear labels, descriptions, and unique identifiers
5. **Sentence mapping**: Links individual participant contributions to the identified themes
6. **Sentiment analysis**: Analyses the position and stance of sentences within each theme

## Features

- **Concurrent processing**: Handles multiple API calls simultaneously for each stage
- **Configurable parameters**: Adjustable batch sizes, concurrency limits, and iteration counts for theme condensation
- **Facilitator removal**: Optional filtering of moderator content to focus on participant insights
- **Structured output**: Generates themes with topic IDs, labels, descriptions, and source sentence mappings
- **CSV export**: Saves all analysis results to CSV files for further analysis

## Requirements

- Python 3.8 or higher
- Access to Google's Gemini API (Key stored as environment variable)
- Transcript data folder with CSV formats

## Installation

```bash
pip install ccid-transcript-theme-finder
```

## Usage

The tool supports two processing modes:

### Session mode (default)
Analyse all sections within a single deliberation session:

```python
from ccid_transcript_theme_finder.pipeline import analyse_deliberation_session

# Analyse a transcript session
results = await analyse_deliberation_session(
    data_path="path/to/transcript/folder",
    model_name="gemini-2.5-flash",
    remove_facilitator_content=True
)
```

### Cross-session mode
Analyse a specific section across all deliberation sessions across all dates:

```python
from ccid_transcript_theme_finder.pipeline import analyse_deliberation_session

# Analyse a specific section across all sessions across all dates
results = await analyse_deliberation_session(
    data_path="path/to/root/folder",     # Root folder containing date folders
    target_section="groundwork-intro",   # specific section to analyse
    model_name="gemini-2.5-flash",
    remove_facilitator_content=True
)
```

**Folder structure for cross-session mode:**
```
root_folder/
├── 2025-06-05/
│   ├── 090000_fli-system-1-expert_0196f390/
│   │   └── deliberation/
│   │       ├── session-id_system-id_audio-recording_01-groundwork-intro.csv
│   │       ├── session-id_system-id_audio-recording_02-mission-deep-dive.csv
│   │       └── ...
│   ├── 140000_fli-system-1-12345678/
│   │   └── deliberation/
│   │       ├── session-id_system-id_audio-recording_01-groundwork-intro.csv
│   │       └── ...
│   └── ...
├── 2025-06-06/
│   └── ...
└── ...
```

**CSV file format:**
Each CSV file should contain a "transcript" column with the conversation text. The tool automatically concatenates all transcript rows to create the full conversation content.

## Output format

The tool produces structured data including:
- Initial themes extracted from transcript segments
- Condensed themes after similarity analysis
- Refined themes with clear labels and descriptions
- Sentence-level mapping of participant contributions to themes
- Sentiment analysis of position and stance within themes

## Example usage

```bash
python example/main_pipeline.py \
    --data_path "data/2025 Live FLI workshops - Consult tool" \
    --target_section "groundwork-intro"
```

This will process the specified data and save results to CSV files in the `example/outputs/` directory.