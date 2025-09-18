"""Bootstrap condensation system using network clustering."""

import logging
import random
from collections import defaultdict
from typing import Any

import networkx as nx
from networkx.algorithms import community

from ..models import ThemeCondensationResponse
from .context_loader import get_section_context, load_section_context
from .gemini_processor import GeminiProcessor, process_items_with_gemini

logger = logging.getLogger(__name__)


class BootstrapCondenser:
    """Bootstrap condensation system using multiple shuffles and network clustering."""

    def __init__(
        self,
        processor: GeminiProcessor,
        discussion_topic: str,
        batch_size: int = 5,
        concurrency: int = 3,
        n_bootstrap_samples: int = 10,
        context_file_path: str | None = None,
    ) -> None:
        """Initialise the bootstrap condenser.

        Args:
            processor: GeminiProcessor to use
            discussion_topic: Topic of the discussion
            batch_size: Batch size for theme condensation
            concurrency: Number of concurrent API calls
            n_bootstrap_samples: Number of bootstrap samples to generate
            context_file_path: Optional path to Excel file with section context

        """
        self.processor = processor
        self.discussion_topic = discussion_topic
        self.batch_size = batch_size
        self.concurrency = concurrency
        self.n_bootstrap_samples = n_bootstrap_samples
        self.context_file_path = context_file_path

        # load context if provided
        self.context_dict = {}
        if context_file_path:
            self.context_dict = load_section_context(context_file_path)

    async def condense_themes(self, themes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Condense themes using bootstrap sampling and network clustering.

        Args:
            themes: List of themes to condense

        Returns:
            List of condensed themes

        """
        logger.info(f"Starting bootstrap condensation with {len(themes)} themes")

        # build co-occurrence network from bootstrap samples
        cooccurrence_network = await self._build_cooccurrence_network(themes)

        # apply Louvain clustering to get condensed themes
        condensed_themes = self._cluster_themes(themes, cooccurrence_network)

        return condensed_themes

    async def _build_cooccurrence_network(self, themes: list[dict[str, Any]]) -> nx.Graph:
        """Build a co-occurrence network from bootstrap samples.

        Args:
            themes: List of themes to process

        Returns:
            NetworkX graph with edge weights representing co-occurrence probabilities

        """
        logger.info(f"Building co-occurrence network with {self.n_bootstrap_samples} bootstrap samples")

        # start co-occurrence counter
        cooccurrence_counts: defaultdict[tuple[str, str], int] = defaultdict(int)
        total_samples = 0

        # generate bootstrap samples
        for sample_idx in range(self.n_bootstrap_samples):
            logger.info(f"Processing bootstrap sample {sample_idx + 1}/{self.n_bootstrap_samples}")

            # Shuffle themes for this sample
            shuffled_themes = themes.copy()
            random.shuffle(shuffled_themes)

            # process themes in batches
            batched_themes = [
                {"themes": shuffled_themes[i : i + self.batch_size]}
                for i in range(0, len(shuffled_themes), self.batch_size)
            ]

            # add context to batches
            for batch in batched_themes:
                batch_context = self._get_batch_context(batch["themes"])
                for key, value in batch_context.items():
                    batch[key] = value

            # get LLM responses for this sample
            try:
                condensed_responses = await process_items_with_gemini(
                    items=batched_themes,
                    prompt_template_name="theme_condensation",
                    response_model=ThemeCondensationResponse,
                    processor=self.processor,
                    concurrency=self.concurrency,
                    discussion_topic=self.discussion_topic,
                )

                # extract co-occurrences from this sample
                self._extract_cooccurrences(condensed_responses, cooccurrence_counts)
                total_samples += 1

            except Exception as e:
                logger.warning(f"Bootstrap sample {sample_idx + 1} failed: {e}")
                continue

        # convert counts to probabilities and build network
        return self._build_network_from_cooccurrences(cooccurrence_counts, total_samples, themes)

    def _get_batch_context(self, theme_batch: list[dict[str, Any]]) -> dict[str, str]:
        """Get context for a batch of themes.

        Args:
            theme_batch: Batch of themes

        Returns:
            Dictionary with context information

        """
        batch_context = {"stimulus": "", "core_question": "", "facilitator_prompts": ""}
        if self.context_dict and theme_batch:
            section_context = get_section_context(theme_batch[0].get("section_id", ""), self.context_dict)
            batch_context = {
                "stimulus": section_context.get("stimulus", ""),
                "core_question": section_context.get("core_question", ""),
                "facilitator_prompts": section_context.get("facilitator_prompts", ""),
            }
        return batch_context

    def _extract_cooccurrences(
        self, condensed_responses: list[dict[str, Any]], cooccurrence_counts: defaultdict[tuple[str, str], int]
    ) -> None:
        """Extract co-occurrences from condensed responses.

        Args:
            condensed_responses: List of condensed theme responses
            cooccurrence_counts: Dictionary to store co-occurrence counts

        """
        for batch_response in condensed_responses:
            for condensed_theme in batch_response.get("condensed_themes", []):
                inner_topics = condensed_theme.get("inner_topic_list", [])

                # count all pairs of topics that co-occur in the same condensed theme
                for i, topic1 in enumerate(inner_topics):
                    for topic2 in inner_topics[i + 1 :]:
                        # use sorted tuple to ensure consistent ordering
                        pair = tuple(sorted([topic1, topic2]))
                        cooccurrence_counts[pair] += 1

    def _build_network_from_cooccurrences(
        self, cooccurrence_counts: defaultdict[tuple[str, str], int], total_samples: int, themes: list[dict[str, Any]]
    ) -> nx.Graph:
        """Build NetworkX graph from co-occurrence counts.

        Args:
            cooccurrence_counts: Dictionary of co-occurrence counts
            total_samples: Total number of bootstrap samples
            themes: Original themes to ensure all nodes are included

        Returns:
            NetworkX graph with edge weights as probabilities

        """
        graph = nx.Graph()

        # add all theme nodes (including isolated ones)
        for theme in themes:
            topic_id = theme.get("topic_id")
            if topic_id:
                graph.add_node(topic_id)

        # add edges with weights as probabilities (likelihood of co-occurrence)
        for (topic1, topic2), count in cooccurrence_counts.items():
            probability = count / total_samples
            graph.add_edge(topic1, topic2, weight=probability)

        logger.info(f"Built network with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
        return graph

    def _cluster_themes(self, themes: list[dict[str, Any]], network: nx.Graph) -> list[dict[str, Any]]:
        """Cluster themes using Louvain algorithm.

        Args:
            themes: Original themes
            network: Co-occurrence network

        Returns:
            List of condensed themes

        """
        logger.info("Applying Louvain clustering to co-occurrence network")

        # apply Louvain clustering
        communities = list(community.louvain_communities(network, weight="weight"))

        # build condensed themes from communities
        condensed_themes = []
        for community_idx, community_topics in enumerate(communities):
            if not community_topics:
                continue

            # get themes in this community
            community_themes = [theme for theme in themes if theme["topic_id"] in community_topics]

            if not community_themes:
                continue

            # create condensed theme
            condensed_theme = self._create_condensed_theme(community_themes, community_idx)
            condensed_themes.append(condensed_theme)

        return condensed_themes

    def _create_condensed_theme(self, themes: list[dict[str, Any]], community_idx: int) -> dict[str, Any]:
        """Create a condensed theme from a community of themes.

        Args:
            themes: List of themes in the community
            community_idx: Index of the community

        Returns:
            Condensed theme dictionary

        """
        # combine source topic lists
        all_source_topics = []
        all_sentences = []
        all_section_ids = []

        for theme in themes:
            all_source_topics.extend(theme.get("source_topic_list", []))
            all_sentences.extend(theme.get("source_sentences", []))
            if theme.get("section_id"):
                all_section_ids.append(theme["section_id"])

        # create condensed theme
        condensed_theme = {
            "topic_id": f"c{community_idx}",
            "topic_label": self._generate_condensed_label(themes),
            "topic_description": self._generate_condensed_description(themes),
            "source_topic_list": all_source_topics,
            "source_sentences": all_sentences,
            "section_id": all_section_ids[0] if all_section_ids else "",
        }

        return condensed_theme

    def _generate_condensed_label(self, themes: list[dict[str, Any]]) -> str:
        """Generate a label for a condensed theme.

        Args:
            themes: List of themes to combine

        Returns:
            Combined label

        """
        labels = [theme.get("topic_label", "") for theme in themes if theme.get("topic_label")]
        return " | ".join(labels)

    def _generate_condensed_description(self, themes: list[dict[str, Any]]) -> str:
        """Generate a description for a condensed theme.

        Args:
            themes: List of themes to combine

        Returns:
            Combined description

        """
        descriptions = [theme.get("topic_description", "") for theme in themes if theme.get("topic_description")]
        if not descriptions:
            return "Combined theme from multiple sources"

        # simple combination - in practice, you might want to use LLM for this too
        return " | ".join(descriptions)
