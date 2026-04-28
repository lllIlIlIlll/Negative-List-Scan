"""google_search.templates — 搜索模板管理"""

import urllib.parse

from google_search.config import TemplateEntry
from google_search.models import Query


def build_queries(
    entity: str,
    entity_type: str,
    templates: dict[str, list[TemplateEntry]],
    custom_template: str | None = None,
    hl: str = "zh-CN",
    gl: str = "cn",
) -> list[Query]:
    """构造一组独立的查询。

    - 如果传入 custom_template，只返回一条查询（id 固定为 "custom"）
    - 否则按 entity_type 返回该类型的全部模板的独立查询
    """
    if custom_template:
        entries = [TemplateEntry(id="custom", template=custom_template)]
    else:
        entries = templates.get(entity_type, [])
        if not entries:
            raise ValueError(f"未找到实体类型 {entity_type} 的模板")

    queries: list[Query] = []
    for entry in entries:
        text = entry.template.replace("{name}", entity)
        url = _build_google_url(text, hl=hl, gl=gl)
        queries.append(Query(template_id=entry.id, query_text=text, google_url=url))
    return queries


def _build_google_url(query: str, hl: str, gl: str) -> str:
    """构造 Google 搜索 URL"""
    encoded = urllib.parse.quote_plus(query)
    return f"https://www.google.com/search?q={encoded}&hl={hl}&gl={gl}"
