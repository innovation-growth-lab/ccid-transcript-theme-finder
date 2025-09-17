from typing import Any


class ThemeTracer:
    """Tracks theme evolution through the processing pipeline."""

    def __init__(self) -> None:
        """Initialise the theme tracer."""
        self.initial_themes: list[dict[str, Any]] = []
        self.condensed_trace_data: list[dict[str, Any]] = []
        self.refined_themes: list[dict[str, Any]] = []

    def record_initial_themes(self, themes: list[dict[str, Any]]) -> None:
        """Record the initial themes."""
        self.initial_themes = themes.copy()
        self.condensed_trace_data = [{"iteration": 0, "themes": themes.copy()}]

    def record_condensation_iteration(self, iteration: int, themes: list[dict[str, Any]]) -> None:
        """Record a condensation iteration."""
        self.condensed_trace_data.append({"iteration": iteration, "themes": themes.copy()})

    def record_refined_themes(self, themes: list[dict[str, Any]]) -> None:
        """Record the final refined themes."""
        self.refined_themes = themes.copy()

    def get_trace_data(self) -> list[dict[str, Any]]:
        """Generate the complete trace data showing theme evolution."""
        trace_rows = []

        # Create one row per granular topic ID, showing its evolution through all iterations
        for initial_theme in self.initial_themes:
            # Get the granular topic ID from source_topic_list
            source_topic_list = initial_theme.get("source_topic_list", [])
            if not source_topic_list:
                continue

            granular_topic_id = source_topic_list[0]  # Should be the only one for initial themes

            row = {
                "granular_topic_id": granular_topic_id,
                "initial_theme": initial_theme.get("topic_label", ""),
                "initial_description": initial_theme.get("topic_description", ""),
                "source_sentences": initial_theme.get("source_sentences", []),
            }

            # Add columns for each condensation iteration
            for trace_entry in self.condensed_trace_data:
                iteration = trace_entry.get("iteration", 0)
                themes = trace_entry.get("themes", [])

                # Find which theme in this iteration contains this granular topic ID
                iteration_theme = ""
                iteration_description = ""
                for theme in themes:
                    theme_source_list = theme.get("source_topic_list", [])
                    if granular_topic_id in theme_source_list:
                        iteration_theme = theme.get("topic_label", "")
                        iteration_description = theme.get("topic_description", "")
                        break

                row[f"iteration_{iteration}_theme"] = iteration_theme
                row[f"iteration_{iteration}_description"] = iteration_description

            # Find which refined theme contains this granular topic ID
            refined_theme = ""
            refined_description = ""
            refined_topic_id = ""
            for theme in self.refined_themes:
                theme_source_list = theme.get("source_topic_list", [])
                if granular_topic_id in theme_source_list:
                    refined_theme = theme.get("topic_label", "")
                    refined_description = theme.get("topic_description", "")
                    refined_topic_id = theme.get("topic_id", "")
                    refined_sentences = theme.get("source_sentences", [])
                    break

            row["refined_theme"] = refined_theme
            row["refined_description"] = refined_description
            row["refined_topic_id"] = refined_topic_id
            row["refined_sentences"] = refined_sentences

            trace_rows.append(row)

        return trace_rows
