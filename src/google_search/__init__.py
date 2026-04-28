"""google_search — Google 负面新闻取证工具"""

__version__ = "0.2.0"

from google_search.exceptions import (
    FatalError,
    GoogleSearchError,
    RecoverableError,
    UserActionRequiredError,
)
from google_search.models import (
    EvidenceMetadata,
    Query,
    SearchResult,
    SearchTaskResult,
    TemplateRunResult,
)

# Alias for backwards compatibility
UserActionRequired = UserActionRequiredError

__all__ = [
    "__version__",
    "GoogleSearchError",
    "RecoverableError",
    "UserActionRequired",
    "UserActionRequiredError",
    "FatalError",
    "SearchResult",
    "SearchTaskResult",
    "EvidenceMetadata",
    "TemplateRunResult",
    "Query",
]
