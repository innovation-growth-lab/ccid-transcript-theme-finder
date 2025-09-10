"""Data models for focus group analysis - pure Pydantic (for now!)."""


from pydantic import BaseModel, Field


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
    source_topic_list: list[str] = Field(
        default_factory=list, description="List of topic_id values from original themes that were combined"
    )
    source_sentences: list[str] = Field(
        default_factory=list, description="List of all sentences that contributed to this theme"
    )


class ThemeCondensationResponse(BaseModel):
    """Response from theme condensation."""

    condensed_themes: list[CondensedTheme] = Field(..., description="List of condensed themes")


class RefinedTheme(BaseModel):
    """Model for a refined theme with standardized format."""

    topic_label: str = Field(..., description="Brief, clear topic label (3-7 words)")
    topic_description: str = Field(..., description="Detailed description (1-2 sentences)")
    source_topic_list: list[str] = Field(
        default_factory=list, description="List of topic_id values from original themes that contributed to this theme"
    )
    source_sentences: list[str] = Field(
        default_factory=list, description="List of all sentences that contributed to this theme"
    )


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


class SentenceSentiment(BaseModel):
    """Model for analysing sentiment and stance of a single sentence."""

    sentence: str = Field(..., description="The sentence being considered")
    position: str = Field(..., description="Position: 'agreement', 'disagreement', or 'unclear'")
    stance: str = Field(..., description="Stance: 'positive', 'negative', or 'unclear'")


class ThemeSentiment(BaseModel):
    """Model for sentiment analysis of all sentences within a theme."""

    topic_id: str = Field(..., description="The topic ID of the theme being considered")
    topic_label: str = Field(..., description="The topic label of the theme")
    sentence_sentiments: list[SentenceSentiment] = Field(
        ..., description="Sentiment analysis for each sentence in the theme"
    )
