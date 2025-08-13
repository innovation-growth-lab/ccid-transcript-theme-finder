"""Session processor for focus group analysis.

This module provides functionality to process transcript sessions from CSV files
and create text sections for analysis.
"""

import csv
import logging
import re
from pathlib import Path
from typing import List, Tuple

from ..models import FacilitatorRemovalResponse, TextSection, TranscriptSession
from .gemini_processor import GeminiProcessor, process_items_with_gemini

logger = logging.getLogger(__name__)


def extract_deliberation_phase(filename: str) -> str:
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


def extract_system_info(filename: str) -> str:
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


def extract_session_info_from_folder_name(folder_name: str) -> dict[str, str]:
    """Extract session information from deliberation folder name.

    Args:
        folder_name: The folder name to parse (e.g., "090000_fli-system-1-expert_0196f390")

    Returns:
        dict containing time, system, and session_id

    """
    parts = folder_name.split("_")

    if len(parts) >= 3:
        time_str = parts[0]
        system_info = parts[1]
        session_id = parts[2]

        return {"time": time_str, "system": system_info, "session_id": session_id}
    else:
        # fallback for malformed folder names (no such cases yet)
        return {"time": "unknown", "system": "unknown", "session_id": folder_name}


def find_date_folders(root_folder_path: Path) -> List[Path]:
    """Find all date folders in the root folder.

    Args:
        root_folder_path: Path to the root folder

    Returns:
        list[Path]: List of date folder paths

    """
    date_folders = [f for f in root_folder_path.iterdir() if f.is_dir() and f.name.count("-") == 2]

    if not date_folders:
        raise ValueError(f"No date folders found in {root_folder_path}")

    logger.info(f"Found {len(date_folders)} date folders in {root_folder_path}")
    return date_folders


def find_session_folders(date_folder: Path) -> List[Path]:
    """Find all session folders within a date folder.

    Args:
        date_folder: Path to the date folder

    Returns:
        list[Path]: List of session folder paths

    """
    session_folders = [f for f in date_folder.iterdir() if f.is_dir()]

    if not session_folders:
        logger.warning(f"No session folders found in date folder {date_folder.name}")

    return session_folders


def check_csv_has_transcript_content(csv_path: Path) -> bool:
    """Check if a CSV file contains valid transcript content.

    Args:
        csv_path: Path to the CSV file to check

    Returns:
        bool: True if file contains transcript content, False otherwise

    """
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "transcript" in row and row["transcript"].strip():
                    return True
        return False
    except Exception:
        return False


def find_section_file(session_folder: Path, target_section: str) -> Path | None:
    """Find the specific section file within a session's deliberation folder.

    Args:
        session_folder: Path to the session folder
        target_section: The target section to find

    Returns:
        Path | None: Path to the section file, or None if not found

    """
    deliberation_folder = session_folder / "deliberation"

    if not deliberation_folder.exists():
        logger.warning(f"No deliberation folder found in session {session_folder.name}")
        return None

    # look for files that contain the target section in their name
    section_files = []
    for file in deliberation_folder.glob("*.csv"):
        if target_section in file.name:
            section_files.append(file)

    if not section_files:
        logger.warning(f"No {target_section} file found in deliberation folder {deliberation_folder}")
        return None

    if len(section_files) == 1:
        return section_files[0]

    # multiple files found - check which ones have content
    valid_files = []
    for file in section_files:
        if check_csv_has_transcript_content(file):
            valid_files.append(file)
        else:
            logger.info(f"Discarding empty file: {file.name}")

    if not valid_files:
        logger.warning(f"All {target_section} files found are empty in deliberation folder {deliberation_folder}")
        return None

    if len(valid_files) > 1:
        logger.warning(f"Multiple non-empty {target_section} files found, using first: {valid_files[0].name}")

    return valid_files[0]


