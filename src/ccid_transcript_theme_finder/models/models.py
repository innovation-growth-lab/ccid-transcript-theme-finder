"""Data models for focus group analysis - pure Pydantic (for now!)."""

from typing import Self

from pydantic import BaseModel, Field, model_validator


class TranscriptSession(BaseModel):
    """Model for a transcript session/topic."""

    session_id: str | None = Field(None, description="unique identifier for this session")
    content: str = Field(..., description="the full transcript content for this session")
    system_info: str = Field(..., description="system context for this session")


class TextSection(BaseModel):
    """Model for a section of text within a transcript."""

    section_id: str = Field(..., description="Unique identifier for this text section")
    session_id: str | None = Field(None, description="Which session this section belongs to")
    system_info: str = Field(..., description="System context for this section")
    content: str = Field(..., description="The text content of this section")


class Theme(BaseModel):
    """Model for a single extracted theme from transcript sessions."""

    topic_label: str = Field(..., description="Short label summarising the topic in a few words")
    topic_description: str = Field(..., description="More detailed description of the topic in 1-2 sentences")
    source_sentences: list[str] = Field(
        default_factory=list, description="List of sentences where this theme originated"
    )


class ThemeGenerationResponse(BaseModel):
    """Response from theme generation."""

    section_id: str = Field(..., description="Unique identifier for this text section")
    themes: list[Theme] = Field(..., description="List of extracted themes")


class CondensedTheme(BaseModel):
    """Model for a condensed theme."""

    topic_label: str = Field(..., description="Representative label for the condensed topic")
    topic_description: str = Field(
        ..., description="Concise description incorporating key insights from constituent topics"
    )
    source_session_count: int = Field(..., ge=0, description="Sum of source_session_counts from combined topics")
    source_sentences: list[str] = Field(
        default_factory=list, description="List of all sentences that contributed to this theme"
    )


class ThemeCondensationResponse(BaseModel):
    """Response from theme condensation."""

    condensed_themes: list[CondensedTheme] = Field(..., description="List of condensed themes")


class RefinedTheme(BaseModel):
    """Model for a refined theme with standardized format."""

    topic_id: str = Field(..., description="Single uppercase letter ID (A-Z, then AA, AB, etc.)")
    topic_label: str = Field(..., description="Brief, clear topic label (3-7 words)")
    topic_description: str = Field(..., description="Detailed description (1-2 sentences)")
    source_session_count: int = Field(..., ge=0, description="Count of source sessions combined")
    source_sentences: list[str] = Field(
        default_factory=list, description="List of all sentences that contributed to this theme"
    )

    @model_validator(mode="after")
    def validate_topic_id_format(self) -> Self:
        """Validate that topic_id follows the expected format."""
        topic_id = self.topic_id.strip()
        if not topic_id.isupper() or not topic_id.isalpha():
            raise ValueError(f"topic_id must be uppercase letters only: {topic_id}")
        return self


class ThemeRefinementResponse(BaseModel):
    """Response from theme refinement."""

    refined_themes: list[RefinedTheme] = Field(..., description="List of refined themes")


class TextSectionMapping(BaseModel):
    """Model for mapping a text section to themes."""

    section_id: str = Field(..., description="Text section ID")
    theme_labels: list[str] = Field(..., description="List of theme IDs")
    reasons: list[str] = Field(..., description="List of reasons for mapping")


class TextSectionMappingResponse(BaseModel):
    """Response from text section mapping."""

    mappings: list[TextSectionMapping] = Field(..., description="List of text section mappings")


class FacilitatorRemovalResponse(BaseModel):
    """Response from facilitator content removal."""

    cleaned_content: str = Field(..., description="Transcript content with facilitator content removed")
