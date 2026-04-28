"""google_search.models — 数据类定义"""

from dataclasses import dataclass, field


@dataclass
class SearchResult:
    """单条搜索结果"""
    rank: int
    title: str
    url: str
    snippet: str
    source: str = ""
    date: str = ""


@dataclass
class EvidenceMetadata:
    """取证元数据：PDF/HTML/截图的路径和 SHA-256"""
    pdf_path: str
    pdf_sha256: str
    pdf_bytes: int
    html_path: str | None = None
    html_sha256: str | None = None
    screenshot_path: str | None = None


@dataclass
class TemplateRunResult:
    """单次模板搜索的结果"""
    template_id: str
    search_template: str
    search_url: str
    searched_at_utc: str
    searched_at_local: str
    evidence: EvidenceMetadata | None
    results: list[SearchResult]
    results_parse_status: str  # "success" | "partial" | "failed"
    page_load_ms: int
    had_user_interaction: bool
    error: str | None = None


@dataclass
class SearchTaskResult:
    """一次完整任务（多模板）的结果"""
    entity: str
    entity_type: str
    template_runs: list[TemplateRunResult] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.template_runs if r.error is None)

    @property
    def total_count(self) -> int:
        return len(self.template_runs)


@dataclass
class Query:
    """单条查询构造结果"""
    template_id: str
    query_text: str
    google_url: str
