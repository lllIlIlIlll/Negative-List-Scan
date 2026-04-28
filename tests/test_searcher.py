"""tests/test_searcher.py — 搜索流程测试（v2）"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from google_search.config import BrowserConfig, Config, OutputConfig, SearchConfig, TemplateEntry
from google_search.searcher import Searcher
from google_search.templates import build_queries


def _make_config():
    """创建测试用 Config 对象"""
    return Config(
        profile_path=Path(tempfile.mkdtemp()),
        browser=BrowserConfig(headless=True),
        search=SearchConfig(
            hl="zh-CN",
            gl="cn",
            inter_query_delay_seconds=(0, 0),  # 无延迟加速测试
        ),
        templates={
            "company": [],
            "person": [],
        },
        output=OutputConfig(
            directory=Path(tempfile.mkdtemp()),
            save_html=False,
            save_screenshot=False,
        ),
    )


def test_searcher_init():
    """Searcher 应能用 Config 初始化"""
    cfg = _make_config()
    searcher = Searcher(cfg)
    assert searcher.config == cfg


def test_build_queries_returns_list():
    """build_queries 应返回 list[Query]"""
    cfg = _make_config()
    queries = build_queries(
        "测试公司",
        "company",
        cfg.templates,
        custom_template='"{name}" AND 欺诈',
    )
    assert isinstance(queries, list)
    assert len(queries) == 1
    assert queries[0].template_id == "custom"
    assert "测试公司" in queries[0].query_text


def test_searcher_accepts_custom_template():
    """Searcher.search() 应接受 custom_template 参数"""
    cfg = _make_config()
    searcher = Searcher(cfg)

    # 验证 search 方法签名
    import inspect
    sig = inspect.signature(searcher.search)
    assert "custom_template" in sig.parameters


def test_searcher_returns_search_task_result():
    """Searcher.search() 应返回 SearchTaskResult"""
    cfg = _make_config()
    cfg.output.save_html = True
    searcher = Searcher(cfg)
    cfg.templates["company"] = [
        TemplateEntry(id="company_test", template='"{name}" AND 欺诈')
    ]

    # Mock browser session
    mock_ctx = MagicMock()
    mock_page = MagicMock()
    mock_page.url = "https://www.google.com/search?q=test"
    mock_page.goto = MagicMock()
    mock_page.wait_for_load_state = MagicMock()
    mock_page.query_selector = MagicMock(return_value=None)
    mock_page.context.new_cdp_session = MagicMock(return_value=MagicMock(
        send=MagicMock(return_value={"data": ""})
    ))
    mock_page.content = MagicMock(return_value="<html></html>")
    mock_page.evaluate = MagicMock(return_value="Mozilla/5.0")
    mock_page.viewport_size = {"width": 1280, "height": 900}
    mock_page.screenshot = MagicMock()
    mock_page.query_selector_all = MagicMock(return_value=[])

    mock_ctx.new_page.return_value = mock_page

    # Mock session context manager
    with patch.object(searcher.browser, 'session') as mock_session:
        mock_session.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)

        result = searcher.search("测试公司", "company")

    assert result.entity == "测试公司"
    assert result.entity_type == "company"
    assert result.total_count == 1
    assert result.success_count == 1
    assert list(cfg.output.directory.glob("测试公司_*.json"))


def test_sanitize_filename():
    """_sanitize_filename 应替换非法字符"""
    from google_search.searcher import _sanitize_filename

    assert _sanitize_filename("正常公司") == "正常公司"
    assert _sanitize_filename("公司/名称") == "公司_名称"
    assert _sanitize_filename("公司\\名称") == "公司_名称"
    assert _sanitize_filename("公司:名称") == "公司_名称"
    assert _sanitize_filename("公司*名称") == "公司_名称"
    assert _sanitize_filename('公司"名称') == "公司_名称"
    assert _sanitize_filename("公司<名称>") == "公司_名称_"
    assert _sanitize_filename("公司|名称") == "公司_名称"
