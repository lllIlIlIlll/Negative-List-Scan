"""google_search.parser — best-effort DOM 解析器"""

from playwright.sync_api import Page

from google_search.models import SearchResult

# 多套选择器策略，按可靠性递减排列
_RESULT_SELECTORS = [
    "div.g",                  # 经典选择器（已不稳定）
    "div[data-snhf]",         # 部分页面
    "div[data-async-context]",
    "div.MjjYud",             # 当前主流（2024 年）
]


def parse_search_results(page: Page) -> tuple[list[SearchResult], str]:
    """解析搜索结果。

    Returns:
        (结果列表, 状态: "success" | "partial" | "failed")
    """
    results: list[SearchResult] = []
    used_selector: str | None = None

    for selector in _RESULT_SELECTORS:
        elements = page.query_selector_all(selector)
        if not elements:
            continue
        used_selector = selector
        for i, el in enumerate(elements):
            r = _try_parse_one(el, rank=i + 1)
            if r:
                results.append(r)
        if results:
            break

    if not used_selector:
        return [], "failed"
    if len(results) < 3:
        # 几乎没解析到，标记为部分失败
        return results, "partial"
    return results, "success"


def _try_parse_one(el, rank: int) -> SearchResult | None:
    try:
        title_el = el.query_selector("h3")
        if not title_el:
            return None
        title = title_el.inner_text()

        link_el = el.query_selector("a[href^='http']")
        url = link_el.get_attribute("href") if link_el else ""

        # 摘要选择器多套尝试
        snippet = ""
        for snippet_sel in ["div[data-sncf]", "div.VwiC3b", "span.aCOpRe"]:
            snippet_el = el.query_selector(snippet_sel)
            if snippet_el:
                snippet = snippet_el.inner_text()
                break

        return SearchResult(
            rank=rank, title=title, url=url, snippet=snippet,
            source="", date="",
        )
    except Exception:
        return None
