"""Research Assistant domain errors with human-friendly messages."""


class ResearchAssistantScopeError(Exception):
    """Raised when a question is outside Spotify review research scope."""


class ResearchAssistantNoDataError(Exception):
    """Raised when no relevant review evidence exists for the question."""


class ResearchAssistantNoCorpusError(Exception):
    """Raised when the database has no RAG-eligible reviews at all."""
