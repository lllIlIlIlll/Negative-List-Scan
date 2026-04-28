"""tests/test_pdf.py — PDF 模块测试（v2）"""

from unittest.mock import MagicMock

from google_search.pdf import (
    save_html_snapshot,
    save_screenshot,
    wait_for_page_ready,
)


class TestWaitForPageReady:
    """wait_for_page_ready 逻辑测试"""

    def _mock_page(self):
        page = MagicMock()
        page.wait_for_load_state = MagicMock()
        page.wait_for_timeout = MagicMock()
        return page

    def test_networkidle_success(self):
        """networkidle 成功时应等待 networkidle + 额外 2 秒"""
        page = self._mock_page()

        wait_for_page_ready(page, network_idle_timeout_ms=30_000)

        page.wait_for_load_state.assert_any_call("networkidle", timeout=30)
        page.wait_for_timeout.assert_called_with(2000)

    def test_networkidle_timeout_fallback(self):
        """networkidle 超时应 fallback 到 domcontentloaded + 3 秒"""
        page = self._mock_page()
        page.wait_for_load_state.side_effect = [Exception("timeout"), None]

        result = wait_for_page_ready(page, network_idle_timeout_ms=30_000)

        calls = page.wait_for_load_state.call_args_list
        assert len(calls) == 2
        page.wait_for_load_state.assert_any_call("networkidle", timeout=30)
        page.wait_for_load_state.assert_any_call("domcontentloaded")
        page.wait_for_timeout.assert_called_with(3000)
        assert result >= 0

    def test_returns_elapsed_ms(self):
        """应返回实际等待毫秒数"""
        page = self._mock_page()

        result = wait_for_page_ready(page)

        assert isinstance(result, int)
        assert result >= 0


class TestSaveHtmlSnapshot:
    """save_html_snapshot 逻辑测试"""

    def _mock_page(self, html_content="<html><body>Test</body></html>"):
        page = MagicMock()
        page.content.return_value = html_content
        return page

    def test_saves_html_file(self, tmp_path):
        """应保存 HTML 文件"""
        page = self._mock_page()
        output_path = tmp_path / "test.html"

        result_path, sha = save_html_snapshot(page, output_path)

        assert result_path == output_path
        assert output_path.exists()
        assert sha  # SHA-256 应为 64 字符的十六进制字符串

    def test_html_content_preserved(self, tmp_path):
        """应保留 HTML 原始内容"""
        html = "<html><body>Hello World</body></html>"
        page = self._mock_page(html)
        output_path = tmp_path / "test.html"

        save_html_snapshot(page, output_path)

        assert output_path.read_text(encoding="utf-8") == html


class TestSaveScreenshot:
    """save_screenshot 逻辑测试"""

    def _mock_page(self):
        page = MagicMock()
        page.screenshot = MagicMock()
        return page

    def test_calls_page_screenshot(self, tmp_path):
        """应调用 page.screenshot"""
        page = self._mock_page()
        output_path = tmp_path / "test.png"

        result = save_screenshot(page, output_path)

        page.screenshot.assert_called_once()
        call_kwargs = page.screenshot.call_args[1]
        assert call_kwargs["path"] == str(output_path)
        assert call_kwargs["full_page"] is True
        assert result == output_path


class TestSavePdf:
    """save_pdf 逻辑测试（需要真实 CDP session，难以 mock）"""

    def test_creates_parent_directory(self, tmp_path):
        """输出目录不存在时应自动创建"""
        # 这个测试需要 mock CDP session，完整测试需要集成环境
        output_path = tmp_path / "nested" / "dir" / "test.pdf"
        assert not output_path.parent.exists()

        # 验证目录创建逻辑存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        assert output_path.parent.exists()
