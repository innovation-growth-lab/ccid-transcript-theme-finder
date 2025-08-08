"""Session processor for focus group analysis.

This module provides functionality to process transcript sessions from JSON files
and create text sections for analysis.
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Tuple

from ..models import FacilitatorRemovalResponse, TextSection, TranscriptSession
from .gemini_processor import GeminiProcessor, process_items_with_gemini

logger = logging.getLogger(__name__)


class SessionProcessor:
    """Processor for transcript sessions from JSON files."""

    def __init__(self, processor: GeminiProcessor | None = None) -> None:
        """Init the session processor.

        Args:
            processor: Optional GeminiProcessor for facilitator removal

        """
        self.processor = processor

    def _extract_deliberation_phase(self, filename: str) -> str:
        """Extract deliberation phase from filename.

        Args:
            filename: The filename to parse

        Returns:
            The deliberation phase (e.g., "groundwork-intro", "mission-deep-dive-process")

        """
        pattern = r".*_(\d+-\w+(?:-\w+)*)$"
        match = re.search(pattern, filename)

        if match:
            return match.group(1)

        # fallback: try to extract from the end of filename
        parts = filename.split("_")
        if len(parts) > 1:
            last_part = parts[-1]
            # remove any trailing numbers or extensions
            phase = re.sub(r"-\d+$", "", last_part)
            return phase

        # final fallback: use the filename
        return filename

    def _extract_system_context(self, filename: str) -> str:
        """Extract system context from filename.

        Args:
            filename: The filename to parse

        Returns:
            The system context with comprehensive Public AI Task Force information

        """
        if "system-1" in filename.lower() or "fli-system-1" in filename.lower():
            return (
                "System 1 - Consult Tool (Government Consultations) | "
                "Public AI Task Force - Government Consultations pilot examining the Consult tool "
                "developed by the UK Government's Incubator for AI. This is part of an immersive "
                "public engagement experience using educational media content and deliberative polling "
                "to assess public preferences about AI tool use in government consultations. "
                "The research aims to develop an AI Social Readiness Advisory Label and generate "
                "evidence about deliberative public engagement efficacy for AI assurance."
            )
        elif "system-2" in filename.lower() or "fli-system-2" in filename.lower():
            return (
                "System 2 - MagicNotes (Social Care) | "
                "Public AI Task Force - Social Care pilot examining the MagicNotes tool "
                "developed by social enterprise Beam. This is part of an immersive "
                "public engagement experience using educational media content and deliberative polling "
                "to assess public preferences about AI tool use in social care. "
                "The research aims to develop an AI Social Readiness Advisory Label and generate "
                "evidence about deliberative public engagement efficacy for AI assurance."
            )
        else:
            return "Unknown System - Public AI Task Force Context"

    def _load_transcript_from_json(self, json_path: str | Path) -> TranscriptSession:
        """Load a transcript session from a JSON file.

        Args:
            json_path: Path to the JSON file containing transcript data

        Returns:
            TranscriptSession: the session data

        """
        json_path = Path(json_path)

        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)  # [DAVID] how to do this in a more pythonic way when using streamlit?

        # extract transcript from the JSON structure
        transcript = data.get("results", {}).get("transcripts", [{}])[0].get("transcript", "")

        if not transcript:
            raise ValueError(f"No transcript found in JSON file: {json_path}")

        # parse filename to extract deliberation phase and system context
        filename = json_path.stem

        # extract deliberation phase (e.g., "groundwork-intro", "mission-deep-dive-process")
        deliberation_phase = self._extract_deliberation_phase(filename)

        # extract system context (System 1 or System 2)
        system_context = self._extract_system_context(filename)

        # create session id from deliberation phase
        session_id = deliberation_phase.replace("-", "_")

        # create topic from system context
        topic = system_context

        return TranscriptSession(session_id=session_id, content=transcript, topic=topic)

    def _load_transcripts_from_folder(self, folder_path: str | Path) -> List[TranscriptSession]:
        """Load multiple transcript sessions from a folder of JSON files.

        Args:
            folder_path: Path to the folder containing JSON files

        Returns:
            list[TranscriptSession]: one per JSON file

        """
        folder_path = Path(folder_path)

        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        # find all JSON files in the folder
        json_files = list(folder_path.glob("*.json"))

        if not json_files:
            raise ValueError(f"No JSON files found in folder: {folder_path}")

        logger.info(f"Found {len(json_files)} JSON files in {folder_path}")

        # load each JSON file as a separate session
        sessions = []
        for json_file in sorted(json_files):  # sort for consistent ordering
            try:
                session = self._load_transcript_from_json(json_file)
                sessions.append(session)
                logger.info(f"Loaded session from {json_file.name}: {session.session_id}")
            except Exception as e:
                logger.error(f"Failed to load {json_file.name}: {e}")
                continue

        if not sessions:
            raise ValueError(f"No valid sessions loaded from folder: {folder_path}")

        logger.info(f"Successfully loaded {len(sessions)} sessions from folder")
        return sessions

    def _create_text_sections_from_sessions(self, sessions: List[TranscriptSession]) -> List[TextSection]:
        """Create text sections from multiple transcript sessions.

        Each session (JSON file) becomes a separate text section for analysis.

        Args:
            sessions: List of TranscriptSession objects to process

        Returns:
            list[TextSection]: a list of deliberation phase transcript sections

        """
        text_sections = []

        for index, session in enumerate(sessions):
            # create a section for each deliberation phase/session
            section = TextSection(
                section_id=session.session_id,
                content=session.content,
                session_id=session.session_id,
                section_index=index,
            )
            text_sections.append(section)
            logger.info(f"Created text section {index}: {session.session_id}")

        logger.info(f"Created {len(text_sections)} text sections from {len(sessions)} sessions")
        return text_sections

    def _create_combined_session(self, sessions: List[TranscriptSession]) -> TranscriptSession:
        """Create a combined session from multiple transcript sessions.

        This creates a single session that represents the entire deliberation
        by combining all the individual session contents.

        Args:
            sessions: List of TranscriptSession objects to combine

        Returns:
            TranscriptSession: the combined data across deliberation phases

        """
        if not sessions:
            raise ValueError("No sessions provided for combination")

        # use the first session's metadata as the base for the combined session
        base_session = sessions[0]

        # combine all transcript contents into a single string
        combined_content = "\n\n".join([session.content for session in sessions])

        # use the topic from the first session for the combined session
        topic = base_session.topic

        logger.info(f"Created combined session with {len(sessions)} individual sessions")
        return TranscriptSession(session_id="combined sessions", content=combined_content, topic=topic)

    async def _remove_facilitator_content(
        self,
        transcript_sections: list[TranscriptSession],
    ) -> list[TranscriptSession]:
        """Remove facilitator content from transcript while preserving participant discussions.

        Args:
            transcript_sections: The raw transcript sections to process

        Returns:
            Cleaned transcript content with facilitator content removed

        """
        logger.info("Processing transcript for facilitator content removal")

        # assume topic is the same for all sections
        discussion_topic = transcript_sections[0].topic

        # format transcript sections as items for the prompt template
        items = []
        for section in transcript_sections:
            items.append({"section_id": section.session_id, "content": section.content})

        # process through Gemini using the standard pattern
        filtered_sections = await process_items_with_gemini(
            items=items,
            prompt_template_name="facilitator_removal",
            response_model=FacilitatorRemovalResponse,
            processor=self.processor,
            discussion_topic=discussion_topic,
        )

        # replace the content of the transcript sections with the cleaned content
        for section, cleaned_content in zip(transcript_sections, filtered_sections, strict=True):
            section.content = cleaned_content["cleaned_content"]

        return transcript_sections

    async def process_session_folder(self, folder_path: str | Path) -> Tuple[TranscriptSession, List[TextSection]]:
        """Process a folder of transcript sessions from JSON files.

        Args:
            folder_path: Path to the folder containing JSON files

        Returns:
            combined_session: TranscriptSession
            text_sections: list[TextSection]

        Raises:
            FileNotFoundError: If the folder path does not exist
            ValueError: If no JSON files are found in the folder
            ValueError: If no valid sessions are loaded from the folder

        """
        logger.info(f"Processing session folder: {folder_path}")

        # load all deliberation sections from the folder
        deliberation_sections = self._load_transcripts_from_folder(folder_path)

        # remove facilitator content if requested
        if self.processor:
            logger.info("Removing facilitator content from all sessions")
            deliberation_sections = await self._remove_facilitator_content(deliberation_sections)

        # create text sections (one per JSON file/session)
        text_sections = self._create_text_sections_from_sessions(deliberation_sections)

        # create a combined session for overall analysis
        combined_session = self._create_combined_session(deliberation_sections)

        logger.info(
            f"Processing complete: {len(text_sections)} sections created from {len(deliberation_sections)} files."
        )
        return combined_session, text_sections
