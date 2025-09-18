# CCID Transcript Theme Finder

A tool for analysing focus group transcripts to identify and map key themes from participant discussions.

## Overview

This tool processes transcript data from focus group sessions to extract meaningful themes and insights. It uses AI-powered analysis to identify distinct topics, viewpoints, and discussion points from participant conversations, providing a structured approach to understanding the range of perspectives shared during deliberation sessions.

![diagram](https://igl-public.s3.eu-west-2.amazonaws.com/misc/basic_pipeline.svg)

## Functionality

The tool performs a multi-stage analysis process:

1. **Session processing**: Loads transcript data from CSV files and optionally removes facilitator content
2. **Theme generation**: Extracts initial themes from transcript segments, identifying distinct topics and viewpoints
3. **Bootstrap theme condensation**: Uses multiple bootstrap samples with different theme orderings to build a co-occurrence network, then applies Louvain clustering for robust theme combination
4. **Theme refinement**: Polishes themes with clear labels, descriptions, and unique identifiers
5. **Sentence mapping**: Links individual participant contributions to the identified themes
6. **Sentiment analysis**: Analyses the position and stance of sentences within each theme
7. **Theme tracing**: Tracks the evolution of themes from initial granular themes through condensation to final refined themes, including session count tracking

## Features

- **Bootstrap condensation**: Robust theme clustering using multiple bootstrap samples and network analysis
- **Concurrent processing**: Handles multiple API calls simultaneously for each stage
- **Configurable parameters**: Adjustable batch sizes, concurrency limits, and bootstrap sample counts
- **Facilitator removal**: Optional filtering of moderator content to focus on participant insights
- **Session tracking**: Counts unique sessions associated with each theme at different processing stages
- **Theme evolution tracing**: Complete lineage tracking from granular themes through condensation to final refined themes
- **Context integration**: Incorporates section-specific context (stimulus, core questions, facilitator prompts) into theme analysis
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

## Bootstrap condensation approach

The tool uses a bootstrap sampling approach for theme condensation that provides more robust and reliable results than alternative single-pass methods:

1. **Multiple bootstrap samples**: Generates multiple (default: 5) different random orderings of themes
2. **Co-occurrence network**: Builds a network where themes are nodes and edges represent how often they are grouped together
3. **Louvain clustering**: Applies community detection algorithms to find optimal theme clusters based on co-occurrence probabilities

## Session Tracking and Progress Monitoring

The tool provides tracking of theme evolution and session coverage:

- **Session Count Tracking**: Counts unique sessions associated with each theme at different processing stages
- **Theme Lineage**: Complete tracking from initial granular themes through condensation to final refined themes
- **Cross-Session Analysis**: When processing multiple sessions, tracks which themes appear across different sessions

## Output format

The tool produces structured data including:
- **Initial themes**: Extracted from transcript segments with unique topic IDs
- **Condensed themes**: Combined themes using bootstrap sampling and network clustering
- **Refined themes**: Final themes with clear labels, descriptions, and unique identifiers (A, B, C, etc.)
- **Theme trace data**: Complete evolution tracking showing how granular themes flow through condensation to final themes
- **Session counts**: Number of unique sessions associated with each theme at different processing stages
- **Sentence mapping**: Links individual participant contributions to themes with section and session IDs
- **Sentiment analysis**: Position and stance analysis of sentences within each theme

## Example usage

```bash
python example/main_pipeline.py \
    --data_path "data/2025 Live FLI workshops - Consult tool" \
    --target_section "groundwork-intro"
```

This will process the specified data and save results to CSV files in the `example/outputs/` directory.