class DeliberationProcessor:
    """Processor for transcript deliberations from CSV files."""

    def __init__(self, processor: GeminiProcessor | None = None) -> None:
        """Init the session processor.

        Args:
            processor: Optional GeminiProcessor for facilitator removal

        """
        self.processor = processor

    def _load_transcript_from_csv(self, csv_path: str | Path, session_id: str | None = None) -> TextSection:
        """Load a transcript session from a CSV file.

        Args:
            csv_path: Path to the CSV file containing transcript data
            session_id: Optional session id to use for the text section

        Returns:
            TextSection: the section data

        """
        csv_path = Path(csv_path)

        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        # read all transcript rows from CSV
        transcripts = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "transcript" in row and row["transcript"].strip():
                    transcripts.append(row["transcript"].strip())

        if not transcripts:
            raise ValueError(f"No transcript found in CSV file: {csv_path}")

        # combine all transcripts
        transcript = " ".join(transcripts)

        # parse filename to extract deliberation phase and system context
        filename = csv_path.stem

        # remove any of the substrings in the list from filename before extracting deliberation phase
        filename = filename.replace("audio-recording-", "").replace("transcription-", "")

        # extract deliberation phase (e.g., "groundwork-intro", "mission-deep-dive-process")
        deliberation_phase = extract_deliberation_phase(filename)

        # extract system context (System 1 or System 2)
        system_info = extract_system_info(filename)

        # create session id from deliberation phase
        section_id = deliberation_phase.replace("-", "_")

        return TextSection(section_id=section_id, content=transcript, session_id=session_id, system_info=system_info)

    def _load_transcripts_from_folder(
        self, folder_path: str | Path, session_id: str | None = None
    ) -> List[TextSection]:
        """Load multiple transcript sessions from a folder of CSV files.

        Args:
            folder_path: Path to the folder containing CSV files
            session_id: Optional session id to use for the text section

        Returns:
            list[TextSection]: one per CSV file

        """
        assert isinstance(folder_path, (str, Path)), "Folder path must be provided and be a string or Path object"

        folder_path = Path(folder_path)

        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        # find all CSV files in the folder
        csv_files = list(folder_path.glob("*.csv"))

        if not csv_files:
            raise ValueError(f"No CSV files found in folder: {folder_path}")

        logger.info(f"Found {len(csv_files)} CSV files in {folder_path}")

        # load each CSV file as a separate session
        sections = []
        for csv_file in sorted(csv_files):  # sort for consistent ordering
            try:
                section = self._load_transcript_from_csv(csv_file, session_id)
                sections.append(section)
                logger.info(f"Loaded session from {csv_file.name}: {section.session_id}")
            except Exception as e:
                logger.error(f"Failed to load {csv_file.name}: {e}")
                continue

        if not sections:
            raise ValueError(f"No valid sections loaded from folder: {folder_path}")

        logger.info(f"Successfully loaded {len(sections)} sections from folder")
        return sections

    def _create_transcript_session(
        self, sections: List[TextSection], system_info: str, session_id: str | None = None
    ) -> TranscriptSession:
        """Create a combined session from multiple transcript sessions.

        This creates a single session that represents the entire deliberation
        by combining all the individual session contents.

        Args:
            sections: List of TextSection objects to combine
            system_info: System context for the combined session (1 or 2)
            session_id: Optional session id to use for the transcript session

        Returns:
            TranscriptSession: the combined data across deliberation phases

        """
        if not sections:
            raise ValueError("No sections provided for combination")

        # combine all transcript contents into a single string
        combined_content = "\n\n".join([section.content for section in sections])

        logger.info(f"Created combined session with {len(sections)} individual sections")
        return TranscriptSession(session_id=session_id, content=combined_content, system_info=system_info)

    async def _remove_facilitator_content(
        self,
        transcript_sections: list[TextSection],
    ) -> list[TextSection]:
        """Remove facilitator content from transcript while preserving participant discussions.

        Args:
            transcript_sections: The raw transcript sections to process

        Returns:
            Cleaned transcript content with facilitator content removed

        """
        logger.info("Processing transcript for facilitator content removal")

        # assume (not safe!) topic is the same for all sections  # david: need to fix this
        system_info = transcript_sections[0].system_info

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
            discussion_topic=system_info,
        )

        # replace the content of the transcript sections with the cleaned content
        for section, cleaned_content in zip(transcript_sections, filtered_sections, strict=True):
            section.content = cleaned_content["cleaned_content"]

        return transcript_sections

    def _load_specific_section_across_sessions(
        self, root_folder_path: str | Path, target_section: str
    ) -> List[TextSection]:
        """Load a specific section from all deliberation sessions across all dates.

        Args:
            root_folder_path: Path to the root folder containing date folders
            target_section: The specific section to extract (e.g., "groundwork-intro")

        Returns:
            list[TextSection]: one per deliberation session containing the target section

        """
        root_folder_path = Path(root_folder_path)

        if not root_folder_path.exists():
            raise FileNotFoundError(f"Root folder not found: {root_folder_path}")

        date_folders = find_date_folders(root_folder_path)
        text_sections = []

        for date_folder in sorted(date_folders):
            logger.info(f"Processing date folder: {date_folder.name}")

            session_folders = find_session_folders(date_folder)
            if not session_folders:
                continue

            for session_folder in sorted(session_folders):
                try:
                    session_info = extract_session_info_from_folder_name(session_folder.name)
                    section_file = find_section_file(session_folder, target_section)

                    if section_file is None:
                        continue

                    text_section = self._load_transcript_from_csv(section_file, session_id=session_info["session_id"])
                    text_sections.append(text_section)
                    logger.info(
                        f"Loaded {target_section} from session {session_info['session_id']} in date {date_folder.name}"
                    )

                except Exception as e:
                    logger.error(f"Failed to load {target_section} from session {session_folder.name}: {e}")
                    continue

        if not text_sections:
            raise ValueError(f"No valid {target_section} sections found across all sessions in {root_folder_path}")

        logger.info(
            f"Successfully loaded {target_section} from {len(text_sections)} sessions across {len(date_folders)} dates"
        )
        return text_sections

    async def process_session_folder(
        self, folder_path: str | Path, session_id: str | None = None
    ) -> Tuple[TranscriptSession, List[TextSection]]:
        """Process a folder of transcript sessions from JSON files.

        Args:
            folder_path: Path to the folder containing JSON files
            session_id: Optional session id to use for the transcript session

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
        text_sections = self._load_transcripts_from_folder(folder_path, session_id=session_id)

        # remove facilitator content if requested
        if self.processor:
            logger.info("Removing facilitator content from all sessions")
            text_sections = await self._remove_facilitator_content(text_sections)

        # create a combined session for overall analysis
        system_info = text_sections[0].system_info
        combined_session = self._create_transcript_session(text_sections, system_info=system_info)

        logger.info(f"Processing complete: {len(text_sections)} sections created from {len(text_sections)} files.")
        return combined_session, text_sections

    async def process_specific_section_across_sessions(
        self, date_folder_path: str | Path, target_section: str
    ) -> Tuple[TranscriptSession, List[TextSection]]:
        """Process a specific section across all deliberation sessions on a given date.

        Args:
            date_folder_path: Path to the date folder (e.g., "2025-06-05")
            target_section: The specific section to extract (e.g., "groundwork-intro")

        Returns:
            combined_session: TranscriptSession representing all sessions
            text_sections: list[TextSection] one per deliberation session

        Raises:
            FileNotFoundError: If the date folder path does not exist
            ValueError: If no deliberation session folders are found
            ValueError: If no valid sections are found across sessions

        """
        logger.info(f"Processing {target_section} across sessions in date folder: {date_folder_path}")

        # load the specific section from all deliberation sessions
        text_sections = self._load_specific_section_across_sessions(date_folder_path, target_section)

        # remove facilitator content if requested
        if self.processor:
            logger.info("Removing facilitator content from all sections")
            # Convert TextSections back to TranscriptSessions for facilitator removal
            transcript_sessions = [
                TranscriptSession(
                    session_id=section.session_id,
                    content=section.content,
                    system_info=section.system_info,
                )
                for section in text_sections
            ]

            cleaned_sessions = await self._remove_facilitator_content(transcript_sessions)

            # update the text sections with cleaned content
            for section, cleaned_session in zip(text_sections, cleaned_sessions, strict=True):
                section.content = cleaned_session.content

        # create a combined session for overall analysis
        combined_content = "\n\n".join([section.content for section in text_sections])
        combined_session = TranscriptSession(
            session_id=f"combined_{target_section}_sessions",
            content=combined_content,
            system_info=text_sections[0].system_info,
        )

        logger.info(f"Processing complete: {target_section} loaded from {len(text_sections)} sessions.")
        return combined_session, text_sections
