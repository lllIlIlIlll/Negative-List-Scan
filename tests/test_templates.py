"""tests/test_templates.py — 模板模块单元测试（v2）"""

import pytest

from google_search.config import TemplateEntry
from google_search.templates import build_queries


def test_build_queries_custom_template():
    """自定义模板中 {name} 占位符应被替换，返回单个 Query"""
    templates = {}
    queries = build_queries(
        "三鹿集团",
        "company",
        templates,
        custom_template='"{name}" AND (欺诈 OR 投诉)',
    )
    assert len(queries) == 1
    assert queries[0].template_id == "custom"
    assert queries[0].query_text == '"三鹿集团" AND (欺诈 OR 投诉)'
    # google_url 是 URL 编码后的结果
    assert "%E4%B8%89%E9%B9%BF%E9%9B%86%E5%9B%A2" in queries[0].google_url


def test_build_queries_uses_entity_type_templates():
    """未提供自定义模板时应使用 entity_type 对应的模板"""
    templates = {
        "company": [
            TemplateEntry(id="c1", template='"{name}" AND 欺诈'),
            TemplateEntry(id="c2", template='"{name}" AND 投诉'),
        ],
    }
    queries = build_queries("三鹿集团", "company", templates)
    assert len(queries) == 2
    assert queries[0].template_id == "c1"
    assert queries[1].template_id == "c2"


def test_build_queries_google_url_encoding():
    """Google URL 应正确编码查询参数"""
    templates = {}
    queries = build_queries(
        "三鹿集团",
        "company",
        templates,
        custom_template='"{name}" AND 欺诈',
    )
    url = queries[0].google_url
    assert "q=" in url
    assert "hl=zh-CN" in url
    assert "gl=cn" in url
    assert "三鹿集团" not in url  # 应被 URL 编码


def test_build_queries_special_chars_encoded():
    """特殊字符应被正确 URL 编码"""
    templates = {}
    queries = build_queries(
        "三鹿集团",
        "company",
        templates,
        custom_template='"公司" AND (欺诈 OR 投诉)',
    )
    url = queries[0].google_url
    # 引号和括号应该被编码
    assert "+" in url or "%22" in url.upper() or "%28" in url or "%29" in url


def test_build_queries_unknown_entity_type_raises():
    """未知实体类型应抛出 ValueError"""
    templates = {}
    with pytest.raises(ValueError, match="未找到实体类型"):
        build_queries("张三", "unknown", templates)


def test_build_queries_empty_templates_raises():
    """空模板列表应抛出 ValueError"""
    templates = {"company": []}
    with pytest.raises(ValueError, match="未找到实体类型"):
        build_queries("三鹿集团", "company", templates)
